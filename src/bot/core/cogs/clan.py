import discord

from discord.commands import slash_command, SlashCommandGroup
from discord.commands.errors import CheckFailure
from discord.ext import commands

from bot.core.checks import EcumeneCheck
from bot.core.shared import DATABASE, BNET, DICT_OF_ALL_COMMANDS
from db.query.clans import get_all_clans_in_guild, get_clan_in_guild
from db.query.members import get_members_matching, get_member_by_id
from db.query.admins import get_admin_by_id
from util.local import file_path, delete_file
from util.encrypt import generate_local
from util.data import make_empty_structure, make_structure, append_frames, format_clan_list

CHECKS = EcumeneCheck()
FILTER_INACTIVE = 'Inactive'

class Clan(commands.Cog):
    """
    Cog holding all clan-related functions.
    Basically allows management of the:
      - /clan list <filter: {all|inactive}> (list users in clans and information about them)
      - /clan kick <user> <force_flag> (kick a user from the clan, has interactive prompt but can be forced)
      - /clan join <role> (doesn't actually join the clan, but prompts admin account to send a clan invite)
    """
    def __init__(self, log):
        self.log = log
        super().__init__()

    # Define a top-level command group.
    clan = SlashCommandGroup(
        "clan", 
        "Clan administration and user management."
    )

    @clan.command(
        name='list',
        description='List all clan members and their details.',
        options=[
            discord.Option(str, name='filter', description='Filter members based on criteria.', choices=['All', FILTER_INACTIVE])
        ]
    )
    @commands.check_any(
        commands.check(CHECKS.user_has_role_permission),
        commands.check(CHECKS.user_can_manage_server),
        commands.check(CHECKS.user_is_guild_owner)
    )
    async def list(self, ctx: discord.ApplicationContext, filter: str):
        self.log.info('Command "/clan list" was invoked')
        
        # Defer response until processing is done.
        await ctx.defer()

        # Get all clans registered in this guild from the database.
        clans = get_all_clans_in_guild(DATABASE, str(ctx.guild.id))
        if not clans:
            await ctx.respond("There are no clans configured for this guild.")
            return

        # Construct member details.
        members = make_empty_structure()
        for clan_id, clan_name in zip(clans.get('clan_id'), clans.get('clan_name')):

            # Describe how returns will be handled.
            detail_map = {
                'bnet_id': list(),
                'bungie_name': list(),
                'last_online': list()
            }
            records_map = {
                'discord_id': list(),
                'discord_name': list()
            }

            # Get all members from Bungie for each clan.
            results = BNET.get_members_in_group(clan_id)
            for member in results:
                # Capture identifier and last online activity.
                bnet_info = member.get('bungieNetUserInfo')
                detail_map['bnet_id'].append(str(bnet_info.get('membershipId')))
                detail_map['bungie_name'].append(f"{bnet_info.get('bungieGlobalDisplayName')}#{bnet_info.get('bungieGlobalDisplayNameCode')}")
                detail_map['last_online'].append(member.get('lastOnlineStatusChange'))
            details = make_structure(detail_map)

            # Extract database member information.
            records = get_members_matching(DATABASE, details['bnet_id'].to_list())
            for user_id in records.get('discord_id'):
                # Capture user name from server.
                user = await ctx.guild.fetch_member(user_id)
                records_map['discord_id'].append(user_id)
                records_map['discord_name'].append(f"{user.name}#{user.discriminator}")
            struct = make_structure(records)
            struct['discord_name'] = struct['discord_id'].map(
                dict(
                    zip(
                        records_map.get('discord_id'), 
                        records_map.get('discord_name')
                    )
                )
            )

            # Structure and append additional details.
            clan_members = details.merge(struct, how='outer', on=['bnet_id'])
            clan_members['clan_id'] = clan_id
            clan_members['clan_name'] = clan_name
            members = append_frames(members, clan_members)

        # Processing of columns to make this human-readable.
        format_clan_list(members)

        # Basic filtering of list based on status.
        if filter == FILTER_INACTIVE:
            members = members.loc[members['status'] == 'Inactive'] # Kinda hardcoded but it'll be fine for now.

        # Final output columns for the "pretty" output.
        output_cols = [
            'clan_id',
            'clan_name',
            'bnet_id',
            'destiny_id',
            'discord_id',
            'bungie_name',
            'discord_name',
            'last_online_str', # Created by format_clan_list processing.
            'last_online_rel_str',
            'status'
        ]
        output = members.loc[:, output_cols]

        # Temporarily store this file locally.
        uid = generate_local()
        fpath = file_path(f"list_{uid}.csv")
        self.log.info(f"Export structure -> {fpath} ({output.shape[0]} records)")
        output.to_csv(fpath, index=False)
        
        # Attach this file into the message.
        # Delete from local cache.
        await ctx.respond(file=discord.File(fpath))
        delete_file(fpath)

    @clan.command(
        name='kick',
        description='Kick the specified user from the clan.',
        options=[
            discord.Option(discord.Member, name='user', description='Kick specified user from in-game clan.')
        ]
    )
    @commands.check_any(
        commands.check(CHECKS.user_has_role_permission),
        commands.check(CHECKS.user_can_manage_server),
        commands.check(CHECKS.user_is_guild_owner)
    )
    async def kick(self, ctx: discord.ApplicationContext, user: discord.Member):
        self.log.info('Command "/clan kick" was invoked')
        
        # Defer response until processing is done.
        # Note the ephemeral deferral is required to hide the message.
        await ctx.defer(ephemeral=True)

        # Go from user -> bnet user -> clan -> admin_id
        # Get the member record for this user.
        member = get_member_by_id(DATABASE, 'discord_id', str(user.id))
        if not member:
            await ctx.respond(f"User {user.mention} is not registered with Ecumene.")
            return

        # Get information clan from Bungie.net directly.
        # For now assume the first return is the only relevant one. Have to figure this out later.
        results = BNET.get_groups_for_user(member.get('destiny_mtype')[0], member.get('destiny_id')[0])
        if not results:
            # If user has no groups then, obviously, they're not in the clan.
            await ctx.respond(f"User {user.mention} is not in any clans.")
            return

        # Extract group information.
        to_kick = list()
        for result in results:
            group_info = result.get('group')
            member_info = result.get('member')
            group_id = group_info.get('groupId')
            group_name = group_info.get('name')
            user_membership_type = member_info.get('membershipType')

            # Pull the group administrator and credentials.
            clan = get_clan_in_guild(DATABASE, str(ctx.guild.id), group_id)
            if not clan:
                continue

            # Each clan to kick needs to record information for execution.
            info = {
                'admin_id': clan.get('admin_id')[0],
                'group_name': group_name,
                'group_id': group_id,
                'membership_type': user_membership_type
            }
            to_kick.append(info)

        # This clan isn't managed by the bot in this guild.
        if not to_kick:
            await ctx.respond(f"User {user.mention} clans are not managed by Ecumene.")
            return

        # Now actually kick user from managed clans assuming the appropriate admin.
        kicked = list()
        for kickable in to_kick:

            # This hopefully(?) always exists in the database.
            # TODO: Needs a retry block in case of background token refresh causing a race condition. 
            admin = get_admin_by_id(DATABASE, kickable.get('admin_id'))

            # Now we can kick the user directly.
            group_id = kickable.get('group_id')
            group_name = kickable.get('group_name')
            BNET.kick_member_from_group(
                admin.get('access_token')[0],
                kickable.get('group_id'),
                kickable.get('user_membership_type'),
                member.get('destiny_id')[0]
            )
            kicked.append(f"**{group_name}#{group_id}**")

        # Format success message and send.
        await ctx.respond(f"Kicked {user.mention} from {', '.join(kicked)}.")

    @clan.command(
        name='join',
        description='Ask to join a specific clan.',
        options=[
            discord.Option(discord.Role, name='clan', description='Clan you wish to join.')
        ]
    )
    async def join(self, ctx: discord.ApplicationContext, clan: str):
        self.log.info('Command "/clan join" was invoked')
        # Placeholder until the logic here is actually written.
        await ctx.respond(f"You have discovered a secret. This channel is not yet open to you.", ephemeral=True)
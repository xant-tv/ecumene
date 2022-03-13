import discord

from discord.commands import slash_command, SlashCommandGroup
from discord.commands.errors import CheckFailure
from discord.ext import commands
from bnet.client import BungieInterfaceError

from bot.core.checks import EcumeneCheck
from bot.core.shared import DATABASE, BNET, DICT_OF_ALL_COMMANDS
from bot.core.interactions import EcumeneConfirmKick
from db.query.clans import get_all_clans_in_guild, get_clan_in_guild
from db.query.members import get_members_matching, get_member_by_id
from db.query.admins import get_admin_by_id
from util.local import file_path, delete_file, write_file
from util.encrypt import generate_local
from util.data import make_empty_structure, make_structure, append_frames, format_clan_list

CHECKS = EcumeneCheck()
FILTER_INACTIVE = 'Inactive'
EMPTY = ""

class Clan(commands.Cog):
    """
    Cog holding all clan-related functions.
    Basically allows management of the:
      - /clan list <filter: {all|inactive}> (list users in clans and information about them)
      - /clan kick <user> (kick a user from the clan, has interactive prompt but can be forced)
      - /clan join <role> (doesn't actually join the clan, but prompts admin account to send a clan invite)
      - /clan promote <user> (this should be self-evident)
      - /clan demote <user> (also this)
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
    @commands.check(CHECKS.user_has_privilege)
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
                'join_date': list(),
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
                # The user's global display information may only be contained in one key! (Why Bungie?!)
                # It's also possible for the user to not have a Bungie.net login!
                bnet_info = member.get('bungieNetUserInfo') or dict()
                destiny_info = member.get('destinyUserInfo')
                display_name = bnet_info.get('bungieGlobalDisplayName') or destiny_info.get('bungieGlobalDisplayName')
                display_code = bnet_info.get('bungieGlobalDisplayNameCode') or destiny_info.get('bungieGlobalDisplayNameCode')
                join_date = member.get('joinDate')
                # Leave display names null if they're incomplete.
                bungie_name = None
                if display_name and display_code:
                    bungie_name = f"{display_name}#{str(display_code).zfill(4)}"
                detail_map['bnet_id'].append(str(bnet_info.get('membershipId', EMPTY)))
                detail_map['bungie_name'].append(bungie_name)
                detail_map['join_date'].append(join_date)
                detail_map['last_online'].append(member.get('lastOnlineStatusChange'))
            details = make_structure(detail_map)

            # Extract database member information.
            records = get_members_matching(DATABASE, 'bnet_id', details['bnet_id'].dropna().to_list())
            struct = make_empty_structure()
            if records:            
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
            clan_members = details
            if not struct.empty:
                clan_members = clan_members.merge(struct, how='outer', on=['bnet_id'])
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
            'join_date_str',
            'last_online_str', # Created by format_clan_list processing.
            'last_online_rel_str',
            'status'
        ]
        output = members.loc[:, output_cols]

        # Temporarily store this file locally.
        uid = generate_local()
        fpath = file_path(f"list_{uid}.csv")
        self.log.info(f"Export structure -> {fpath} ({output.shape[0]} records)")
        write_file(output, fpath)
        
        # Attach this file into the message.
        # Delete from local cache.
        await ctx.respond(file=discord.File(fpath))
        delete_file(fpath)

    @clan.command(
        name='kick',
        description='Kick the specified user from the clan.',
        options=[
            discord.Option(discord.Member, name='user', description='User to kick from clan.')
        ]
    )
    @commands.check(CHECKS.user_has_privilege)
    async def kick(self, ctx: discord.ApplicationContext, user: discord.Member):
        self.log.info('Command "/clan kick" was invoked')
        
        # Defer response until processing is done.
        # Note the ephemeral deferral is required to hide the message.
        await ctx.defer(ephemeral=True)

        # Make sure the user isn't trying to kick themselves.
        if user.id == ctx.author.id:
            await ctx.respond('You are not allowed to kick yourself.')
            return

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
        to_kick_name = list()
        for result in results:
            group_info = result.get('group')
            member_info = result.get('member')
            group_id = group_info.get('groupId')
            group_name = group_info.get('name')
            user_membership_type = member_info.get('membershipType')

            # Pull the group administrator and credentials.
            clan = get_clan_in_guild(DATABASE, str(ctx.guild.id), 'clan_id', group_id)
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
            to_kick_name.append(f"**{group_name}#{group_id}**")

        # This clan isn't managed by the bot in this guild.
        if not to_kick:
            await ctx.respond(f"Clans for user {user.mention} are not managed by Ecumene.")
            return

        # Create confirmation menu.
        view = EcumeneConfirmKick()
        message = await ctx.respond(f"This will kick {user.mention} from {', '.join(to_kick_name)}. Are you sure?", view=view)
    
        # Wait for the view to stop listening for input.
        await view.wait()
        if view.value is None:
            # The view timed out - not sure how long the interaction lives for.
            # await message.delete()
            await message.edit('Your request has timed out.', view=None)
        elif view.value:
            # Confirmed - continue function execution.
            pass
        else:
            # Cancelled - remove view and respond to user. Exit command.
            # await message.delete()
            await message.edit('Your request has been cancelled.', view=None)
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
            try:
                BNET.kick_member_from_group(
                    admin.get('access_token')[0],
                    kickable.get('group_id'),
                    kickable.get('user_membership_type'),
                    member.get('destiny_id')[0]
                )
                kicked.append(f"**{group_name}#{group_id}**")
            except BungieInterfaceError:
                # Kick failed, close out nicely.
                pass

        if not kicked:
            await message.edit(f"Unable to kick {user.mention}. Check clan admin configuration.", view=None)
            return

        # Format success message and send.
        await message.edit(f"Kicked {user.mention} from {', '.join(kicked)}.", view=None)

    @clan.command(
        name='promote',
        description='Promote the specific user within the clan.',
        options=[
            discord.Option(discord.Member, name='user', description='User to promote.')
        ]
    )
    @commands.check(CHECKS.user_has_privilege)
    async def promote(self, ctx: discord.ApplicationContext, user: discord.Member):
        self.log.info('Command "/clan promote" was invoked')
        await ctx.respond(f"You have discovered a secret. This channel is not yet open to you.", ephemeral=True)

    @clan.command(
        name='demote',
        description='Demote the specific user within the clan.',
        options=[
            discord.Option(discord.Member, name='user', description='User to demote.')
        ]
    )
    @commands.check(CHECKS.user_has_privilege)
    async def demote(self, ctx: discord.ApplicationContext, user: discord.Member):
        self.log.info('Command "/clan demote" was invoked')
        await ctx.respond(f"You have discovered a secret. This channel is not yet open to you.", ephemeral=True)

    # Note no checks for this command.
    @clan.command(
        name='join',
        description='Ask to join a specific clan.',
        options=[
            discord.Option(discord.Role, name='clan', description='Clan you wish to join.')
        ]
    )
    @commands.check(CHECKS.user_is_not_blacklisted)
    @commands.check(CHECKS.user_has_privilege)
    async def join(self, ctx: discord.ApplicationContext, clan: discord.Role):
        self.log.info('Command "/clan join" was invoked')
        
        # Defer response until processing is done.
        await ctx.defer(ephemeral=True)

        # Get the member record for this user.
        member = get_member_by_id(DATABASE, 'discord_id', str(ctx.author.id))
        if not member:
            await ctx.respond(f"You are not registered with Ecumene. Please register to gain access to this service.")
            return

        # Identify the clan based on the role mentioned.
        # Pull the group administrator and credentials.
        group = get_clan_in_guild(DATABASE, str(ctx.guild.id), 'role_id', str(clan.id))
        if not group:
            await ctx.respond(f"There is no clan associated with {clan.mention}.")
            return
        group_id = group.get('clan_id')[0]
        group_name = group.get('clan_name')[0]

        # TODO: Needs a retry block in case of background token refresh causing a race condition. 
        admin = get_admin_by_id(DATABASE, group.get('admin_id')[0])

        # Try and send the invite.
        # There is a potential this will send an invite to the wrong platform.
        # That depends on what membership type value is cached.
        try:
            BNET.invite_user_to_group(
                admin.get('access_token')[0],
                group_id,
                member.get('destiny_mtype')[0],
                member.get('destiny_id')[0]
            )
        except BungieInterfaceError:
            # Sending invite failed - close out nicely.
            await ctx.respond(f"Could not send a request to join {clan.mention}. The clan might be full. Contact your nearest admin.")
            return

        # Format success message and send.
        await ctx.respond(f"Invite to join **{group_name}#{group_id}** has been sent.")

    @list.error
    @kick.error
    @promote.error
    @demote.error
    @join.error
    async def clan_error(self, ctx: discord.ApplicationContext, error):
        self.log.info(error)
        if isinstance(error, CheckFailure):
            await ctx.respond('Insufficient privileges to perform this action.', ephemeral=True)
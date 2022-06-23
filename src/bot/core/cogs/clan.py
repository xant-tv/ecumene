import discord

from discord import CheckFailure
from discord.commands import slash_command, SlashCommandGroup
from discord.ext import commands
from bnet.client import BungieInterfaceError

from bot.core.checks import EcumeneCheck
from bot.core.shared import DATABASE, BNET, DICT_OF_ALL_COMMANDS, PLATFORMS, EMOJIS
from bot.core.interactions import EcumeneConfirm, EcumeneConfirmKick
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
      - /clan rank <user> (this is used to promote and demote users)
      - /clan action <method> <user> <clan> (used for direct interaction methods without discord link)
      - /clan status <role> (check the status of invites for the specified clan)
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
                    try:
                        # This invokes a call to the Discord API so it can error.
                        user = await ctx.guild.fetch_member(user_id)
                        user_discord_name = f"{user.name}#{user.discriminator}"
                    except Exception:
                        # User is not in guild.
                        user_discord_name = EMPTY
                    records_map['discord_id'].append(user_id)
                    records_map['discord_name'].append(user_discord_name)
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
            destiny_info = member_info.get('destinyUserInfo')
            user_membership_type = destiny_info.get('membershipType')

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
                    kickable.get('membership_type'),
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
        name='rank',
        description='Promote or demote the specific user within the clan.',
        options=[
            discord.Option(discord.Member, name='user', description='User to promote or demote.'),
            discord.Option(str, name='rank', description='Rank within the clan.', choices=['Member', 'Admin'])
        ]
    )
    @commands.check(CHECKS.user_has_privilege)
    async def rank(self, ctx: discord.ApplicationContext, user: discord.Member, rank: str):
        self.log.info('Command "/clan rank" was invoked')

        # Defer response until processing is done.
        # Note the ephemeral deferral is required to hide the message.
        await ctx.defer(ephemeral=True)

        # Map the rank into an enumerated value.
        rank_value = None
        if not rank:
            await ctx.respond("This shouldn't have happened. Something went wrong.")
            return
        elif rank == 'Beginner':
            rank_value = BNET.enum.mlevels.beginner
        elif rank == 'Member':
            rank_value = BNET.enum.mlevels.member
        elif rank == 'Admin':
            rank_value = BNET.enum.mlevels.admin
        else:
            await ctx.respond("This shouldn't have happened. Something went wrong.")
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
        to_set = list()
        to_set_name = list()
        for result in results:
            group_info = result.get('group')
            member_info = result.get('member')
            group_id = group_info.get('groupId')
            group_name = group_info.get('name')
            destiny_info = member_info.get('destinyUserInfo')
            user_membership_type = destiny_info.get('membershipType')

            # Pull the group administrator and credentials.
            clan = get_clan_in_guild(DATABASE, str(ctx.guild.id), 'clan_id', group_id)
            if not clan:
                continue

            # Record information for execution.
            info = {
                'admin_id': clan.get('admin_id')[0],
                'group_name': group_name,
                'group_id': group_id,
                'membership_type': user_membership_type
            }
            to_set.append(info)
            to_set_name.append(f"**{group_name}#{group_id}**")

        # This clan isn't managed by the bot in this guild.
        if not to_set:
            await ctx.respond(f"Clans for user {user.mention} are not managed by Ecumene.")
            return

        # Create confirmation menu.
        view = EcumeneConfirm()
        message = await ctx.respond(f"This will set {user.mention} to **{rank}** in {', '.join(to_set_name)}. Are you sure?", view=view)
    
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
        was_set = list()
        for settable in to_set:

            # This hopefully(?) always exists in the database.
            # TODO: Needs a retry block in case of background token refresh causing a race condition. 
            admin = get_admin_by_id(DATABASE, settable.get('admin_id'))

            # Now we can kick the user directly.
            group_id = settable.get('group_id')
            group_name = settable.get('group_name')
            try:
                BNET.set_membership_level(
                    admin.get('access_token')[0],
                    settable.get('group_id'),
                    settable.get('membership_type'),
                    member.get('destiny_id')[0],
                    rank_value
                )
                was_set.append(f"**{group_name}#{group_id}**")
            except BungieInterfaceError:
                # Kick failed, close out nicely.
                pass

        if not was_set:
            await message.edit(f"Unable to set rank for {user.mention}. Check clan admin configuration.", view=None)
            return

        # Format success message and send.
        await message.edit(f"Set {user.mention} to **{rank}** in {', '.join(was_set)}.", view=None)

    @clan.command(
        name='status',
        description='Check members and invites for a specific clan.',
        options=[
            discord.Option(discord.Role, name='clan', description='Clan you wish to inspect.')
        ]
    )
    @commands.check(CHECKS.user_has_privilege)
    async def status(self, ctx: discord.ApplicationContext, clan: discord.Role):
        self.log.info('Command "/clan status" was invoked')

        # Defer response until processing is done.
        await ctx.defer(ephemeral=True)

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

        # Try and obtain group information.
        try:
            detail = BNET.get_group_by_id(group_id)
            invited = BNET.get_invited_individuals(admin.get('access_token')[0], group_id)
            pending = BNET.get_pending_in_group(admin.get('access_token')[0], group_id)
        except BungieInterfaceError:
            # Data retrieval failed. Throw a simple error.
            await ctx.respond(f"Failed to obtain information for {clan.mention}.")
            return

        # Parse invites for information.
        invites = list()
        for invitee in invited:
            user = invitee.get('destinyUserInfo')
            name = user.get('bungieGlobalDisplayName')
            code = str(user.get('bungieGlobalDisplayNameCode')).zfill(4)
            display = f'{name}#{code}'
            mid = user.get('membershipId')
            mtype = user.get('membershipType')
            date_created = invitee.get('creationDate')
            invites.append(f"{display} ({mid}) {getattr(EMOJIS, PLATFORMS.get(mtype))}")

        pends = list()
        for pendee in pending:
            user = invitee.get('destinyUserInfo')
            name = user.get('bungieGlobalDisplayName')
            code = str(user.get('bungieGlobalDisplayNameCode')).zfill(4)
            display = f'{name}#{code}'
            mid = user.get('membershipId')
            mtype = user.get('membershipType')
            date_created = invitee.get('creationDate')
            pends.append(f"{display} ({mid}) {getattr(EMOJIS, PLATFORMS.get(mtype))}")
        
        invite_str = 'There are no active invites.'
        if invites:
            invite_str = '\n'.join(invites)

        pend_str = 'There are no pending requests.'
        if pends:
            pend_str = '\n'.join(pends)

        embed = discord.Embed(
            title='Clan Details',
            description='Ecumene has access to the following clan information.'
        )
        embed.add_field(
            name=f'{group_name}#{group_id} {EMOJIS.destiny}',
            value=f"Members: {detail.get('memberCount')}/{detail.get('features').get('maximumMembers')}\nInvites: {len(invites)}\nPending: {len(pends)}",
            inline=False
        )
        embed.add_field(
            name='Invited Individuals',
            value=invite_str,
            inline=False
        )
        embed.add_field(
            name='Pending Requests',
            value=pend_str,
            inline=False
        )

        embed.set_thumbnail(url=BNET.web + detail.get('avatarPath'))
        embed.set_footer(text=f"Ecumene", icon_url='https://ecumene.cc/static/assets/img/ecumene.png')

        # Format success message and send.
        await ctx.respond(embed=embed)

    @clan.command(
        name='cancel',
        description='Cancel a clan invite for the specified individual.',
        options=[
            discord.Option(discord.Role, name='clan', description='Clan you wish to interact with.'),
            discord.Option(discord.Member, name='user', description='User for which to cancel invite.')
        ]
    )
    @commands.check(CHECKS.user_has_privilege)
    async def cancel(self, ctx: discord.ApplicationContext, clan: discord.Role, user: discord.Member):
        self.log.info('Command "/clan cancel" was invoked')

        # Defer response until processing is done.
        await ctx.defer(ephemeral=True)

        # Identify the clan based on the role mentioned.
        # Pull the group administrator and credentials.
        group = get_clan_in_guild(DATABASE, str(ctx.guild.id), 'role_id', str(clan.id))
        if not group:
            await ctx.respond(f"There is no clan associated with {clan.mention}.")
            return
        group_id = group.get('clan_id')[0]

        # Get the member record for this user.
        member = get_member_by_id(DATABASE, 'discord_id', str(user.id))
        if not member:
            await ctx.respond(f"User {user.mention} is not registered with Ecumene.")
            return

        # TODO: Needs a retry block in case of background token refresh causing a race condition. 
        admin = get_admin_by_id(DATABASE, group.get('admin_id')[0])

        # Try and cancel invite.
        try:
            BNET.cancel_invite_to_group(
                admin.get('access_token')[0], 
                group_id, 
                member.get('destiny_mtype')[0],  
                member.get('destiny_id')[0]
            )
        except BungieInterfaceError:
            # Data retrieval failed. Throw a simple error.
            await ctx.respond(f"Failed to cancel invite to {clan.mention} for {user.mention}. Are you sure this invite exists?")
            return

        # Format success message and send.
        await ctx.respond(f"Cancelled invite to {clan.mention} for {user.mention}.")

    @clan.command(
        name='action',
        description='Interact with the Bungie clan directly.',
        options=[
            discord.Option(str, name='method', description='Method of interaction.', choices=['Kick', 'Cancel Invite']),
            discord.Option(str, name='user', description='Bungie name of player.'),
            discord.Option(discord.Role, name='clan', description='Clan you wish to interact with.', required=False)
        ]
    )
    @commands.check(CHECKS.user_has_privilege)
    async def action(self, ctx: discord.ApplicationContext, method: str, user: str, clan: discord.Role):
        self.log.info('Command "/clan action" was invoked')

        # Defer response until processing is done.
        # Note the ephemeral deferral is required to hide the message.
        await ctx.defer(ephemeral=True)

        # Split name entry by the code.
        try:
            user_name, user_code = user.split('#')
        except Exception:
            await ctx.respond("Please provide full Bungie display name of the user.")
            return
        
        # Now we need to find all users potentially matching this combination.
        players = BNET.find_destiny_player(user_name, user_code)
        if not players:
            await ctx.respond(f"No player matching the name **{user}** was found.")
            return

        # If a group is provided, we want to get some basic information about it.
        # Identify the clan based on the role mentioned.
        # Pull the group administrator and credentials.
        if clan:
            group = get_clan_in_guild(DATABASE, str(ctx.guild.id), 'role_id', str(clan.id))
            if not group:
                await ctx.respond(f"There is no clan associated with {clan.mention}.")
                return

        # Perform the appropriate action.
        # Pass-through just in case a method is not covered properly.
        if not method:
            pass

        # To kick, we need to obtain more user information.
        elif method == 'Kick':

            # For each user we need to:
            # - Identify any groups they are registered with.
            # - Map the user information to that group.
            all_results = list()
            for player in players:
                
                membership_id = player.get('membershipId')
                membership_type = player.get('membershipType')
                results = BNET.get_groups_for_user(membership_type, membership_id)
                if results:
                    all_results += results
            
            # If no results have been returned then, obviously, they're not in the clan.
            if not all_results:
                await ctx.respond(f"User **{user}** is not in any clans.")
                return

            # Extract group information.
            to_kick = list()
            to_kick_name = list()
            for results in all_results:
                group_info = results.get('group')
                member_info = results.get('member')
                group_id = group_info.get('groupId')
                group_name = group_info.get('name')
                destiny_info = member_info.get('destinyUserInfo')
                user_membership_id = destiny_info.get('membershipId')
                user_membership_type = destiny_info.get('membershipType')

                # Pull the group administrator and credentials.
                clan = get_clan_in_guild(DATABASE, str(ctx.guild.id), 'clan_id', group_id)
                if not clan:
                    continue

                # Each clan to kick needs to record information for execution.
                info = {
                    'admin_id': clan.get('admin_id')[0],
                    'group_name': group_name,
                    'group_id': group_id,
                    'membership_id': user_membership_id,
                    'membership_type': user_membership_type
                }
                to_kick.append(info)
                to_kick_name.append(f"**{group_name}#{group_id}**")

            # This clan isn't managed by the bot in this guild.
            if not to_kick:
                await ctx.respond(f"Clans for user **{user}** are not managed by Ecumene.")
                return

            # Create confirmation menu.
            view = EcumeneConfirmKick()
            message = await ctx.respond(f"This will kick **{user}** from {', '.join(to_kick_name)}. Are you sure?", view=view)
        
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
                        kickable.get('membership_type'),
                        kickable.get('membership_id')
                    )
                    kicked.append(f"**{group_name}#{group_id}**")
                except BungieInterfaceError:
                    # Kick failed, close out nicely.
                    pass

            if not kicked:
                await message.edit(f"Unable to kick **{user}**. Check clan admin configuration.", view=None)
                return
            
            # Format success message and send.
            await message.edit(f"Kicked **{user}** from {', '.join(kicked)}.", view=None)
            return
        
        # To cancel invites, we need some clan information.
        elif method == 'Cancel Invite':

            # If no clan is provided, we need to exit out.
            if not clan:
                await ctx.respond('This method requires a clan input.')
                return

            # Get some group information from the initial return.        
            group_id = group.get('clan_id')[0]
            group_name = group.get('clan_name')[0]
            
            # Query administrator information for this clan.
            admin = get_admin_by_id(DATABASE, group.get('admin_id')[0])

            # Try and obtain group information.
            try:
                invited = BNET.get_invited_individuals(admin.get('access_token')[0], group_id)
            except BungieInterfaceError:
                # Data retrieval failed. Throw a simple error.
                await ctx.respond(f"Failed to obtain information for {clan.mention}.")
                return

            # Create a mapping for existing invites.
            invite_map = dict()
            for invite in invited:
                user_info = invite.get('destinyUserInfo')
                invite_name = user_info.get('bungieGlobalDisplayName')
                invite_code = str(user_info.get('bungieGlobalDisplayNameCode')).zfill(4)
                display = f'{invite_name}#{invite_code}'
                mid = user_info.get('membershipId')
                mtype = user_info.get('membershipType')
                invite_map[display] = (mid, mtype)

            # Find the equivalent invite tuple through name and code.
            if user not in invite_map.keys():
                await ctx.respond(f"Failed to cancel invite to {clan.mention} for **{user}**. Are you sure this invite exists?")
                return

            # Attempt to cancel invite.
            mid, mtype = invite_map.get(user)
            try:
                BNET.cancel_invite_to_group(
                    admin.get('access_token')[0], 
                    group_id, 
                    mtype,  
                    mid
                )
            except BungieInterfaceError:
                # Data retrieval failed. Throw a simple error.
                await ctx.respond(f"Failed to cancel invite to {clan.mention} for **{user}**. Are you sure this invite exists?")
                return

            # Format success message and send.
            await ctx.respond(f"Cancelled invite to {clan.mention} for **{user}**.")
            return

        # Catch-all case if somehow the chosen method wasn't implemented.
        await ctx.respond("This shouldn't have happened. Something went wrong.")
        return

    # Note additional checks for this command.
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
    @rank.error
    @status.error
    @cancel.error
    @action.error
    @join.error
    async def clan_error(self, ctx: discord.ApplicationContext, error):
        self.log.info(error)
        if isinstance(error, CheckFailure):
            await ctx.respond('Insufficient privileges to perform this action.', ephemeral=True)
import discord

from discord.commands import slash_command
from discord.ext import commands

from bot.core.checks import EcumeneCheck
from bot.core.interactions import EcumenePlatformDropdown, EcumeneSelectPlatform
from bot.core.routines import routine_before, routine_after, routine_error
from bot.core.shared import DATABASE, BNET, PLATFORMS, LEVELS, EMOJIS
from web.core.shared import WEB_RESOURCES
from db.query.clans import get_all_clans_in_guild
from db.query.members import get_member_by_id, update_member_details
from db.query.transactions import update_transaction
from util.encrypt import generate_state
from util.enum import TransactionType, AuditRecordType
from util.time import get_current_time, epoch_to_time, bnet_to_time, time_to_discord, get_timedelta, humanize_timedelta

DT_FMT = '{dt.day} {dt:%B} {dt.year} {dt:%H}:{dt:%M}:{dt:%S}'
CHECKS = EcumeneCheck()

class Identity(commands.Cog):
    """
    Cog holding all identity-related functions.
    This includes:
      - /register (user registration)
      - /profile (allows user to select preferred platform)
      - /inspect (user identification check)
    """
    def __init__(self, log):
        self.log = log
        super().__init__()

    @slash_command(
        name='register', 
        description="Begin negotiations with Ecumene."
    )
    @commands.check(CHECKS.guild_is_not_blacklisted)
    async def register(self, ctx: discord.ApplicationContext):
        """Register with Ecumene leadership."""

        # Defer response until processing is done.
        await ctx.defer(ephemeral=True)

        # If no guild, then something went wrong.
        if not ctx.guild:
            await ctx.respond('This command has to be run within a server context.')
            await routine_after(ctx, AuditRecordType.FAILED_CONTEXT)
            return

        # Capture message information and generate a state.
        state = generate_state()
        purpose = TransactionType.USER.value
        data = {
            'state': state,
            'guild_id': str(ctx.guild.id), # Might have to make this optional because you can message commands to the bot directly, too.
            'request_id': str(ctx.author.id),
            'request_display': str(ctx.author),
            'purpose': purpose,
            'requested_at': get_current_time()
        }
        
        # Insert this data into the store.
        DATABASE.insert('transactions', data)

        # Use state to produce an authorisation URL.
        url = BNET.get_authorisation_url(state)

        # Generate a message embed.
        embed = discord.Embed(
            title='Ecumene Registration',
            url=url,
            description=f"Your interest has been noted. Please click the link and follow instructions."
        )
        embed.set_thumbnail(url=WEB_RESOURCES.logo)
        embed.set_footer(text=f"ecumene.cc", icon_url=WEB_RESOURCES.logo)

        # Generate message content.
        content = f" • Registration is global across all servers."
        content += f"\n • Registration is supported for any platform."
        content += f"\n • Only one Bungie account may be linked to Discord at a time."
        embed.add_field(
            name=f'Important Information',
            value=content,
            inline=False
        )

        # Respond to the initial command.
        message = await ctx.author.send(embed=embed)

        # Obtain channel and message information that was just sent.
        # Update transaction record to include this information.
        info = {
            'channel_id': str(message.channel.id),
            'message_id': str(message.id)
        }
        update_transaction(DATABASE, info, state)
        self.log.info('Registration now awaiting web response...')

        # Close out context.
        await ctx.respond("Negotiations have begun. Enact impulse.")
        await routine_after(ctx, AuditRecordType.SUCCESS)

    @slash_command(
        name='inspect', 
        description="Find out information about a user (or yourself).",
        options=[
            discord.Option(discord.Member, name='user', description='User to inspect.', required=False)
        ]
    )
    @commands.check(CHECKS.guild_is_not_blacklisted)
    async def inspect(self, ctx: discord.ApplicationContext, user: discord.Member):

        # Defer response until processing is done.
        await ctx.defer(ephemeral=True)

        # If no user, we assume it is the author.
        if not user:
            user = ctx.author

        # If no guild, then something went wrong.
        if not ctx.guild:
            await ctx.respond('This command has to be run within a server context.')
            await routine_after(ctx, AuditRecordType.FAILED_CONTEXT)
            return
        
        # Get the author's identity.
        id = str(user.id)
        result = get_member_by_id(DATABASE, 'discord_id', id)

        # Get clans we manage for this guild.
        managed = get_all_clans_in_guild(DATABASE, str(ctx.guild.id))

        # If no result, then the user is not registered.
        if not result:

            # Generate a basic embed with only Discord details.
            embed = discord.Embed(
                title='Ecumene User Details',
                description='Ecumene has no record of this user within the network. Available information is limited.'
            )

            # User display.
            user_display = f"{user.display_name}"
            if user.id == ctx.guild.owner_id:
                user_display += f" {EMOJIS.owner}"
            if user.premium_since:
                user_display += f" {EMOJIS.nitro}"
            user_text = f"{user_display}\nJoined: {time_to_discord(user.joined_at)} ({humanize_timedelta(get_timedelta(user.joined_at))})"
            
            # Add to embed as top-most field.
            embed.add_field(
                name=f'{user.name}#{user.discriminator} ({id}) {EMOJIS.discord}',
                value=user_text,
                inline=False
            )
            embed.set_thumbnail(url=user.display_avatar.url)
            embed.set_footer(text=f"ecumene.cc", icon_url=WEB_RESOURCES.logo)

            await ctx.respond(embed=embed)
            await routine_after(ctx, AuditRecordType.SUCCESS)
            return

        # Get information about the user from Bungie.
        content = BNET.get_linked_profiles(result.get('destiny_mtype')[0], result.get('destiny_id')[0])
        bnet_info = content.get('bnetMembership')
        profile_info = content.get('profiles')
        legacy_info = content.get('profilesWithErrors')

        # If there are no profiles, we can back up to the user search.
        # TODO: Refactor this whole function later.
        if not profile_info:
            backup_name = bnet_info.get('bungieGlobalDisplayName')
            backup_code = bnet_info.get('bungieGlobalDisplayNameCodes')
            profile_info = BNET.find_destiny_player(backup_name, backup_code)

        # Sometimes we are missing Bungie information as well!
        if not bnet_info:
            alt_content = BNET.get_linked_profiles(result.get('bnet_mtype')[0], result.get('bnet_id')[0])
            bnet_info = alt_content.get('bnetMembership')

        # Now we need to get clan membership information for all active profiles.
        clans = list()
        for profile in profile_info:
            group_results = BNET.get_groups_for_user(profile.get('membershipType'), profile.get('membershipId'))
            for entry in group_results:
                group = entry.get('group')
                clan_header = {
                    'group_id': group.get('groupId'),
                    'group_name': group.get('name'),
                    'member_type': profile.get('membershipType'),
                    'member_id': profile.get('membershipId')
                }
                clans.append(clan_header)
        
        # Sort clans by identifier.
        clan_dict = {
            int(clan.get('group_id')): clan for clan in clans
        }
        sorted_ids = sorted(clan_dict.keys())
        sorted_clans = list()
        for clan_id in sorted_ids:
            sorted_clans.append(clan_dict[clan_id])
            
        # Information about when a user actually joined a group is not available from the GetUserGroups API - really, why?
        # Instead, we have to loop through each clan and hit the members API and parse that.
        for clan in sorted_clans:
            
            # Flag is the clan is managed by ecumene while we're at it.
            if managed:
                if clan.get('group_id') in managed.get('clan_id'):
                    clan['ecumene_managed'] = True

            # Hit and parse members API - we are only doing this for active profiles.
            members = BNET.get_members_in_group(clan.get('group_id'))
            for member in members:
                destiny_info = member.get('destinyUserInfo')
                if destiny_info.get('membershipId') == clan.get('member_id'):
                    clan['member_level'] = LEVELS.get(member.get('memberType'))
                    clan['member_since'] = member.get('joinDate')

        # Generate a message embed.
        embed = discord.Embed(
            title='Ecumene User Details',
            description='Ecumene has access to the following user information across all platforms.'
        )

        # Parse other Discord or Ecumene information.
        ecumene_registered = epoch_to_time(int(result.get('registered_on')[0]))
        user_display = f"{user.display_name}"
        if user.id == ctx.guild.owner_id:
            user_display += f" {EMOJIS.owner}"
        if user.premium_since:
            user_display += f" {EMOJIS.nitro}"
        user_text = f"{user_display}\nJoined: {time_to_discord(user.joined_at)} ({humanize_timedelta(get_timedelta(user.joined_at))})"
        
        # Add to embed as top-most field.
        embed.add_field(
            name=f'{user.name}#{user.discriminator} ({id}) {EMOJIS.discord}',
            value=user_text,
            inline=False
        )

        # Generate output formats.
        accounts = list()
        last_played = epoch_to_time(0)
        for profile in profile_info:

            # Update last played.
            played = bnet_to_time(profile.get('dateLastPlayed'))
            if played > last_played:
                last_played = played

            # Append platform information.
            platforms = list()
            platforms.append(getattr(EMOJIS, PLATFORMS.get(profile.get('membershipType'))))
            if profile.get('isCrossSavePrimary'):
                # Flag as cross-save account.
                platforms.append(EMOJIS.cross_save) 
            if profile.get('membershipType') == result.get('destiny_mtype')[0]:
                # If the registered membership type matches the platform, append our emoji as well.
                platforms.append(EMOJIS.ecumene)
                platforms.append('(Primary)')

            # Add to accounts list.
            platform_text = ' '.join(platforms)
            accounts.append(f"{profile.get('displayName')} {platform_text}")
        
        for legacy in legacy_info:

            # Similar, shorter process for legacy accounts.
            # Each legacy account is listed alongside an error code so the actual data is nested.
            card = legacy.get('infoCard')
            platform = getattr(EMOJIS, PLATFORMS.get(card.get('membershipType')))
            accounts.append(f"{card.get('displayName')} {platform}")
        
        # Account text to display.
        account_text = '\n'.join(accounts)
        account_text += f"\n\nLast Played:\n{time_to_discord(last_played)} ({humanize_timedelta(get_timedelta(last_played))})"

        # Add to embed as second field.
        embed.add_field(
            name=f"{bnet_info.get('bungieGlobalDisplayName')}#{str(bnet_info.get('bungieGlobalDisplayNameCode')).zfill(4)} ({result.get('destiny_id')[0]}) {EMOJIS.destiny}",
            value=account_text,
            inline=False
        )

        # Clan text to display.
        for clan in sorted_clans:
            
            # Record clan name, platform and join date.
            clan_name = f"{clan.get('group_name')}#{clan.get('group_id')}"
            clan_platform = getattr(EMOJIS, PLATFORMS.get(clan.get('member_type')))
            clan_display = f"{clan_name} {clan_platform}"
            if clan.get('ecumene_managed'):
                clan_display += f" {EMOJIS.ecumene}"
            join_date = bnet_to_time(clan.get('member_since'))
            join_date_delta = get_timedelta(join_date)

            # Create a field for each clan.
            embed.add_field(
                name=clan_display,
                value=f"{clan.get('member_level')}\nJoined: {time_to_discord(join_date)} ({humanize_timedelta(join_date_delta)})",
                inline=False
            )
        
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_footer(text=f"ecumene.cc | {DT_FMT.format(dt=ecumene_registered)} ECMNST", icon_url=WEB_RESOURCES.logo)

        # Close out context.
        await ctx.respond(embed=embed)
        await routine_after(ctx, AuditRecordType.SUCCESS)

    @slash_command(
        name='profile', 
        description="Set your primary profile."
    )
    @commands.check(CHECKS.guild_is_not_blacklisted)
    async def profile(self, ctx: discord.ApplicationContext):

        # Defer response until processing is done.
        await ctx.defer(ephemeral=True)
        
        # Get the member record for this user.
        member = get_member_by_id(DATABASE, 'discord_id', str(ctx.author.id))
        if not member:
            await ctx.respond(f"You are not registered with Ecumene. Please register to gain access to this service.")
            await routine_after(ctx, AuditRecordType.FAILED_UNREGISTERED)
            return
            
        # Existing user information.
        membership_id = member.get('destiny_id')[0]
        platform_id = member.get('destiny_mtype')[0]
        bungie_id = member.get('bnet_id')[0]

        # We need to search for all user profile options.
        linked_profiles = BNET.get_linked_profiles(BNET.enum.mtype.bungie, bungie_id)
        profile_data = linked_profiles.get('profiles')
        if not profile_data:
            linked_profiles = BNET.get_linked_profiles(platform_id, membership_id)
            profile_data = linked_profiles.get('profiles')
        profile_map = dict()
        for profile in profile_data:
            profile_type = profile.get('membershipType')
            profile_map[profile_type] = profile
        primary_profile = profile_map.get(platform_id)
        if not primary_profile:
            primary_profile = profile_data[0]
        display_name = primary_profile.get('displayName')
        bungie_name = f"{primary_profile.get('bungieGlobalDisplayName')}#{str(primary_profile.get('bungieGlobalDisplayNameCode')).zfill(4)}"

        # Extract flags about cross-save and multiple profiles.
        cross_save = False
        cross_save_platform = primary_profile.get('crossSaveOverride')
        mismatch = False
        if cross_save_platform:
            cross_save = True
        has_multiple = False
        if len(profile_data) > 1:
            has_multiple = True

        # Construct field information.
        content_header = 'I have detected one profile linked to this account.'
        if cross_save:
            content_header = 'I detect this user has cross-save enabled.'
        if has_multiple:
            content_header = 'It appears this user has multiple active platforms.'
        content_info = "\n\nThis user's primary profile is set to:"
        content_info += f'\n**{display_name}** ({membership_id}:{platform_id}) {getattr(EMOJIS, PLATFORMS.get(platform_id))}'
        if cross_save:
            if cross_save_platform == platform_id:
                content_info += f' {EMOJIS.cross_save}'
            else:
                mismatch = True
                content_info += f'\n\n*There is a mismatch between cross-save and selected profiles.*'
        if has_multiple or mismatch:
            content_info += '\n\nAll available profiles are:'
            for profile_id in sorted(profile_map.keys()):
                profile_name = profile_map[profile_id].get('displayName')
                content_info += f'\n**{profile_name}** ({membership_id}:{profile_id}) {getattr(EMOJIS, PLATFORMS.get(profile_id))}'
                if cross_save_platform == profile_id:
                    content_info += f' {EMOJIS.cross_save}'
        else:
            content_info += '\n\nThere are no other available profiles.'
        content_footer ="\n\nUse the dropdown below to update primary profile."

        # Display current user information.
        content = content_header + content_info + content_footer
            
        # Generate option objects.
        options = list()
        for profile_id in sorted(profile_map.keys()):
            platform = PLATFORMS.get(profile_id)
            label = platform.capitalize()
            emoji = getattr(EMOJIS, platform)
            option = discord.SelectOption(
                label=label, emoji=emoji
            )
            options.append(option)
        
        # Try making an interaction with this.
        dropdown = EcumenePlatformDropdown(options)
        view = EcumeneSelectPlatform(dropdown)

        # Respond with both the embed and the interactive view.
        message = await ctx.respond(content, view=view)

        # Wait for the view to stop listening for input.
        await view.wait()
        if view.value is None:
            # The view timed out - timeout default is 3 minutes.
            # await message.delete()
            await message.edit('Your request has timed out.', view=None)
            await routine_after(ctx, AuditRecordType.FAILED_TIMEOUT)
            return
        elif view.value:
            # Value chosen - continue function execution.
            pass
        
        # Update value in database to reflect current settings.
        target_mtype = getattr(BNET.enum.mtype, view.value.lower())
        data = {
            'discord_id': str(ctx.author.id),
            'destiny_id': str(profile_map[target_mtype].get('membershipId')),
            'destiny_mtype': target_mtype
        }
        update_member_details(DATABASE, 'discord_id', data)

        # Recreate embed with new information.
        await message.edit(f'Request acknowledged. Primary profile set to **{view.value}**.',  view=None)
        await routine_after(ctx, AuditRecordType.SUCCESS)
        return

    @register.before_invoke
    @inspect.before_invoke
    @profile.before_invoke    
    async def inspect_before(self, ctx: discord.ApplicationContext):
        await routine_before(ctx, self.log)

    @register.error
    @inspect.error
    @profile.error
    async def inspect_error(self, ctx: discord.ApplicationContext, error):
        await routine_error(ctx, self.log, error)
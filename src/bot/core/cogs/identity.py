import discord

from discord.commands import slash_command
from discord.ext import commands

from bot.core.checks import EcumeneCheck
from bot.core.shared import DATABASE, BNET, PLATFORMS, LEVELS, EMOJIS
from db.query.clans import get_all_clans_in_guild
from db.query.members import get_member_by_id
from db.query.transactions import update_transaction
from util.encrypt import generate_state
from util.time import get_current_time, epoch_to_time, bnet_to_time, get_timedelta, humanize_timedelta
from util.enum import ENUM_USER_REGISTRATION

DT_FMT = '%B %d %Y %H:%M:%S'
CHECKS = EcumeneCheck()

# TODO: Commands that will need to be implemented.
#   - /whoami (print stored user data back)

class Identity(commands.Cog):
    """
    Cog holding all identity-related functions.
    This includes:
      - /register (user registration)
      - /whoami (user identification check)
    """
    def __init__(self, log):
        self.log = log
        super().__init__()

    @slash_command(
        name='register', 
        description="Begin negotiations with Ecumene."
    )
    async def register(self, ctx: discord.ApplicationContext):
        """Register with Ecumene leadership."""
        self.log.info('Command "/register" was invoked')

        # Defer response until processing is done.
        await ctx.defer(ephemeral=True)

        # If no guild, then something went wrong.
        if not ctx.guild:
            await ctx.respond('This command has to be run within a server context.')
            return

        # Capture message information and generate a state.
        state = generate_state()
        purpose = ENUM_USER_REGISTRATION
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

    @slash_command(
        name='inspect', 
        description="Find out information about a user (or yourself).",
        options=[
            discord.Option(discord.Member, name='user', description='User to inspect.', required=False)
        ]
    )
    async def inspect(self, ctx: discord.ApplicationContext, user: discord.Member):
        self.log.info('Command "/inspect" was invoked')

        # Defer response until processing is done.
        await ctx.defer(ephemeral=True)

        # If no user, we assume it is the author.
        if not user:
            user = ctx.author

        # If no guild, then something went wrong.
        if not ctx.guild:
            await ctx.respond('This command has to be run within a server context.')
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
            user_text = f"{user_display}\nJoined: {user.joined_at.strftime(DT_FMT)} ({humanize_timedelta(get_timedelta(user.joined_at))})"
            
            # Add to embed as top-most field.
            embed.add_field(
                name=f'{user.name}#{user.discriminator} ({id}) {EMOJIS.discord}',
                value=user_text,
                inline=False
            )
            embed.set_thumbnail(url=user.display_avatar.url)
            embed.set_footer(text=f"Ecumene", icon_url='https://ecumene.cc/static/assets/img/ecumene.png')

            await ctx.respond(embed=embed)
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
        user_text = f"{user_display}\nJoined: {user.joined_at.strftime(DT_FMT)} ({humanize_timedelta(get_timedelta(user.joined_at))})"
        
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
        account_text += f"\n\nLast Played:\n{last_played.strftime(DT_FMT)} ({humanize_timedelta(get_timedelta(last_played))})"

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
                value=f"{clan.get('member_level')}\nJoined: {join_date.strftime(DT_FMT)} ({humanize_timedelta(join_date_delta)})",
                inline=False
            )
        
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_footer(text=f"Ecumene | {ecumene_registered.strftime(DT_FMT)}", icon_url='https://ecumene.cc/static/assets/img/ecumene.png')

        # Close out context.
        await ctx.respond(embed=embed)
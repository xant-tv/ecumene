import discord

from discord.commands import slash_command, SlashCommandGroup
from discord.commands.errors import CheckFailure
from discord.ext import commands

from bot.core.checks import EcumeneCheck
from bot.core.interactions import EcumeneConfirmRemoveClan
from bot.core.shared import DATABASE, BNET, DICT_OF_ALL_COMMANDS
from db.query.transactions import update_transaction
from db.query.clans import get_all_clans_in_guild, get_clan_in_guild, delete_clan_in_guild
from util.encrypt import generate_state
from util.time import get_current_time
from util.enum import ENUM_ADMIN_REGISTRATION

CHECKS = EcumeneCheck()

# TODO: Actually implement all the functionality for these.
# TODO: All functions here will require an audit log as well.

class Admin(commands.Cog):
    """
    Cog holding all admin-related functions.
    These commands are used for registering clan administration:
      - /admin register <id> <role> (basically /register but for a destiny clan)
      - /admin deregister <id> (remove a clan from bot administration)
      - /admin list (list clans and the roles that administrate them)
      - /admin grant <clan> <role> (allows the selected role to run /clan commands for that clan)
      - /admin revoke <clan> <role> (disallows the selected role from running /clan commands for that clan)
    """
    def __init__(self, log):
        self.log = log
        super().__init__()

    # Define a top-level command group.
    admin = SlashCommandGroup(
        "admin", 
        "Restricted clan administration commands."
    )

    @admin.command(
        name='register',
        description='Register a clan with Ecumene.',
        options=[
            discord.Option(str, name='clan', description='Group identifier for the clan you wish to register.'),
            discord.Option(discord.Role, name='role', description='Role to attach to this clan.')
        ]
    )
    @commands.check(CHECKS.user_has_privilege)
    async def register(self, ctx: discord.ApplicationContext, clan: str, role: discord.Role):
        self.log.info('Command "/admin register" was invoked')

        # Defer response until processing is done.
        await ctx.defer(ephemeral=True)

        # Try to resolve the clan identifier. If not valid, we would want to notify.
        detail = BNET.get_group_by_id(clan)

        # Capture message information and generate a state.
        state = generate_state()
        purpose = ENUM_ADMIN_REGISTRATION
        data = {
            'state': state,
            'guild_id': str(ctx.guild.id),
            'request_id': clan,
            'request_display': f"{detail.get('name')}#{clan}",
            'option_id': str(role.id),
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
            description=f"Your request for elevated access has been noted. Please authorise accordingly."
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
        await ctx.respond("Privilege escalation has begun. Enact impulse.")

    @admin.command(
        name='deregister',
        description='Stop administering a clan with Ecumene.',
        options=[
            discord.Option(str, name='clan', description='Group identifier for the clan you wish to deregister.')
        ]
    )
    @commands.check(CHECKS.user_has_privilege)
    async def deregister(self, ctx: discord.ApplicationContext, clan: str):
        self.log.info('Command "/admin deregister" was invoked')

        # Defer response until processing is done.
        await ctx.defer(ephemeral=True)

        # Check if we have this clan in this guild.
        results = get_clan_in_guild(DATABASE, str(ctx.guild.id), 'clan_id', clan)
        if not results:
            await ctx.respond("This clan is not managed by Ecumene for this server.")
            return

        # Get some clan details.
        clan_name = f"{results.get('clan_name')[0]}#{results.get('clan_id')[0]}"

        # Create confirmation menu.
        view = EcumeneConfirmRemoveClan()
        message = await ctx.respond(f"This will remove **{clan_name}** from my network. Are you sure?", view=view)
    
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

        # Remove the clan entry.
        delete_clan_in_guild(DATABASE, str(ctx.guild.id), clan)
        await message.edit(f'Designated clan **{clan_name}** has been removed.', view=None)

    @admin.command(
        name='list',
        description='List all clans registered with Ecumene in this server.',
    )
    @commands.check(CHECKS.user_has_privilege)
    async def clans(self, ctx: discord.ApplicationContext):
        self.log.info('Command "/admin list" was invoked')

        # Defer response until processing is done.
        await ctx.defer(ephemeral=True)

        # Get clans for this server.
        clans = get_all_clans_in_guild(DATABASE, str(ctx.guild.id))
        if not clans:
            await ctx.respond('Ecumene does not manage any clans on this server.')
            return

        # Structure details so we can loop numerically by identifier.
        clan_details = dict()
        for clan_id, clan_name, role_id in zip(clans.get('clan_id'), clans.get('clan_name'), clans.get('role_id')):
            data = {
                'clan_name': clan_name,
                'role_id': int(role_id)
            }
            clan_details[int(clan_id)] = data
        
        # Nicely format the clan names.
        clan_display = list()
        for clan_id in sorted(clan_details.keys()):
            clan_data = clan_details.get(clan_id) # Already an integer from prior handling.
            role = ctx.guild.get_role(clan_data.get('role_id'))
            clan_display.append(f"**{clan_data.get('clan_name')}#{clan_id}** → {role.mention}")

        # Respond to request.
        list_separator = "\n • "
        await ctx.respond(f"Clans managed by Ecumene: {list_separator}{list_separator.join(clan_display)}")

    @register.error
    @clans.error
    async def admin_error(self, ctx: discord.ApplicationContext, error):
        self.log.info(error)
        if isinstance(error, CheckFailure):
            await ctx.respond('Insufficient privileges to perform this action.', ephemeral=True)
import discord

from discord.commands import slash_command, SlashCommandGroup
from discord.commands.errors import CheckFailure
from discord.ext import commands

from bot.core.checks import EcumeneCheck
from bot.core.shared import DATABASE, BNET, DICT_OF_ALL_COMMANDS
from db.query.transactions import update_transaction
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

    @register.error
    async def admin_error(self, ctx: discord.ApplicationContext, error):
        self.log.info(error)
        if isinstance(error, CheckFailure):
            await ctx.respond('Insufficient privileges to perform this action.', ephemeral=True)
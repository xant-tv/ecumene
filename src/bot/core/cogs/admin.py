import discord

from discord.commands import slash_command, SlashCommandGroup
from discord.commands.errors import CheckFailure
from discord.ext import commands

from bot.core.checks import EcumeneCheck
from bot.core.shared import DATABASE, BNET, GUILDS, DICT_OF_ALL_COMMANDS
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
      - /admin register <clan> (basically /register but for a destiny clan)
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
        "Restricted clan administration commands.", 
        guild_ids=GUILDS
    )

    @admin.command(
        name='register',
        description='Register a clan with Ecumene.',
        options=[
            discord.Option(str, name='id', description='Group identifier for the clan you wish to register.', required=True)
        ],
        guild_ids=GUILDS
    )
    @commands.check_any(
        commands.check(CHECKS.user_has_role_permission),
        commands.check(CHECKS.user_can_manage_server),
        commands.check(CHECKS.user_is_guild_owner)
    )
    async def register(self, ctx: discord.ApplicationContext, id: str):
        self.log.info('Command "/admin register" was invoked')

        # Try to resolve the clan identifier. If not valid, we would want to notify.
        detail = BNET.get_group_by_id(id)

        # Capture message information and generate a state.
        state = generate_state()
        purpose = ENUM_ADMIN_REGISTRATION
        data = {
            'state': state,
            'guild_id': str(ctx.guild.id),
            'request_id': id,
            'request_display': f"{detail.get('name')}#{id}",
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
        await ctx.respond("Priviledge escalation has begun. Enact impulse.", ephemeral=True)

    @register.error
    async def admin_error(self, ctx: discord.ApplicationContext, error):
        self.log.info(error)
        if isinstance(error, CheckFailure):
            await ctx.respond('Insufficient privileges to perform this action.')
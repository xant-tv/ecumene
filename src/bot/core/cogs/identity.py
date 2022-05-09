import discord

from discord.commands import slash_command
from discord.ext import commands

from bot.core.checks import EcumeneCheck
from bot.core.shared import DATABASE, BNET
from db.query.transactions import update_transaction
from util.encrypt import generate_state
from util.time import get_current_time
from util.enum import ENUM_USER_REGISTRATION

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
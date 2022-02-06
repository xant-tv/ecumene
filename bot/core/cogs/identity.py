import discord

from discord.commands import slash_command
from discord.ext import commands

from bot.core.checks import EcumeneCheck
from bot.core.shared import DATABASE, BNET, GUILDS
from db.query import update_transaction
from util.encrypt import generate_state
from util.time import get_current_time

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
        description="Begin negotiations with Ecumene.", 
        guild_ids=GUILDS
    )
    async def register(self, ctx: discord.ApplicationContext):
        """Register with Ecumene leadership."""
        self.log.info('Command "/register" was invoked')

        # Capture message information and generate a state.
        state = generate_state()
        data = {
            'state': state,
            'discord_id': str(ctx.author.id),
            'req_display_name': str(ctx.author),
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
        await ctx.respond("Negotiations have begun. Enact impulse.", ephemeral=True)

    # CONTAINS /register and /whoami
    pass
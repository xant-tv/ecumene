import random
import logging
import discord

from bot.core.interactions import EcumeneView, EcumeneDropdown
from bnet.client import BungieInterface
from db.client import DatabaseService
from db.query import update_transaction
from util.local import get_user
from util.encrypt import generate_state
from util.time import get_current_time

class EcumeneEventHandler():

    def __init__(self):
        self.log = logging.getLogger(f'{self.__module__}.{self.__class__.__name__}')
        self.bnet = BungieInterface()
        self.db = DatabaseService()

    async def register(self, ctx):
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
        self.db.insert('transactions', data)

        # Use state to produce an authorisation URL.
        url = self.bnet.get_authorisation_url(state)

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
        update_transaction(self.db, info, state)

        # Close out context.
        await ctx.respond("Negotiations have begun. Enact impulse.", ephemeral=True)

    async def admin(self, ctx):
        self.log.info('Command "/admin" was invoked')
        await ctx.respond("This information is top-secret.")

    async def colour(self, ctx, limit_interactions: bool):
        self.log.info('Command "/colour" was invoked')
        # Create the view we want to present.
        # Note the view starts as disabled until the parent message is attached.
        options = [
            discord.SelectOption(
                label="Red", description="Your favourite colour is red.", emoji="🟥"
            ),
            discord.SelectOption(
                label="Green", description="Your favourite colour is green.", emoji="🟩"
            ),
            discord.SelectOption(
                label="Blue", description="Your favourite colour is blue.", emoji="🟦"
            )
        ]

        # Split functionality based on "limit_interactions" flag.
        delete_after = None
        if not limit_interactions:
            delete_after = 10

        # Create dropdown and add to view on construct.
        dropdown = EcumeneDropdown(options, limit=limit_interactions)
        view = EcumeneView(
            children=[dropdown]
        )

        # Send a response to the command including the interaction view.
        # Capture the response message object and attach this parent to the dropdown for callback.
        # Attaching the parent will enable the view (in-memory object).
        response = await ctx.respond("What is your favourite color?", view=view, delete_after=delete_after)
        if not limit_interactions:
            return

        # This is only necessary if interactions are limited.
        message = await response.original_message()
        view.attach_parent(message)

        # We need to update the message on Discord to reflect the new non-disabled state.
        await response.edit_original_message(view=view)

    async def ping(self, ctx):
        self.log.info('Command "/ping" was invoked')
        await ctx.respond(f"{ctx.author.mention}", ephemeral=True)
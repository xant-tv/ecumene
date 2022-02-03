import random
import logging
import discord

from bot.interactions import EcumeneView, EcumeneDropdown
from api.client import BungieInterface
from util.local import get_user
from util.format import format_as_code_block

class EcumeneEventHandler():

    def __init__(self):
        self.log = logging.getLogger(f'{self.__module__}.{self.__class__.__name__}')
        self.bnet = BungieInterface()

    async def register(self, ctx):
        """Register with Ecumene leadership."""
        await ctx.author.send("Your interest has been noted. Instructions will follow.")
        await ctx.respond("Negotiations have begun. Enact impulse.")

    async def choose(self, ctx, *choices: str):
        """Chooses between multiple choices."""
        await ctx.respond(random.choice(choices))

    async def bungo(self, ctx, clan):
        """Ping the Bungie API to get some basic data."""
        clan = self.bnet.find_clan_by_name(clan)
        msg = format_as_code_block(clan, 'json')
        await ctx.respond(msg)

    async def admin(self, ctx):
        await ctx.respond("This information is top-secret.")

    async def flawless(self, ctx, user, activity):
        member = get_user(user.id, 'discord')
        is_flawless = self.bnet.is_flawless(
            member.get('destiny').get('id'), 
            member.get('destiny').get('type'), 
            activity.lower()
        )
        if is_flawless:
            await ctx.respond(f'Yes, {user} is a Flawless {activity.capitalize()}er!')
            return
        await ctx.respond(f'No, {user} is not a Flawless {activity.capitalize()}er!')

    async def colour(self, ctx, limit_interactions: bool):
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
        await ctx.respond(f"{ctx.author.mention}", ephemeral=True)
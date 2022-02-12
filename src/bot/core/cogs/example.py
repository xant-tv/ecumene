import discord

from distutils.util import strtobool
from discord.commands import slash_command
from discord.ext import commands

from bot.core.checks import EcumeneCheck
from bot.core.interactions import EcumeneView, EcumeneDropdown
from bot.core.shared import GUILDS

CHECKS = EcumeneCheck()

class Example(commands.Cog):
    """
    Example functions only.
    Will be removed later.
    """
    def __init__(self, log):
        self.log = log
        super().__init__()

    # Sub-function in case we want to call this as a dummy later.
    async def _ping_(self, ctx: discord.ApplicationContext):
        await ctx.respond(f"{ctx.author.mention}", ephemeral=True)

    @slash_command(
        name='ping',
        description='You have a red dot now.'
    )
    async def ping(self, ctx: discord.ApplicationContext):
        self.log.info('Command "/ping" invoked')
        await self._ping_(ctx)

    # Demonstration of how arguments work.
    @slash_command(
        name='flawless', 
        description="I'm better than you.",
        options=[
            discord.Option(str, name='activity', description="Activity that I'm better than you at.", choices=['Raid', 'Dungeon']),
            discord.Option(discord.Member, description='Identify yourself.', name='user'),
            discord.Option(str, name='meme', description='Memes are always better.', choices=['Yes', 'No'], required=False)
        ],
        guild_ids=GUILDS
    )
    async def flawless(self, ctx: discord.ApplicationContext, activity: str, user: discord.Member, meme: str):
        self.log.info('Command "/flawless" invoked')
        await self._ping_(ctx)

    # Demonstration interaction test command.
    @slash_command(
        name='colour',
        description='You made this? I made this! 😀',
        options=[
            discord.Option(str, name='limit', description="Do you limit interactions?", choices=['Yes', 'No']),
        ],
        guild_ids=GUILDS 
    )
    async def colour(self, ctx: discord.ApplicationContext, limit):
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
        limit_interactions = strtobool(limit.lower())
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
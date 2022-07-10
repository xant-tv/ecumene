import discord

from distutils.util import strtobool
from discord.commands import slash_command
from discord.ext import commands

from bot.core.checks import EcumeneCheck

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
        ]
    )
    async def flawless(self, ctx: discord.ApplicationContext, activity: str, user: discord.Member, meme: str):
        self.log.info('Command "/flawless" invoked')
        await self._ping_(ctx)
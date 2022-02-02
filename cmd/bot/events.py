import random
import logging

from api.client import BungieInterface
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
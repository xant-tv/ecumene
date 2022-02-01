import random
import logging

import api.client
import util.format

class EcumeneEventHandler():

    def __init__(self):
        self.log = logging.getLogger(f'{self.__module__}.{self.__class__.__name__}')
        self.bnet = api.client.BungieInterface()

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
        msg = util.format.format_as_code_block(clan, 'json')
        await ctx.respond(msg)
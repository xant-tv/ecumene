import logging

from discord.ext import commands
from discord.commands.errors import CheckFailure

class EcumeneErrorHandler():

    def __init__(self):
        self.log = logging.getLogger(f'{self.__module__}.{self.__class__.__name__}')

    async def admin(self, ctx, error):
        self.log.info(error)
        if isinstance(error, CheckFailure):
            await ctx.respond('Insufficient privileges to receive this transmission.')
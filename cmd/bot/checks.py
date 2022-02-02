import inspect
import logging

from discord.ext import commands

class EcumeneCheckHandler():

    def __init__(self):
        self.log = logging.getLogger(f'{self.__module__}.{self.__class__.__name__}')

    def is_guild_owner(self):
        def predicate(ctx):
            self.log.info(f'Check is_guild_owner() predicate')
            return ctx.guild is not None and ctx.guild.owner_id == ctx.author.id
        return commands.check(predicate)
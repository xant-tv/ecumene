import logging

from discord.ext import commands

from util.local import get_roles_permitted

class EcumeneCheckHandler():

    def __init__(self):
        self.log = logging.getLogger(f'{self.__module__}.{self.__class__.__name__}')

    def is_guild_owner(self):
        def predicate(ctx):
            self.log.info(f'Check is_guild_owner() predicate')
            return ctx.guild is not None and ctx.guild.owner_id == ctx.author.id
        return commands.check(predicate)

    def user_has_role_permission(self):
        def predicate(ctx):
            self.log.info(f'Check user_has_role_permission() predicate')
            permitted = get_roles_permitted(ctx.command.name)
            for role in ctx.author.roles:
                if role.id in permitted:
                    return True
            return False
        return commands.check(predicate)
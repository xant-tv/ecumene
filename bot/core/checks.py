import logging
import discord

from bot.core.shared import DATABASE, BNET, DICT_OF_ALL_COMMANDS
from util.local import get_roles_permitted

class EcumeneCheck():

    def __init__(self):
        self.log = logging.getLogger(f'{self.__module__}.{self.__class__.__name__}')

    def user_is_guild_owner(self, ctx):
        self.log.info(f'Check is_guild_owner() invoked')
        return ctx.guild is not None and ctx.guild.owner_id == ctx.author.id

    def user_can_manage_server(self, ctx):
        self.log.info(f'Check user_can_manage_server() invoked')
        return ctx.guild is not None and ctx.author.guild_permissions.manage_guild

    def user_has_role_permission(self, ctx):
        self.log.info(f'Check user_has_role_permission() invoked')
        self.log.info(f'Checking permissions against "{ctx.command.parent.name}/{ctx.command.name}"...')
        permitted = get_roles_permitted(ctx.command.parent.name, ctx.command.name)
        for role in ctx.author.roles:
            if role.id in permitted:
                return True
        return False
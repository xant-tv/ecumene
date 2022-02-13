import copy
import logging
import discord

from bot.core.shared import DATABASE, BNET, DICT_OF_ALL_COMMANDS
from util.local import get_roles_permitted

def get_command_name(cmd, default=''):
    """Extracts command name."""
    # Check if command object exists.
    # Return the expected name property or replace with default.
    if cmd:
        return cmd.name
    return default

def get_lineage(cmd, lineage=list()):
    """Recursively builds group -> command lineage."""
    lineage.append(get_command_name(cmd))
    if cmd.parent:
        get_lineage(cmd.parent, lineage)
    return lineage

def get_lineage_paths(lineage, paths=list()):
    """
    Recursively builds lineage paths for permission checks.
    Expects the lineage input to be reversed from get_lineage().
    """
    # Capture number of members.
    members = len(lineage)

    # Loop through lineage members count.
    for i in range(members):
        # Consider the slice of lineage up to the (i+1)th member.
        # Build that into a string.
        branch = lineage[:i+1]
        name = '.'.join(branch)
        # If your slice length ommitted the child.
        if len(branch) < members:
            name += '.*'
        paths.append(name)

    return paths

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
        # Get lineage and display path.
        lineage = get_lineage(ctx.command)
        display_path = '/'.join(reversed(lineage))
        self.log.info(f'Checking permissions against "{display_path}"...')
        # Obtain role paths from lineage.
        role_paths = get_lineage_paths(list(reversed(lineage)))
        permitted = get_roles_permitted(role_paths)
        for role in ctx.author.roles:
            if role.id in permitted:
                return True
        return False
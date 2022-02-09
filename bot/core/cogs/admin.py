import discord

from discord.commands import slash_command, SlashCommandGroup
from discord.commands.errors import CheckFailure
from discord.ext import commands

from bot.core.checks import EcumeneCheck
from bot.core.shared import DATABASE, BNET, GUILDS, DICT_OF_ALL_COMMANDS
from db.query import update_transaction
from util.encrypt import generate_state
from util.time import get_current_time

CHECKS = EcumeneCheck()

# TODO: Actually implement all the functionality for these.
# TODO: All functions here will require an audit log as well.

class Admin(commands.Cog):
    """
    Cog holding all admin-related functions.
    This includes:
      - /admin grant <role> <command> (configure permissions for the selected role)
      - /admin revoke <role> <command> (undoes the grant)
      - /admin roles <command> (list roles with permissiosn for a command)
      - /admin command <roles> (list commands able to be run by a specific role)
      - /admin register <group> (basically /register but for a destiny clan)
      - /admin message (restricted test command)
    """
    def __init__(self, log):
        self.log = log
        super().__init__()

    # Define a top-level command group.
    # It would be possible to attach 
    admin = SlashCommandGroup(
        "admin", 
        "Restricted admin commands.", 
        guild_ids=GUILDS
    )

    # Grant function to configure per-role permissions.
    @admin.command(
        name='grant', 
        description="Grant permission for a role to execute a command.",
        options=[
            discord.Option(discord.Role, name='role', description="Role to award grant to."),
            discord.Option(str, name='command', description='Command to grant permissions for.', choices=sorted(DICT_OF_ALL_COMMANDS.keys()))
        ]
    )
    @commands.check_any(
        commands.check(CHECKS.user_has_role_permission),
        commands.check(CHECKS.user_can_manage_server),
        commands.check(CHECKS.user_is_guild_owner)
    )
    async def grant(self, ctx: discord.ApplicationContext, role: discord.Role, command: str):
        self.log.info('Command "/grant" was invoked')
        permission = DICT_OF_ALL_COMMANDS.get(command)
        await ctx.respond(f'Grant {permission} to {role.mention}!')

    @admin.command(
        name='revoke', 
        description="Revoke permission from a role to execute a command.",
        options=[
            discord.Option(discord.Role, name='role', description="Role to revoke permissions from."),
            discord.Option(str, name='command', description='Command to revoke access to.', choices=sorted(DICT_OF_ALL_COMMANDS.keys()))
        ]
    )
    @commands.check_any(
        commands.check(CHECKS.user_has_role_permission),
        commands.check(CHECKS.user_can_manage_server),
        commands.check(CHECKS.user_is_guild_owner)
    )
    async def revoke(self, ctx: discord.ApplicationContext, role: discord.Role, command: str):
        self.log.info('Command "/revoke" was invoked')
        permission = DICT_OF_ALL_COMMANDS.get(command)
        await ctx.respond(f'Revoke {permission} from {role.mention}!')

    @admin.command(
        name='roles', 
        description="List all roles able to execute a command.",
        options=[
            discord.Option(str, name='command', description='Command to list role permissions for.', choices=sorted(DICT_OF_ALL_COMMANDS.keys()))
        ]
    )
    @commands.check_any(
        commands.check(CHECKS.user_has_role_permission),
        commands.check(CHECKS.user_can_manage_server),
        commands.check(CHECKS.user_is_guild_owner)
    )
    async def roles(self, ctx: discord.ApplicationContext, command: str):
        self.log.info('Command "/roles" was invoked')
        permission = DICT_OF_ALL_COMMANDS.get(command)
        await ctx.respond(f'List roles for {permission}!')

    @admin.command(
        name='command', 
        description="List all roles able to execute a command.",
        options=[
            discord.Option(discord.Role, name='role', description='Role to list command permissions for.')
        ]
    )
    @commands.check_any(
        commands.check(CHECKS.user_has_role_permission),
        commands.check(CHECKS.user_can_manage_server),
        commands.check(CHECKS.user_is_guild_owner)
    )
    async def command(self, ctx: discord.ApplicationContext, role: discord.Role):
        self.log.info('Command "/command" was invoked')
        await ctx.respond(f'List permissions for {role.mention}!')

    # Demonstration admin-restricted role-based access commmand.
    @admin.command(
        name='message', 
        description="Receive a top-secret communication."
    )
    @commands.check_any(
        commands.check(CHECKS.user_has_role_permission),
        commands.check(CHECKS.user_can_manage_server),
        commands.check(CHECKS.user_is_guild_owner)
    )
    async def message(self, ctx: discord.ApplicationContext):
        self.log.info('Command "/message" was invoked')
        await ctx.respond("This information is top-secret.")

    @grant.error
    @revoke.error
    @roles.error
    @command.error
    @message.error
    async def admin_error(self, ctx: discord.ApplicationContext, error):
        self.log.info(error)
        if isinstance(error, CheckFailure):
            await ctx.respond('Insufficient privileges to perform this action.')
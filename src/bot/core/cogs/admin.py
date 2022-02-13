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
      - /admin roles <command> (list roles with permissions for a command)
      - /admin command <roles> (list commands able to be run by a specific role)

    These commands are useful for registering a clan:
      - /admin clan register <clan> (basically /register but for a destiny clan)
      - /admin clan list (list clans and the roles that administrate them)
      - /admin clan grant <clan> <role> (allows the selected role to run /clan commands for that clan)
      - /admin clan revoke <clan> <role> (disallows the selected role from running /clan commands for that clan)
    """
    def __init__(self, log):
        self.log = log
        super().__init__()

    # Define a top-level command group.
    admin = SlashCommandGroup(
        "admin", 
        "Restricted admin commands.", 
        guild_ids=GUILDS
    )

    # Create a subgroup for clan-level configuration.
    clan = admin.create_subgroup(
        "clan", 
        "Restricted admin commands for clan configuration.", 
        guild_ids=GUILDS
    )

    # Grant function to configure per-role permissions.
    @admin.command(
        name='grant', 
        description="Grant permission for a role to execute a command.",
        options=[
            discord.Option(discord.Role, name='role', description="Role to award grant to."),
            discord.Option(str, name='command', description='Command to grant permissions for.', choices=sorted(DICT_OF_ALL_COMMANDS.keys()))
        ], 
        guild_ids=GUILDS
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
        ], 
        guild_ids=GUILDS
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
        ], 
        guild_ids=GUILDS
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
        ], 
        guild_ids=GUILDS
    )
    @commands.check_any(
        commands.check(CHECKS.user_has_role_permission),
        commands.check(CHECKS.user_can_manage_server),
        commands.check(CHECKS.user_is_guild_owner)
    )
    async def command(self, ctx: discord.ApplicationContext, role: discord.Role):
        self.log.info('Command "/command" was invoked')
        await ctx.respond(f'List permissions for {role.mention}!')

    @clan.command(
        name='register',
        description='Register a clan with Ecumene.',
        guild_ids=GUILDS
    )
    @commands.check_any(
        commands.check(CHECKS.user_has_role_permission),
        commands.check(CHECKS.user_can_manage_server),
        commands.check(CHECKS.user_is_guild_owner)
    )
    async def register(self, ctx: discord.ApplicationContext):
        self.log.info('Command "/register" was invoked')
        await ctx.respond("This is the worst idea in the world.")

    # Demonstration admin-restricted role-based access commmand.
    @admin.command(
        name='message', 
        description="Receive a top-secret communication.", 
        guild_ids=GUILDS
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
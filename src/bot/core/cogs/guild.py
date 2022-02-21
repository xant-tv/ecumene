import discord

from discord.commands import slash_command, SlashCommandGroup
from discord.commands.errors import CheckFailure
from discord.ext import commands

from bot.core.checks import EcumeneCheck
from bot.core.shared import DICT_OF_ALL_COMMANDS

CHECKS = EcumeneCheck()

# TODO: Actually implement all the functionality for these.
# TODO: All functions here will require an audit log as well.

class Guild(commands.Cog):
    """
    Cog holding all guild-related functions.
    This includes:
      - /guild grant <role> <command> (configure permissions for the selected role)
      - /guild revoke <role> <command> (undoes the grant)
      - /guild roles <command> (list roles with permissions for a command)
      - /guild command <roles> (list commands able to be run by a specific role)
    """
    def __init__(self, log):
        self.log = log
        super().__init__()

    # Define a top-level command group.
    guild = SlashCommandGroup(
        "guild", 
        "Restricted guild configuration commands."
    )

    # Grant function to configure per-role permissions.
    @guild.command(
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
        await ctx.respond(f'Grant {permission} to {role.mention}!', ephemeral=True)

    # Revoker function.
    @guild.command(
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
        await ctx.respond(f'Revoke {permission} from {role.mention}!', ephemeral=True)

    # List roles by command.
    @guild.command(
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
        await ctx.respond(f'List roles for {permission}!', ephemeral=True)

    # List commands by role.
    @guild.command(
        name='command', 
        description="List all commands able to executed by a role.",
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
        await ctx.respond(f'List permissions for {role.mention}!', ephemeral=True)

    # Demonstration admin-restricted role-based access commmand.
    @guild.command(
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
        await ctx.respond("This information is top-secret.", ephemeral=True)

    @grant.error
    @revoke.error
    @roles.error
    @command.error
    @message.error
    async def guild_error(self, ctx: discord.ApplicationContext, error):
        self.log.info(error)
        if isinstance(error, CheckFailure):
            await ctx.respond('Insufficient privileges to perform this action.', ephemeral=True)
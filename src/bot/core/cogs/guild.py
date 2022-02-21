import discord

from discord.commands import slash_command, SlashCommandGroup
from discord.commands.errors import CheckFailure
from discord.ext import commands

from bot.core.checks import EcumeneCheck
from bot.core.shared import DATABASE, DICT_OF_ALL_COMMANDS
from db.query.members import check_blacklist, add_user_to_blacklist, remove_user_from_blacklist

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
      - /guild block <user> (add user to guild blacklist)
      - /guild unblock <user> (remove user from guild blacklist)
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

    @guild.command(
        name='block',
        description='Block user from clan-related interaction with Ecumene.',
        options=[
            discord.Option(discord.Member, name='user', description='User to block.')
        ]
    )
    @commands.check_any(
        commands.check(CHECKS.user_has_role_permission),
        commands.check(CHECKS.user_can_manage_server),
        commands.check(CHECKS.user_is_guild_owner)
    )
    async def block(self, ctx: discord.ApplicationContext, user: discord.Member):
        self.log.info('Command "/guild block" was invoked')

        # Defer response until processing is done.
        await ctx.defer(ephemeral=True)

        # You cannot block yourself.
        if user.id == ctx.author.id:
            await ctx.respond('You cannot block yourself.')
            return

        # You cannot block the guild owner or people with manage permissions.
        if user.guild_permissions.manage_guild or ctx.guild.owner_id == ctx.author.id:
            await ctx.respond('You do not have permissions to block this person.')
            return

        # Check if the user is already blocked.
        blacklisted = check_blacklist(DATABASE, str(ctx.guild.id), str(user.id))
        if blacklisted:
            await ctx.respond(f"User {user.mention} is already blocked in this server.")
            return

        # Add user to blacklist.
        add_user_to_blacklist(DATABASE, str(ctx.guild.id), str(user.id))
        await ctx.respond(f"User {user.mention} added to server block list.")

    @guild.command(
        name='unblock',
        description='Unblock user from clan-related interaction with Ecumene.',
        options=[
            discord.Option(discord.Member, name='user', description='User to unblock.')
        ]
    )
    @commands.check_any(
        commands.check(CHECKS.user_has_role_permission),
        commands.check(CHECKS.user_can_manage_server),
        commands.check(CHECKS.user_is_guild_owner)
    )
    async def unblock(self, ctx: discord.ApplicationContext, user: discord.Member): 
        self.log.info('Command "/guild unblock" was invoked')

        # Defer response until processing is done.
        await ctx.defer(ephemeral=True)       

        # Check if the user is already blocked.
        blacklisted = check_blacklist(DATABASE, str(ctx.guild.id), str(user.id))
        if not blacklisted:
            await ctx.respond(f"User {user.mention} is not blocked in this server.")
            return

        # Add user to blacklist.
        remove_user_from_blacklist(DATABASE, str(ctx.guild.id), str(user.id))
        await ctx.respond(f"User {user.mention} removed from server block list.")

    @grant.error
    @revoke.error
    @roles.error
    @command.error
    @block.error
    @unblock.error
    async def guild_error(self, ctx: discord.ApplicationContext, error):
        self.log.info(error)
        if isinstance(error, CheckFailure):
            await ctx.respond('Insufficient privileges to perform this action.', ephemeral=True)
import discord

from discord import CheckFailure
from discord.commands import slash_command, SlashCommandGroup
from discord.ext import commands

from bot.core.checks import EcumeneCheck, get_lineage_paths
from bot.core.shared import DATABASE, DICT_OF_ALL_COMMANDS, DICT_OF_ALL_PERMISSIONS
from db.query.members import check_blacklist, add_user_to_blacklist, remove_user_from_blacklist
from db.query.permissions import \
    select_permission, \
    insert_permission, \
    delete_permission, \
    get_permitted_roles_bulk, \
    get_role_permissions, \
    nuke_permissions, \
    clear_permissions_by_role, \
    clear_permissions_by_command

CHECKS = EcumeneCheck()

# TODO: Actually implement all the functionality for these.
# TODO: All functions here will require an audit log as well.

class Guild(commands.Cog):
    """
    Cog holding all guild-related functions.
    This includes:
      - /guild grant <role> <command> (configure permissions for the selected role)
      - /guild revoke <role> <command> (undoes the grant)
      - /guild clear role <role> (clears all permissions for any provided roles or commands)
      - /guild clear command <command> (clears all permissions for any provided roles or commands)
      - /guild clear all (resets all permissions for everything in the guild)
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

    clear = guild.create_subgroup(
        "clear", 
        "Clear guild configuration."
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
    @commands.check(CHECKS.user_has_privilege)
    async def grant(self, ctx: discord.ApplicationContext, role: discord.Role, command: str):
        self.log.info('Command "/guild grant" was invoked')

        # Defer response until processing is done.
        await ctx.defer(ephemeral=True)

        # If role can manage guild, this doesn't need to do anything.
        if role.permissions.manage_guild:
            await ctx.respond(f'{role.mention} already has access to `{command}`.')
            return

        # Check if permission exists first.
        identifier = DICT_OF_ALL_COMMANDS.get(command)
        permission = select_permission(DATABASE, str(ctx.guild.id), str(role.id), identifier)
        if permission:
            # Permission already exists.
            await ctx.respond(f'{role.mention} already has access to `{command}`.')
            return

        # Create the permission.
        insert_permission(DATABASE, str(ctx.guild.id), str(role.id), identifier)
        await ctx.respond(f'Granted access to `{command}` to {role.mention}.')

    # Revoker function.
    @guild.command(
        name='revoke', 
        description="Revoke permission from a role to execute a command.",
        options=[
            discord.Option(discord.Role, name='role', description="Role to revoke permissions from."),
            discord.Option(str, name='command', description='Command to revoke access to.', choices=sorted(DICT_OF_ALL_COMMANDS.keys()))
        ]
    )
    @commands.check(CHECKS.user_has_privilege)
    async def revoke(self, ctx: discord.ApplicationContext, role: discord.Role, command: str):
        self.log.info('Command "/guild revoke" was invoked')

        # Defer response until processing is done.
        await ctx.defer(ephemeral=True)

        # If role can manage guild, this doesn't need to do anything.
        if role.permissions.manage_guild:
            await ctx.respond(f'Cannot revoke `{command}` privileges from {role.mention}.')
            return

        # Check if permission exists first.
        identifier = DICT_OF_ALL_COMMANDS.get(command)
        permission = select_permission(DATABASE, str(ctx.guild.id), str(role.id), identifier)
        if not permission:
            # Permission does not exist.
            await ctx.respond(f'No permission for {role.mention} for `{command}`. Nothing to revoke.')
            return

        # Create the permission.
        delete_permission(DATABASE, str(ctx.guild.id), str(role.id), identifier)
        await ctx.respond(f'Revoked access to `{command}` from {role.mention}.')

    # Clear permissions from role.
    @clear.command(
        name='role', 
        description="Clear all permissions from a role",
        options=[
            discord.Option(discord.Role, name='role', description="Role to clear permissions from.")
        ]
    )
    @commands.check(CHECKS.user_has_privilege)
    async def clear_role(self, ctx: discord.ApplicationContext, role: discord.Role):
        self.log.info('Command "/guild clear role" was invoked')

        # Defer response until processing is done.
        await ctx.defer(ephemeral=True)

        # Clear by role.
        clear_permissions_by_role(DATABASE, str(ctx.guild.id), str(role.id))
        await ctx.respond(f'Cleared all permissions for {role.mention}.')

    # Clear all permissions from command.
    @clear.command(
        name='command', 
        description="Clear all permissions from a command",
        options=[
            discord.Option(str, name='command', description="Command to clear permissions from.", choices=sorted(DICT_OF_ALL_COMMANDS.keys()))
        ]
    )
    @commands.check(CHECKS.user_has_privilege)
    async def clear_command(self, ctx: discord.ApplicationContext, command: str):
        self.log.info('Command "/guild clear command" was invoked')

        # Defer response until processing is done.
        await ctx.defer(ephemeral=True)

        # Get command and clear.
        identifier = DICT_OF_ALL_COMMANDS.get(command)
        clear_permissions_by_command(DATABASE, str(ctx.guild.id), identifier)
        await ctx.respond(f'Cleared all permissions for `{command}`.')

    # Nuke all permissions.
    @clear.command(
        name='all', 
        description="Reset all configured permissions for the entire server."
    )
    @commands.check(CHECKS.user_has_privilege)
    async def reset(self, ctx: discord.ApplicationContext):
        self.log.info('Command "/guild clear all" was invoked')

        # Defer response until processing is done.
        await ctx.defer(ephemeral=True)

        # Create the permission.
        nuke_permissions(DATABASE, str(ctx.guild.id))
        await ctx.respond(f'All permissions on server have been nuked.')

    # List roles by command.
    @guild.command(
        name='roles', 
        description="List all roles able to execute a command.",
        options=[
            discord.Option(str, name='command', description='Command to list role permissions for.', choices=sorted(DICT_OF_ALL_COMMANDS.keys()))
        ]
    )
    @commands.check(CHECKS.user_has_privilege)
    async def roles(self, ctx: discord.ApplicationContext, command: str):
        self.log.info('Command "/guild roles" was invoked')

        # Defer response until processing is done.
        await ctx.defer(ephemeral=True)

        # Find all roles permitted in guild for this command.
        identifier = DICT_OF_ALL_COMMANDS.get(command)
        permission_ids = list()
        permission_ids = get_lineage_paths(list(identifier.split('.')), permission_ids)
        results = get_permitted_roles_bulk(DATABASE, str(ctx.guild.id), permission_ids)
        if not results:
            await ctx.respond(f'No non-admin permitted roles found for `{command}`.')
            return

        # Parse role identifiers into actual objects.
        role_ids = results.get('role_id')
        roles = list()
        for role_id in role_ids:
            role_obj = ctx.guild.get_role(int(role_id))
            roles.append(role_obj.mention)
        roles = sorted(roles)
        
        # Print roles that are able to run command.
        list_separator = "\n • "
        await ctx.respond(f"Non-admin roles with access to `{command}`: {list_separator}{list_separator.join(roles)}")

    # List commands by role.
    @guild.command(
        name='commands', 
        description="List all commands able to executed by a role.",
        options=[
            discord.Option(discord.Role, name='role', description='Role to list command permissions for.')
        ]
    )
    @commands.check(CHECKS.user_has_privilege)
    async def command(self, ctx: discord.ApplicationContext, role: discord.Role):
        self.log.info('Command "/guild commands" was invoked')
        
        # Defer response until processing is done.
        await ctx.defer(ephemeral=True)

        # Find all commands this role has access to.
        results = get_role_permissions(DATABASE, str(role.id))
        if not results:
            await ctx.respond(f'{role.mention} has no non-admin access to any commands.')
            return
        
        # Parse raw permission identifiers into a command list.
        role_permissions = results.get('permission_id')
        command_list = sorted([f"`{DICT_OF_ALL_PERMISSIONS.get(permission)}`" for permission in role_permissions])

        # Print roles that are able to run command.
        list_separator = "\n • "
        await ctx.respond(f"{role.mention} has non-admin access to: {list_separator}{list_separator.join(command_list)}")

    # Block users from basic clan commands.
    @guild.command(
        name='block',
        description='Block user from clan-related interaction with Ecumene.',
        options=[
            discord.Option(discord.Member, name='user', description='User to block.')
        ]
    )
    @commands.check(CHECKS.user_has_privilege)
    async def block(self, ctx: discord.ApplicationContext, user: discord.Member):
        self.log.info('Command "/guild block" was invoked')

        # Defer response until processing is done.
        await ctx.defer(ephemeral=True)

        # You cannot block yourself.
        if user.id == ctx.author.id:
            await ctx.respond('You cannot block yourself.')
            return

        # You cannot block the guild owner or people with manage permissions.
        if user.guild_permissions.manage_guild or ctx.guild.owner_id == user.id:
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

    # Unblock users from basic clan commands.
    @guild.command(
        name='unblock',
        description='Unblock user from clan-related interaction with Ecumene.',
        options=[
            discord.Option(discord.Member, name='user', description='User to unblock.')
        ]
    )
    @commands.check(CHECKS.user_has_privilege)
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
    @reset.error
    @clear_role.error
    @clear_command.error
    @roles.error
    @command.error
    @block.error
    @unblock.error
    async def guild_error(self, ctx: discord.ApplicationContext, error):
        self.log.info(error)
        if isinstance(error, CheckFailure):
            await ctx.respond('Insufficient privileges to perform this action.', ephemeral=True)
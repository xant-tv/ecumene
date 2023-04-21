import discord

from discord.commands import slash_command, SlashCommandGroup
from discord.ext import commands

from bot.core.checks import EcumeneCheck, get_lineage_paths
from bot.core.routines import routine_before, routine_after, routine_error
from bot.core.shared import DATABASE, DICT_OF_ALL_GRANTABLE_COMMANDS, DICT_OF_ALL_GRANTABLE_PERMISSIONS, NOTIFICATION_TYPES
from db.query.members import check_blacklist, add_user_to_blacklist, remove_user_from_blacklist
from db.query.channels import insert_or_update_channel, select_channel, delete_channel, get_channel_configuration
from db.query.permissions import \
    select_permission, \
    insert_permission, \
    delete_permission, \
    get_permitted_roles_bulk, \
    get_role_permissions, \
    nuke_permissions, \
    clear_permissions_by_role, \
    clear_permissions_by_command
from util.enum import AuditRecordType

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
            discord.Option(str, name='command', description='Command to grant permissions for.', choices=sorted(DICT_OF_ALL_GRANTABLE_COMMANDS.keys()))
        ]
    )
    @commands.check(CHECKS.guild_is_not_blacklisted)
    @commands.check(CHECKS.user_has_privilege)
    async def grant(self, ctx: discord.ApplicationContext, role: discord.Role, command: str):

        # Defer response until processing is done.
        await ctx.defer(ephemeral=True)

        # If role can manage guild, this doesn't need to do anything.
        if role.permissions.manage_guild:
            await ctx.respond(f'{role.mention} already has access to `{command}`.')
            await routine_after(ctx, AuditRecordType.SUCCESS)
            return

        # Check if permission exists first.
        identifier = DICT_OF_ALL_GRANTABLE_COMMANDS.get(command)
        permission = select_permission(DATABASE, str(ctx.guild.id), str(role.id), identifier)
        if permission:
            # Permission already exists.
            await ctx.respond(f'{role.mention} already has access to `{command}`.')
            await routine_after(ctx, AuditRecordType.SUCCESS)
            return

        # Create the permission.
        insert_permission(DATABASE, str(ctx.guild.id), str(role.id), identifier)
        await ctx.respond(f'Granted access to `{command}` to {role.mention}.')
        await routine_after(ctx, AuditRecordType.SUCCESS)

    # Revoker function.
    @guild.command(
        name='revoke', 
        description="Revoke permission from a role to execute a command.",
        options=[
            discord.Option(discord.Role, name='role', description="Role to revoke permissions from."),
            discord.Option(str, name='command', description='Command to revoke access to.', choices=sorted(DICT_OF_ALL_GRANTABLE_COMMANDS.keys()))
        ]
    )
    @commands.check(CHECKS.guild_is_not_blacklisted)
    @commands.check(CHECKS.user_has_privilege)
    async def revoke(self, ctx: discord.ApplicationContext, role: discord.Role, command: str):

        # Defer response until processing is done.
        await ctx.defer(ephemeral=True)

        # If role can manage guild, this doesn't need to do anything.
        if role.permissions.manage_guild:
            await ctx.respond(f'Cannot revoke `{command}` privileges from {role.mention}.')
            await routine_after(ctx, AuditRecordType.SUCCESS)
            return

        # Check if permission exists first.
        identifier = DICT_OF_ALL_GRANTABLE_COMMANDS.get(command)
        permission = select_permission(DATABASE, str(ctx.guild.id), str(role.id), identifier)
        if not permission:
            # Permission does not exist.
            await ctx.respond(f'No permission for {role.mention} for `{command}`. Nothing to revoke.')
            await routine_after(ctx, AuditRecordType.SUCCESS)
            return

        # Create the permission.
        delete_permission(DATABASE, str(ctx.guild.id), str(role.id), identifier)
        await ctx.respond(f'Revoked access to `{command}` from {role.mention}.')
        await routine_after(ctx, AuditRecordType.SUCCESS)

    # Clear permissions from role.
    @clear.command(
        name='role', 
        description="Clear all permissions from a role",
        options=[
            discord.Option(discord.Role, name='role', description="Role to clear permissions from.")
        ]
    )
    @commands.check(CHECKS.guild_is_not_blacklisted)
    @commands.check(CHECKS.user_has_privilege)
    async def clear_role(self, ctx: discord.ApplicationContext, role: discord.Role):

        # Defer response until processing is done.
        await ctx.defer(ephemeral=True)

        # Clear by role.
        clear_permissions_by_role(DATABASE, str(ctx.guild.id), str(role.id))
        await ctx.respond(f'Cleared all permissions for {role.mention}.')
        await routine_after(ctx, AuditRecordType.SUCCESS)

    # Clear all permissions from command.
    @clear.command(
        name='command', 
        description="Clear all permissions from a command",
        options=[
            discord.Option(str, name='command', description="Command to clear permissions from.", choices=sorted(DICT_OF_ALL_GRANTABLE_COMMANDS.keys()))
        ]
    )
    @commands.check(CHECKS.guild_is_not_blacklisted)
    @commands.check(CHECKS.user_has_privilege)
    async def clear_command(self, ctx: discord.ApplicationContext, command: str):

        # Defer response until processing is done.
        await ctx.defer(ephemeral=True)

        # Get command and clear.
        identifier = DICT_OF_ALL_GRANTABLE_COMMANDS.get(command)
        clear_permissions_by_command(DATABASE, str(ctx.guild.id), identifier)
        await ctx.respond(f'Cleared all permissions for `{command}`.')
        await routine_after(ctx, AuditRecordType.SUCCESS)

    # Nuke all permissions.
    @clear.command(
        name='all', 
        description="Reset all configured permissions for the entire server."
    )
    @commands.check(CHECKS.guild_is_not_blacklisted)
    @commands.check(CHECKS.user_has_privilege)
    async def reset(self, ctx: discord.ApplicationContext):

        # Defer response until processing is done.
        await ctx.defer(ephemeral=True)

        # Create the permission.
        nuke_permissions(DATABASE, str(ctx.guild.id))
        await ctx.respond(f'All permissions on server have been nuked.')
        await routine_after(ctx, AuditRecordType.SUCCESS)

    # List roles by command.
    @guild.command(
        name='roles', 
        description="List all roles able to execute a command.",
        options=[
            discord.Option(str, name='command', description='Command to list role permissions for.', choices=sorted(DICT_OF_ALL_GRANTABLE_COMMANDS.keys()))
        ]
    )
    @commands.check(CHECKS.guild_is_not_blacklisted)
    @commands.check(CHECKS.user_has_privilege)
    async def roles(self, ctx: discord.ApplicationContext, command: str):

        # Defer response until processing is done.
        await ctx.defer(ephemeral=True)

        # Find all roles permitted in guild for this command.
        identifier = DICT_OF_ALL_GRANTABLE_COMMANDS.get(command)
        permission_ids = list()
        permission_ids = get_lineage_paths(list(identifier.split('.')), permission_ids)
        results = get_permitted_roles_bulk(DATABASE, str(ctx.guild.id), permission_ids)
        if not results:
            await ctx.respond(f'No non-admin permitted roles found for `{command}`.')
            await routine_after(ctx, AuditRecordType.SUCCESS)
            return

        # Parse role identifiers into actual objects.
        role_ids = results.get('role_id')
        roles = list()
        for role_id in role_ids:
            role_obj = ctx.guild.get_role(int(role_id))
            if not role_obj:
                continue
            roles.append(role_obj.mention)
        roles = sorted(roles)
        if not roles:
            await ctx.respond(f'No non-admin permitted roles found for `{command}`.')
            await routine_after(ctx, AuditRecordType.SUCCESS)
            return

        # Print roles that are able to run command.
        list_separator = "\n • "
        await ctx.respond(f"Non-admin roles with access to `{command}`: {list_separator}{list_separator.join(roles)}")
        await routine_after(ctx, AuditRecordType.SUCCESS)

    # List commands by role.
    @guild.command(
        name='commands', 
        description="List all commands able to executed by a role.",
        options=[
            discord.Option(discord.Role, name='role', description='Role to list command permissions for.')
        ]
    )
    @commands.check(CHECKS.guild_is_not_blacklisted)
    @commands.check(CHECKS.user_has_privilege)
    async def cmds(self, ctx: discord.ApplicationContext, role: discord.Role):
        
        # Defer response until processing is done.
        await ctx.defer(ephemeral=True)

        # Find all commands this role has access to.
        results = get_role_permissions(DATABASE, str(role.id))
        if not results:
            await ctx.respond(f'{role.mention} has no non-admin access to any commands.')
            await routine_after(ctx, AuditRecordType.SUCCESS)
            return
        
        # Parse raw permission identifiers into a command list.
        role_permissions = results.get('permission_id')
        command_list = sorted([f"`{DICT_OF_ALL_GRANTABLE_PERMISSIONS.get(permission)}`" for permission in role_permissions])

        # Print roles that are able to run command.
        list_separator = "\n • "
        await ctx.respond(f"{role.mention} has non-admin access to: {list_separator}{list_separator.join(command_list)}")
        await routine_after(ctx, AuditRecordType.SUCCESS)

    # Block users from basic clan commands.
    @guild.command(
        name='block',
        description='Block user from clan-related interaction with Ecumene.',
        options=[
            discord.Option(discord.Member, name='user', description='User to block.')
        ]
    )
    @commands.check(CHECKS.guild_is_not_blacklisted)
    @commands.check(CHECKS.user_has_privilege)
    async def block(self, ctx: discord.ApplicationContext, user: discord.Member):

        # Defer response until processing is done.
        await ctx.defer(ephemeral=True)

        # You cannot block yourself.
        if user.id == ctx.author.id:
            await ctx.respond('You cannot block yourself.')
            await routine_after(ctx, AuditRecordType.FAILED_CONTEXT)
            return

        # You cannot block the guild owner or people with manage permissions.
        if user.guild_permissions.manage_guild or ctx.guild.owner_id == user.id:
            await ctx.respond('You do not have permissions to block this person.')
            await routine_after(ctx, AuditRecordType.FAILED_CONTEXT)
            return

        # Check if the user is already blocked.
        blacklisted = check_blacklist(DATABASE, str(ctx.guild.id), str(user.id))
        if blacklisted:
            await ctx.respond(f"User {user.mention} is already blocked in this server.")
            await routine_after(ctx, AuditRecordType.SUCCESS)
            return

        # Add user to blacklist.
        add_user_to_blacklist(DATABASE, str(ctx.guild.id), str(user.id))
        await ctx.respond(f"User {user.mention} added to server block list.")
        await routine_after(ctx, AuditRecordType.SUCCESS)

    # Unblock users from basic clan commands.
    @guild.command(
        name='unblock',
        description='Unblock user from clan-related interaction with Ecumene.',
        options=[
            discord.Option(discord.Member, name='user', description='User to unblock.')
        ]
    )
    @commands.check(CHECKS.guild_is_not_blacklisted)
    @commands.check(CHECKS.user_has_privilege)
    async def unblock(self, ctx: discord.ApplicationContext, user: discord.Member): 

        # Defer response until processing is done.
        await ctx.defer(ephemeral=True)       

        # Check if the user is already blocked.
        blacklisted = check_blacklist(DATABASE, str(ctx.guild.id), str(user.id))
        if not blacklisted:
            await ctx.respond(f"User {user.mention} is not blocked in this server.")
            await routine_after(ctx, AuditRecordType.SUCCESS)
            return

        # Add user to blacklist.
        remove_user_from_blacklist(DATABASE, str(ctx.guild.id), str(user.id))
        await ctx.respond(f"User {user.mention} removed from server block list.")
        await routine_after(ctx, AuditRecordType.SUCCESS)

    # Set up a notification channel.
    @guild.command(
        name='notify',
        description='Set channel for receiving notification posts.',
        options=[
            discord.Option(discord.TextChannel, name='channel', description='Target channel.'),
            discord.Option(str, name='purpose', description='Type of notifications to receive.', choices=NOTIFICATION_TYPES, required=False)
        ]
    )
    @commands.check(CHECKS.guild_is_not_blacklisted)
    @commands.check(CHECKS.user_has_privilege)
    async def notify(self, ctx: discord.ApplicationContext, channel: discord.TextChannel, purpose: str):

        # Defer response until processing is done.
        await ctx.defer(ephemeral=True)

        # Purposes to attach to channel.
        purposes = NOTIFICATION_TYPES
        if purpose:
            purposes = [purpose]
        
        # Insert or update a record for every purpose for this channel.
        for p in purposes:
            insert_or_update_channel(DATABASE, str(ctx.guild.id), str(channel.id), p)

        # List all notifications in this server.
        result = get_channel_configuration(DATABASE, str(ctx.guild.id))
        if not result:
            await ctx.respond(f"There are no configured notification channels for this server.")
            await routine_after(ctx, AuditRecordType.FAILED_CONTEXT)
            return

        c_cfgs = zip(result.get('channel_id'), result.get('purpose'))
        c_outputs = []
        for c_id, c_purpose in c_cfgs:
            c = ctx.guild.get_channel(int(c_id))
            if not c:
                delete_channel(DATABASE, str(ctx.guild.id), str(c_id), c_purpose)
                continue
            c_outputs.append(f"`{c_purpose}` → {c.mention}")

        # Somehow there were no channels added.
        if not c_outputs:
            await ctx.respond(f"There are no configured notification channels for this server.")
            await routine_after(ctx, AuditRecordType.FAILED_CONTEXT)
            return
        
        # Respond to request.
        list_separator = "\n • "
        await ctx.respond(f"Notification configuration for this server: {list_separator}{list_separator.join(c_outputs)}")
        await routine_after(ctx, AuditRecordType.SUCCESS)

    # Set up a notification channel.
    @guild.command(
        name='silence',
        description='Disable notification posts for a certain channel and purpose.',
        options=[
            discord.Option(discord.TextChannel, name='channel', description='Target channel.'),
            discord.Option(str, name='purpose', description='Type of notifications to disable.', choices=NOTIFICATION_TYPES, required=False)
        ]
    )
    @commands.check(CHECKS.guild_is_not_blacklisted)
    @commands.check(CHECKS.user_has_privilege)
    async def silence(self, ctx: discord.ApplicationContext, channel: discord.TextChannel, purpose: str):

        # Defer response until processing is done.
        await ctx.defer(ephemeral=True)

        # Purposes to attach to channel.
        purposes = NOTIFICATION_TYPES
        if purpose:
            purposes = [purpose]
        
        # Insert or update a record for every purpose for this channel.
        for p in purposes:
            delete_channel(DATABASE, str(ctx.guild.id), str(channel.id), p)

        # List all notifications in this server.
        result = get_channel_configuration(DATABASE, str(ctx.guild.id))
        if not result:
            await ctx.respond(f"There are no configured notification channels for this server.")
            await routine_after(ctx, AuditRecordType.SUCCESS)
            return

        c_cfgs = zip(result.get('channel_id'), result.get('purpose'))
        c_outputs = []
        for c_id, c_purpose in c_cfgs:
            c = ctx.guild.get_channel(int(c_id))
            if not c:
                delete_channel(DATABASE, str(ctx.guild.id), str(c_id), c_purpose)
                continue
            c_outputs.append(f"`{c_purpose}` → {c.mention}")

        # Respond to request - assumes successful for now.
        if not c_outputs:
            await ctx.respond(f"There are no configured notification channels for this server.")
            await routine_after(ctx, AuditRecordType.SUCCESS)
            return
        
        # Respond to request.
        list_separator = "\n • "
        await ctx.respond(f"Notification configuration for this server: {list_separator}{list_separator.join(c_outputs)}")
        await routine_after(ctx, AuditRecordType.SUCCESS)

    @grant.before_invoke
    @revoke.before_invoke
    @reset.before_invoke
    @clear_role.before_invoke
    @clear_command.before_invoke
    @roles.before_invoke
    @cmds.before_invoke
    @block.before_invoke
    @unblock.before_invoke
    @notify.before_invoke
    @silence.before_invoke
    async def guild_before(self, ctx: discord.ApplicationContext):
        await routine_before(ctx, self.log)

    @grant.error
    @revoke.error
    @reset.error
    @clear_role.error
    @clear_command.error
    @roles.error
    @cmds.error
    @block.error
    @unblock.error
    @notify.error
    @silence.error
    async def guild_error(self, ctx: discord.ApplicationContext, error):
        await routine_error(ctx, self.log, error)
import discord

from discord.commands import slash_command, SlashCommandGroup
from discord.ext import commands

from bot.core.checks import EcumeneCheck
from bot.core.routines import routine_before, routine_after, routine_error
from bot.core.shared import DATABASE, BNET, DICT_OF_ALL_COMMAND_GROUPS
from db.query.audit import \
    get_audit_records_with_period, \
    get_audit_records_with_command_and_period, \
    get_audit_records_with_user_and_period, \
    get_audit_records_with_target_and_period
from util.data import make_structure, format_audit_records
from util.enum import AuditRecordType
from util.encrypt import generate_local
from util.local import file_path, delete_file, write_file
from util.time import get_current_time

AUDIT_TIME_PERIODS = {
    'Last Day': 24*60*60,
    'Last Week': 7*24*60*60,
    'Last Month': 31*24*60*60,
    'Last Year': 366*24*60*60
}
CHECKS = EcumeneCheck()

class Audit(commands.Cog):
    """
    Cog holding all auditing functions:
      - /audit all <period> (gets audit logs from period to now)
      - /audit command <command> <period> (gets audit logs for a specific command from period to now)
      - /audit user <user> <period> (gets audit logs for a specific user from period to now)
      - /audit target <user> <period> (gets audit logs that affected a specific target from period to now)
    """
    def __init__(self, log):
        self.log = log
        super().__init__()

    # Define a top-level command group.
    audit = SlashCommandGroup(
        "audit", 
        "Audit bot functionality and usage history."
    )

    @audit.command(
        name='all',
        description='Get all audit logs within the specified period.',
        options=[
            discord.Option(str, name='period', description='Time period to query for audit logs.', choices=AUDIT_TIME_PERIODS.keys())
        ]
    )
    @commands.check(CHECKS.guild_is_not_blacklisted)
    @commands.check(CHECKS.user_has_privilege)
    async def period(self, ctx: discord.ApplicationContext, period: str):
        
        # Defer response until processing is done.
        await ctx.defer()

        # Obtain the equivalent lookback from select period.
        lookback_seconds = AUDIT_TIME_PERIODS.get(period, 0)
        audit_records = get_audit_records_with_period(DATABASE, str(ctx.guild_id), lookback_seconds)

        # If no records, we can exit quickly.
        if not audit_records:
            await ctx.respond('There are no available audit records for this period.')
            await routine_after(ctx, AuditRecordType.SUCCESS)
            return

        # Make structure, format and limit output.
        struct = make_structure(audit_records)
        output = format_audit_records(struct)

        # Temporarily store this file locally.
        uid = generate_local()
        fpath = file_path(f"audit_all_{uid}.csv")
        self.log.info(f"Export structure -> {fpath} ({output.shape[0]} records)")
        write_file(output, fpath)
        
        # Attach this file into the message.
        # Delete from local cache.
        await ctx.respond(file=discord.File(fpath))
        delete_file(fpath)
        await routine_after(ctx, AuditRecordType.SUCCESS)

    @audit.command(
        name='command',
        description='Get all audit logs for a specific command within the specified period.',
        options=[
            discord.Option(str, name='period', description='Time period to query for audit logs.', choices=AUDIT_TIME_PERIODS.keys()),
            discord.Option(str, name='command', description='Specific command to query for audit logs.', choices=sorted(DICT_OF_ALL_COMMAND_GROUPS.keys()))
        ]
    )
    @commands.check(CHECKS.guild_is_not_blacklisted)
    @commands.check(CHECKS.user_has_privilege)
    async def cmd(self, ctx: discord.ApplicationContext, period: str, command: str):
        
        # Defer response until processing is done.
        await ctx.defer()

        # Obtain the equivalent lookback and command identifier from selections.
        lookback_seconds = AUDIT_TIME_PERIODS.get(period, 0)
        command_id = DICT_OF_ALL_COMMAND_GROUPS.get(command, '%')
        audit_records = get_audit_records_with_command_and_period(DATABASE, str(ctx.guild_id), lookback_seconds, command_id)

        # If no records, we can exit quickly.
        if not audit_records:
            await ctx.respond('There are no available audit records for this command and period.')
            await routine_after(ctx, AuditRecordType.SUCCESS)
            return

        # Make structure, format and limit output.
        struct = make_structure(audit_records)
        output = format_audit_records(struct)

        # Temporarily store this file locally.
        uid = generate_local()
        fpath = file_path(f"audit_command_{uid}.csv")
        self.log.info(f"Export structure -> {fpath} ({output.shape[0]} records)")
        write_file(output, fpath)
        
        # Attach this file into the message.
        # Delete from local cache.
        await ctx.respond(file=discord.File(fpath))
        delete_file(fpath)
        await routine_after(ctx, AuditRecordType.SUCCESS)

    @audit.command(
        name='user',
        description='Get all audit logs for a specific user within the specified period.',
        options=[
            discord.Option(str, name='period', description='Time period to query for audit logs.', choices=AUDIT_TIME_PERIODS.keys()),
            discord.Option(discord.User, name='user', description='Specific user to query for audit logs.')
        ]
    )
    @commands.check(CHECKS.guild_is_not_blacklisted)
    @commands.check(CHECKS.user_has_privilege)
    async def user(self, ctx: discord.ApplicationContext, period: str, user: discord.User):
        
        # Defer response until processing is done.
        await ctx.defer()

        # Obtain the equivalent lookback and user identifier from selections.
        lookback_seconds = AUDIT_TIME_PERIODS.get(period, 0)
        user_id = str(user.id)
        audit_records = get_audit_records_with_user_and_period(DATABASE, str(ctx.guild_id), lookback_seconds, user_id)

        # If no records, we can exit quickly.
        if not audit_records:
            await ctx.respond('There are no available audit records for this user and period.')
            await routine_after(ctx, AuditRecordType.SUCCESS)
            return

        # Make structure, format and limit output.
        struct = make_structure(audit_records)
        output = format_audit_records(struct)

        # Temporarily store this file locally.
        uid = generate_local()
        fpath = file_path(f"audit_user_{uid}.csv")
        self.log.info(f"Export structure -> {fpath} ({output.shape[0]} records)")
        write_file(output, fpath)
        
        # Attach this file into the message.
        # Delete from local cache.
        await ctx.respond(file=discord.File(fpath))
        delete_file(fpath)
        await routine_after(ctx, AuditRecordType.SUCCESS)

    @audit.command(
        name='target',
        description='Get all audit logs impacting a specific target within the specified period.',
        options=[
            discord.Option(str, name='period', description='Time period to query for audit logs.', choices=AUDIT_TIME_PERIODS.keys()),
            discord.Option(discord.User, name='target', description='Specific target to query for audit logs.')
        ]
    )
    @commands.check(CHECKS.guild_is_not_blacklisted)
    @commands.check(CHECKS.user_has_privilege)
    async def target(self, ctx: discord.ApplicationContext, period: str, target: discord.User):
        
        # Defer response until processing is done.
        await ctx.defer()

        # Obtain the equivalent lookback and user identifier from selections.
        lookback_seconds = AUDIT_TIME_PERIODS.get(period, 0)
        target_id = str(target.id)
        audit_records = get_audit_records_with_target_and_period(DATABASE, str(ctx.guild_id), lookback_seconds, target_id)

        # If no records, we can exit quickly.
        if not audit_records:
            await ctx.respond('There are no available audit records for this target and period.')
            await routine_after(ctx, AuditRecordType.SUCCESS)
            return

        # Make structure, format and limit output.
        struct = make_structure(audit_records)
        output = format_audit_records(struct)

        # Temporarily store this file locally.
        uid = generate_local()
        fpath = file_path(f"audit_target_{uid}.csv")
        self.log.info(f"Export structure -> {fpath} ({output.shape[0]} records)")
        write_file(output, fpath)
        
        # Attach this file into the message.
        # Delete from local cache.
        await ctx.respond(file=discord.File(fpath))
        delete_file(fpath)
        await routine_after(ctx, AuditRecordType.SUCCESS)

    @period.before_invoke
    @cmd.before_invoke
    @user.before_invoke
    @target.before_invoke
    async def audit_before(self, ctx: discord.ApplicationContext):
        await routine_before(ctx, self.log)

    @period.error
    @cmd.error
    @user.error
    @target.error
    async def audit_error(self, ctx: discord.ApplicationContext, error):
        await routine_error(ctx, self.log, error)
import discord

from bot.core.history import generate_command_record
from bot.core.shared import DATABASE
from db.query.audit import insert_audit_record, update_audit_record
from util.enum import AuditRecordType

async def routine_before(ctx: discord.ApplicationContext, log):
    record = generate_command_record(ctx)
    insert_audit_record(DATABASE, record.as_data())
    log.info(f'Command "{record.command_id}" was invoked')

async def routine_after(ctx: discord.ApplicationContext, status):
    # Deliberately call such that the record is stubbed (i.e. some values are not calculated).
    # We only need to update status really so only core values need to be present here.
    record = generate_command_record(ctx, status=status, stub=True)
    update_audit_record(DATABASE, 'record_id', record.as_data())

async def routine_error(ctx: discord.ApplicationContext, log, error):
    log.info(error)
    if isinstance(error, discord.CheckFailure):
        # This error will be reached before the @before_invoke routine is called.
        # As a result, it will not have an existing record.
        # Generate and insert a failure record here directly instead.
        record = generate_command_record(ctx, status=AuditRecordType.FAILED_CHECK)
        insert_audit_record(DATABASE, record.as_data())
        await ctx.respond('Insufficient privileges to perform this action.', ephemeral=True)
        return
    # Handle all other unhandled exceptions here.
    # This will occur after @before_invoke is called.
    # We can call the custom @after_invoke with our own error.
    await routine_after(ctx, AuditRecordType.FAILED_ERROR)
    await ctx.respond("An error occurred. Please don't yell at the developer!")
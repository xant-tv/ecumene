from sqlalchemy import select, update

from db.client import DatabaseService
from util.enum import AuditRecordType
from util.time import get_current_time

def insert_audit_record(service: DatabaseService, data):
    return service.insert('history', data)

def update_audit_record(service: DatabaseService, on, data):
    """Update audit details based 'on' column."""
    # Retain match identifier separately.
    # Pop this out of the dictionary because it shouldn't be part of the values payload.
    match_id = data.get(on)
    data.pop(on, None)
    table = service.retrieve_model('history')
    qry = (
        update(table).
            where(getattr(table.c, on) == match_id).
            values(data)
    )
    result = service.execute(qry)
    return result

def get_audit_records_with_period(service: DatabaseService, guild_id, lookback):
    """Get all records with some lookback period."""
    table = service.retrieve_model('history')
    min_time = get_current_time() - (1000 * lookback) # Subtract lookback from current.
    qry = (
        select(table).
            filter(
                # This is an "and" operator on both conditions.
                table.c.guild_id == guild_id,
                table.c.invoked_at >= min_time,
                table.c.status != AuditRecordType.PENDING.value
            )
    )
    result = service.select(qry)
    return result

def get_audit_records_with_command_and_period(service: DatabaseService, guild_id, lookback, command_id):
    """Get all records with some command identifier and lookback period."""
    table = service.retrieve_model('history')
    min_time = get_current_time() - (1000 * lookback) # Subtract lookback from current.
    qry = (
        select(table).
            filter(
                # This is an "and" operator on both conditions.
                table.c.guild_id == guild_id,
                table.c.command_id.like(command_id),
                table.c.invoked_at >= min_time,
                table.c.status != AuditRecordType.PENDING.value
            )
    )
    result = service.select(qry)
    return result

def get_audit_records_with_user_and_period(service: DatabaseService, guild_id, lookback, discord_id):
    """Get all records with some user identifier and lookback period."""
    table = service.retrieve_model('history')
    min_time = get_current_time() - (1000 * lookback) # Subtract lookback from current.
    qry = (
        select(table).
            filter(
                # This is an "and" operator on both conditions.
                table.c.guild_id == guild_id,
                table.c.discord_id == discord_id,
                table.c.invoked_at >= min_time,
                table.c.status != AuditRecordType.PENDING.value
            )
    )
    result = service.select(qry)
    return result

def get_audit_records_with_target_and_period(service: DatabaseService, guild_id, lookback, target_id):
    """Get all records with some specific target and lookback period."""
    table = service.retrieve_model('history')
    min_time = get_current_time() - (1000 * lookback) # Subtract lookback from current.
    qry = (
        select(table).
            filter(
                # This is an "and" operator on both conditions.
                table.c.guild_id == guild_id,
                table.c.command_options.like(f"%={target_id}%"),
                table.c.invoked_at >= min_time,
                table.c.status != AuditRecordType.PENDING.value
            )
    )
    result = service.select(qry)
    return result

def get_expired_records(service: DatabaseService, process_buffer):
    """Get all expired records."""
    table = service.retrieve_model('history')
    expiry_time = get_current_time() - (1000 * process_buffer) # Apply a small buffer - commands time out after 15 minutes anyway.
    qry = (
        select(table).
            filter(
                # This is an "and" operator on both conditions.
                table.c.invoked_at <= expiry_time,
                table.c.status == AuditRecordType.PENDING.value
            )
    )
    result = service.select(qry)
    return result

def clean_expired_records(service: DatabaseService, process_buffer):
    """Set status for all expired records."""
    table = service.retrieve_model('history')
    expiry_time = get_current_time() - (1000 * process_buffer) # As above.
    data = {
        'status': AuditRecordType.EXPIRED_OR_UNHANDLED.value
    }
    qry = (
        update(table).
            where(table.c.invoked_at <= expiry_time).
            where(table.c.status == AuditRecordType.PENDING.value).
            values(data)
    )
    result = service.execute(qry)
    return result
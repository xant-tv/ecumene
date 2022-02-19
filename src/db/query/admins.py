from sqlalchemy import select, update, delete

from db.client import DatabaseService
from util.time import get_current_time

def get_admin_by_id(service: DatabaseService, target_column, id):
    table = service.retrieve_model('admins')
    qry = (
        select(table).
            where(getattr(table.c, target_column) == id)
    )
    result = service.select(qry)
    return result

# Evaluate if this is necessary. 
# We probably want some way of culling inactive or unused administrator accounts.
def delete_admin_by_id(service: DatabaseService, target_column, id):
    pass

def insert_admin_details(service: DatabaseService, data):
    return service.insert('admins', data)

def update_admin_details(service: DatabaseService, on, data):
    """Update admin details based 'on' column."""
    # Retain match identifier separately.
    # Pop this out of the dictionary because it shouldn't be part of the values payload.
    match_id = data.get(on)
    data.pop(on, None)
    table = service.retrieve_model('admins')
    qry = (
        update(table).
            where(getattr(table.c, on) == match_id).
            values(data)
    )
    result = service.execute(qry)
    return result
    
def insert_or_update_admin(service: DatabaseService, data):
    """Check to see if administrator details exist before updating."""
    # Evaluate length of returns. If at least one record is returned then match.
    match_admin = get_admin_by_id(service, 'admin_id', data.get('admin_id'))

    # If administrator exists, then run update.
    if match_admin:
        return update_admin_details(service, 'admin_id', data)

    # New admin details.
    return insert_admin_details(service, data)

def get_tokens_to_refresh(service: DatabaseService, delay, process_buffer):
    table = service.retrieve_model('admins')
    access_expiry_time = get_current_time() + (1000 * delay) + (1000 * process_buffer) # Add a five minute buffer.
    refresh_expiry_time = get_current_time() + (1000 * process_buffer) # Use the same buffer.
    qry = (
        select(table).
            filter(
                table.c.access_expires_at <= access_expiry_time,
                table.c.refresh_expires_at > refresh_expiry_time
            )
    )
    result = service.select(qry)
    return result

def get_orphans(service: DatabaseService):
    """Find all administrator credentials not used by a clan."""
    admins = service.retrieve_model('admins')
    clans = service.retrieve_model('clans')
    subqry = (
        select(clans.c.admin_id) # Only need the admin_id column from this table.
    )
    qry = (
        select(admins).
            where(admins.c.admin_id.not_in(subqry)) # Check the not_in condition using the subquery.
    )
    result = service.select(qry)
    return result

def delete_orphans(service: DatabaseService):
    """Remove all administrator credentials not used by a clan."""
    admins = service.retrieve_model('admins')
    clans = service.retrieve_model('clans')
    subqry = (
        select(clans.c.admin_id)
    )
    # Same as the getter but executes a delete this time.
    qry = (
        delete(admins).
            where(admins.c.admin_id.not_in(subqry))
    )
    result = service.execute(qry)
    return result

def get_dead(service: DatabaseService, process_buffer):
    """Get all dead credentials."""
    table = service.retrieve_model('admins')
    refresh_expiry_time = get_current_time() + (1000 * process_buffer) # Apply a small buffer - no way these refresh any time soon.
    qry = (
        select(table).
            filter(table.c.refresh_expires_at <= refresh_expiry_time)
    )
    result = service.select(qry)
    return result
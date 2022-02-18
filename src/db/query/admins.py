from sqlalchemy import select, update, delete

from db.client import DatabaseService

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
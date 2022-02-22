from sqlalchemy import select, update, delete

from db.client import DatabaseService

def insert_permission(service: DatabaseService, guild_id, role_id, permission_id):
    data = {
        'guild_id': guild_id,
        'role_id': role_id,
        'permission_id': permission_id
    }
    return service.insert('permissions', data)

def delete_permission(service: DatabaseService, guild_id, role_id, permission_id):
    table = service.retrieve_model('permissions')
    qry = (
        delete(table).
            where(table.c.guild_id == guild_id).
            where(table.c.role_id == role_id).
            where(table.c.permission_id == permission_id)
    )
    result = service.execute(qry)
    return result

def select_permission(service: DatabaseService, guild_id, role_id, permission_id):
    table = service.retrieve_model('permissions')
    qry = (
        select(table).
            where(table.c.guild_id == guild_id).
            where(table.c.role_id == role_id).
            where(table.c.permission_id == permission_id)
    )
    result = service.select(qry)
    return result

def get_permitted_roles(service: DatabaseService, guild_id, permission_id):
    """For a command - get the roles that are allowed to run it."""
    table = service.retrieve_model('permissions')
    qry = (
        select(table).
            where(table.c.guild_id == guild_id).
            where(table.c.permission_id == permission_id)
    )
    result = service.select(qry)
    return result

def get_role_permissions(service: DatabaseService, role_id):
    """For a role - get the commands it is able to run."""
    table = service.retrieve_model('permissions')
    qry = (
        select(table).
            where(table.c.role_id == role_id)
    )
    result = service.select(qry)
    return result

def get_permitted_roles_bulk(service: DatabaseService, guild_id, permission_ids):
    """For a list of command identifiers - get all permitted roles."""
    table = service.retrieve_model('permissions')
    qry = (
        select(table).
            where(table.c.guild_id == guild_id).
            where(table.c.permission_id.in_(permission_ids))
    )
    result = service.select(qry)
    return result

def nuke_permissions(service: DatabaseService, guild_id):
    table = service.retrieve_model('permissions')
    qry = (
        delete(table).
            where(table.c.guild_id == guild_id)
    )
    result = service.execute(qry)
    return result

def clear_permissions_by_role(service: DatabaseService, guild_id, role_id):
    table = service.retrieve_model('permissions')
    qry = (
        delete(table).
            where(table.c.guild_id == guild_id).
            where(table.c.role_id == role_id)
    )
    result = service.execute(qry)
    return result

def clear_permissions_by_command(service: DatabaseService, guild_id, permission_id):
    table = service.retrieve_model('permissions')
    qry = (
        delete(table).
            where(table.c.guild_id == guild_id).
            where(table.c.permission_id == permission_id)
    )
    result = service.execute(qry)
    return result
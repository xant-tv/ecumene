from sqlalchemy import select, update, delete

from db.client import DatabaseService

def get_guilds(service: DatabaseService):
    table = service.retrieve_model('headers')
    qry = (
        select(table)
    )
    result = service.select(qry)
    return result

def get_guild_system_role(service: DatabaseService, guild_id):
    table = service.retrieve_model('headers')
    qry = (
        select(table).
            where(table.c.guild_id == guild_id)
    )
    result = service.select(qry)
    return result

def delete_system_role(service: DatabaseService, guild_id):
    table = service.retrieve_model('headers')
    qry = (
        delete(table).
            where(table.c.guild_id == guild_id)
    )
    result = service.execute(qry)
    return result

def publish_system_role(service: DatabaseService, guild_id, role_id):
    data = {
        'guild_id': guild_id,
        'role_id': role_id
    }
    return service.insert('headers', data)
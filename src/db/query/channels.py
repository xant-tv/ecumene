from sqlalchemy import select, update, delete, or_

from db.client import DatabaseService

def select_channel(service: DatabaseService, guild_id, channel_id, purpose):
    table = service.retrieve_model('channels')
    qry = (
        select(table).
            filter(
                # This is an "and" operator on both conditions.
                table.c.guild_id == guild_id,
                table.c.channel_id == channel_id,
                table.c.purpose == purpose
            )
    )
    result = service.select(qry)
    return result

def insert_channel(service: DatabaseService, guild_id, channel_id, purpose):
    data = {
        'guild_id': guild_id,
        'channel_id': channel_id,
        'purpose': purpose
    }
    return service.insert('channels', data)

def delete_channel(service: DatabaseService, guild_id, channel_id, purpose):
    table = service.retrieve_model('channels')
    qry = (
        delete(table).
            filter(
                # This is an "and" operator on both conditions.
                table.c.guild_id == guild_id,
                table.c.channel_id == channel_id,
                table.c.purpose == purpose
            )
    )
    result = service.execute(qry)
    return result

def insert_or_update_channel(service: DatabaseService, guild_id, channel_id, purpose):
    entry = select_channel(service, guild_id, channel_id, purpose)
    if entry:
        # We don't need to do anything but we could replace with an update later.
        return entry
    return insert_channel(service, guild_id, channel_id, purpose)

def get_guild_channels_by_purpose(service: DatabaseService, guild_id, purpose):
    table = service.retrieve_model('channels')
    qry = (
        select(table).
            filter(
                # This is an "and" operator on both conditions.
                table.c.guild_id == guild_id,
                table.c.purpose == purpose
            )
    )
    result = service.select(qry)
    return result

def get_channel_configuration(service: DatabaseService, guild_id):
    table = service.retrieve_model('channels')
    qry = (
        select(table).
            where(table.c.guild_id == guild_id)
    )
    result = service.select(qry)
    return result  

def delete_channel_configuration(service: DatabaseService, guild_id):
    table = service.retrieve_model('channels')
    qry = (
        delete(table).
            where(table.c.guild_id == guild_id)
    )
    result = service.execute(qry)
    return result
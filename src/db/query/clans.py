from sqlalchemy import select, update, delete

from db.client import DatabaseService

def get_clan_in_guild(service: DatabaseService, guild_id, clan_id):
    table = service.retrieve_model('clans')
    qry = (
        select(table).
            where(table.c.guild_id == guild_id).
            where(table.c.clan_id == clan_id)
    )
    result = service.select(qry)
    return result

def insert_clan_details(service: DatabaseService, data):
    return service.insert('clans', data)

def update_clan_details(service: DatabaseService, data):
    # Retain match identifier separately.
    # Pop this out of the dictionary because it shouldn't be part of the values payload.
    guild_id = data.get('guild_id')
    clan_id = data.get('clan_id')
    data.pop('guild_id', None)
    data.pop('clan_id', None)
    table = service.retrieve_model('clans')
    qry = (
        update(table).
            where(table.c.guild_id == guild_id).
            where(table.c.clan_id == clan_id).
            values(data)
    )
    result = service.execute(qry)
    return result

def insert_or_update_clan(service: DatabaseService, data):
    """Check to see if clan is already being tracked in this guild."""
    # Evaluate length of returns. If at least one record is returned then match.
    match_clan = get_clan_in_guild(service, data.get('guild_id'), data.get('clan_id'))

    # If clan exists in guild, run update.
    if match_clan:
        return update_clan_details(service, data)

    # New clan details.
    return insert_clan_details(service, data)
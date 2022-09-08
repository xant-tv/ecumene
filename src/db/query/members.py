from sqlalchemy import select, update, delete, or_

from db.client import DatabaseService

def get_member_by_id(service: DatabaseService, target_column, id):
    table = service.retrieve_model('members')
    qry = (
        select(table).
            where(getattr(table.c, target_column) == id)
    )
    result = service.select(qry)
    return result

def delete_member_by_id(service: DatabaseService, target_column, id):
    table = service.retrieve_model('members')
    qry = (
        delete(table).
            where(getattr(table.c, target_column) == id)
    )
    result = service.execute(qry)
    return result

def insert_member_details(service: DatabaseService, data):
    return service.insert('members', data)

def update_member_details(service: DatabaseService, on, data):
    """Update member details based 'on' column."""
    # Retain match identifier separately.
    # Pop this out of the dictionary because it shouldn't be part of the values payload.
    match_id = data.get(on)
    data.pop(on, None)
    table = service.retrieve_model('members')
    qry = (
        update(table).
            where(getattr(table.c, on) == match_id).
            values(data)
    )
    result = service.execute(qry)
    return result

def insert_or_update_member(service: DatabaseService, data):
    """Check to see if member details exist before updating."""
    # Evaluate length of returns. If at least one record is returned then match.
    match_discord = get_member_by_id(service, 'discord_id', data.get('discord_id'))
    match_destiny = get_member_by_id(service, 'destiny_id', data.get('destiny_id'))

    # If both sets of details exist, delete and then insert fresh?
    # Delete is necessary because the individual matches might actually be for separate records.
    #   i.e. Discord user registers an account which a different discord user had already registered.
    if match_discord and match_destiny:
        discord_id_potentially_removed = set(match_discord.get('discord_id') + match_destiny.get('discord_id'))
        delete_member_by_id(service, 'discord_id', data.get('discord_id'))
        delete_member_by_id(service, 'destiny_id', data.get('destiny_id'))
        return insert_member_details(service, data), discord_id_potentially_removed
    
    # If either _but not both_ then we need to update members data.
    if match_discord:
        discord_id_potentially_removed = set(match_discord.get('discord_id'))
        return update_member_details(service, 'discord_id', data), discord_id_potentially_removed
    if match_destiny:
        discord_id_potentially_removed = set(match_destiny.get('discord_id'))
        return update_member_details(service, 'destiny_id', data), discord_id_potentially_removed

    # New member details.
    return insert_member_details(service, data), None

def get_members_matching(service: DatabaseService, target_column, member_ids):
    table = service.retrieve_model('members')
    qry = (
        select(table).
            where(getattr(table.c, target_column).in_(member_ids))
    )
    result = service.select(qry)
    return result

def get_members_matching_by_all_ids(service: DatabaseService, bnet_ids, destiny_ids):
    table = service.retrieve_model('members')
    qry = (
        select(table).
            where(
                or_(
                    table.c.bnet_id.in_(bnet_ids),
                    table.c.destiny_id.in_(destiny_ids)
                )
            )
    )
    result = service.select(qry)
    return result

def check_blacklist(service: DatabaseService, guild_id, user_id):
    table = service.retrieve_model('blacklist')
    qry = (
        select(table).
            where(table.c.guild_id == guild_id).
            where(table.c.discord_id == user_id)
    )
    result = service.select(qry)
    return result

def add_user_to_blacklist(service: DatabaseService, guild_id, user_id):
    data = {
        'guild_id': guild_id,
        'discord_id': user_id
    }
    return service.insert('blacklist', data)

def remove_user_from_blacklist(service: DatabaseService, guild_id, user_id):
    table = service.retrieve_model('blacklist')
    qry = (
        delete(table).
            where(table.c.guild_id == guild_id).
            where(table.c.discord_id == user_id)
    )
    result = service.execute(qry)
    return result
import pandas as pd

from api.client import DiscordInterface, DiscordInterfaceError
from db.client import DatabaseService
from db.query.headers import get_guilds
from db.query.members import insert_or_update_member
from util.time import get_current_time

API = DiscordInterface()
DB = DatabaseService()

def force_register_user(user_id, destiny_id, destiny_mtype, bnet_id, bnet_mtype):

    # Data package
    data = {
        'discord_id': str(user_id),
        'destiny_id': str(destiny_id),
        'destiny_mtype': destiny_mtype,
        'bnet_id': str(bnet_id),
        'bnet_mtype': bnet_mtype,
        'registered_on': get_current_time()
    }
    _, delete_list = insert_or_update_member(DB, data)
    print('Captured registration request!')

    # Update user roles in all guilds for this new member.
    headers = get_guilds(DB)
    if headers:

        # Unfortunately, we have to do this guild-by-guild.
        # Could take a while at scale, thankfully there are multiple workers!
        for guild_id, role_id in zip(headers.get('guild_id'), headers.get('role_id')):

            # Remove role for any members that we deleted.       
            if delete_list:
                for delete_id in delete_list:
                    if delete_id == user_id: 
                        continue
                    try:
                        API.get_member(guild_id, user_id)
                        API.delete_role_from_member(guild_id, delete_id, role_id)
                    except DiscordInterfaceError as e:
                        # Either member didn't exist in guild or unable to set roles.
                        pass

            # Now try to grant the role for new registration.
            try:
                API.get_member(guild_id, user_id)
                API.add_role_to_member(guild_id, user_id, role_id)
            except DiscordInterfaceError as e:
                # Either member didn't exist in guild or unable to set roles.
                pass
        
        print(f'Proliferated user roles for {user_id} on all guilds!')

def start():

    # Manually structure all people to force sign-up.
    df = pd.read_csv('script/source.csv')
    records = df.to_dict('records')
    for record in records:
        force_register_user(record['user_id'], record['destiny_id'], record['destiny_mtype'], record['bnet_id'], record['bnet_mtype'])
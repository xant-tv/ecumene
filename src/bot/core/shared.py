from db.client import DatabaseService
from bnet.client import BungieInterface

# Get access to dependencies here.
# Some of these cannot be passed into the Cog as they are un-pickleable.
DATABASE = DatabaseService()
BNET = BungieInterface()

# All grantable commands map.
DICT_OF_ALL_COMMANDS = {
    '/clan': 'clan.*',
    '/clan list': 'clan.list',
    '/clan kick': 'clan.kick',
    '/clan promote': 'clan.promote',
    '/clan demote': 'clan.demote',
    '/clan join': 'clan.join'
}
DICT_OF_ALL_PERMISSIONS = {
    i: c for c, i in DICT_OF_ALL_COMMANDS.items() # Inverse dictionary of above.
}
from db.client import DatabaseService
from bnet.client import BungieInterface
from util.local import get_guild_ids

# Get access to dependencies here.
# Some of these cannot be passed into the Cog as they are un-pickleable.
DATABASE = DatabaseService()
BNET = BungieInterface()

GUILDS = get_guild_ids()

# All commands mapped as combinations of:
#  <display>:<internal>
DICT_OF_ALL_COMMANDS = {
    '/admin': 'admin.*',
    '/admin grant': 'admin.grant',
    '/admin revoke': 'admin.revoke',
    '/admin roles': 'admin.roles',
    '/admin command': 'admin.command',
    '/admin register': 'admin.register',
    '/admin message': 'admin.message'
}
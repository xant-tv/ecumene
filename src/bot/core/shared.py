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
    '/guild': 'guild.*',
    '/guild grant': 'guild.grant',
    '/guild revoke': 'guild.revoke',
    '/guild roles': 'guild.roles',
    '/guild command': 'guild.command',
    '/admin': 'admin.*',
    '/admin register': 'admin.register',
    '/admin grant': 'admin.grant',
    '/admin revoke': 'admin.revoke',
    '/admin list': 'admin.list',
}
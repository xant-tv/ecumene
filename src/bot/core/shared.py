from db.client import DatabaseService
from bnet.client import BungieInterface

# Get access to dependencies here.
# Some of these cannot be passed into the Cog as they are un-pickleable.
DATABASE = DatabaseService()
BNET = BungieInterface()

# All commands map.
DICT_OF_ALL_COMMANDS = {
    # <display>:<internal>
    '/guild': 'guild.*',
    '/guild grant': 'guild.grant', # Will need to support these sooner than I thought.
    '/guild revoke': 'guild.revoke',
    '/guild roles': 'guild.roles',
    '/guild command': 'guild.command',
    '/guild block': 'guild.block',
    '/guild unblock': 'guild.unblock',
    '/admin': 'admin.*',
    '/admin register': 'admin.register',
    '/admin grant': 'admin.grant', # Low priority.
    '/admin revoke': 'admin.revoke', # Low priority.
    '/admin list': 'admin.list',
    '/clan': 'clan.*',
    '/clan list': 'clan.list',
    '/clan kick': 'clan.kick',
    '/clan promote': 'clan.promote', # Not sure if these will remain yet.
    '/clan demote': 'clan.demote',
    '/clan join': 'clan.join'
}
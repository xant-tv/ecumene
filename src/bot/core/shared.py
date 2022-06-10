from types import SimpleNamespace

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
    '/clan rank': 'clan.rank',
    '/clan join': 'clan.join',
    '/clan action': 'clan.action',
    '/clan status': 'clan.status',
    '/clan cancel': 'clan.cancel'
}
DICT_OF_ALL_PERMISSIONS = {
    i: c for c, i in DICT_OF_ALL_COMMANDS.items() # Inverse dictionary of above.
}

# Emoji information we want the bot to use.
# These unforunately have to be hardcoded.
EMOJIS = SimpleNamespace(**{
    'destiny': '<:destiny:977602340800565298>',
    'cross_save': '<:cross_save:977576110361542677>',
    'steam': '<:steam:977585822515753020>',
    'playstation': '<:playstation:977584690628288653>',
    'xbox': '<:xbox:977585872344072192>',
    'stadia': '<:stadia:977585850542071818>',
    'blizzard': '<:blizzard:977587177225596999>',
    'discord': '<:discord:977592420940284006>',
    'nitro': '<:nitro:977599227960115230>',
    'owner': '<:owner:977599814080532610>',
    'ecumene': '<:ecumene_round:977596974461247548>'
})

# This reverses the Bungie namespace lookup for platforms.
PLATFORMS = {
    1: 'xbox',
    2: 'playstation',
    3: 'steam',
    4: 'blizzard',
    5: 'stadia'
}

# This reverses the Bungie namespace lookup for member levels.
LEVELS = {
    1: 'Beginner',
    2: 'Member',
    3: 'Admin',
    4: 'Acting Founder',
    5: 'Founder'
}
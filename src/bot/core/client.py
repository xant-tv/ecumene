import os
import discord
import logging

from bot.core.cogs.admin import Admin
from bot.core.cogs.audit import Audit
from bot.core.cogs.clan import Clan
from bot.core.cogs.guild import Guild
from bot.core.cogs.identity import Identity
from bot.core.cogs.example import Example
from util.local import get_guild_ids

class EcumeneBot():
    """
    Bot client that should be used for primary Discord functionality.
    Will hold focus until terminated.
    """

    def __init__(self):
        self.log = logging.getLogger(f'{self.__module__}.{self.__class__.__name__}')
        self.client = discord.Bot(
            allowed_mentions=discord.AllowedMentions.all(), # Can mention all the things!
            debug_guilds=get_guild_ids()
        )
        self.token = os.getenv('DISCORD_TOKEN')

        # Add all commands to bot via their respective Cogs.
        self.client.add_cog(Audit(self.log))
        self.client.add_cog(Guild(self.log))
        self.client.add_cog(Admin(self.log))
        self.client.add_cog(Identity(self.log))
        self.client.add_cog(Clan(self.log))
        # self.client.add_cog(Example(self.log))

        # Add our on-ready event listener.
        self.client.add_listener(
            self.ready, 
            'on_ready'
        )

    async def ready(self):
        """Trigger on bot ready."""
        self.log.info(f'Logged in as {self.client.user} (ID={self.client.user.id})')

    def run(self):
        self.client.run(self.token)
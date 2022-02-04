import os
import discord
import logging

from bot.core.events import EcumeneEventHandler
from bot.core.checks import EcumeneCheckHandler
from bot.core.errors import EcumeneErrorHandler

class EcumeneBot():

    def __init__(self):
        self.log = logging.getLogger(f'{self.__module__}.{self.__class__.__name__}')
        self.client = discord.Bot(
            allowed_mentions=discord.AllowedMentions.all() # Can mention all the things!
        )
        self.token = os.getenv('DISCORD_TOKEN')
        self.events = EcumeneEventHandler()
        self.checks = EcumeneCheckHandler()
        self.errors = EcumeneErrorHandler()

        self.client.add_listener(
            self.ready, 
            'on_ready'
        )

    async def ready(self):
        """Trigger on bot ready."""
        self.log.info(f'Logged in as {self.client.user} (ID={self.client.user.id})')

    def run(self):
        self.client.run(self.token)
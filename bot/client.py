import os
import discord
import logging

import bot.events
import bot.checks
import bot.errors

class Ecumene():

    def __init__(self):
        self.log = logging.getLogger(f'{self.__module__}.{self.__class__.__name__}')
        self.client = discord.Bot()
        self.token = os.getenv('DISCORD_TOKEN')
        self.events = bot.events.EcumeneEventHandler()
        self.checks = bot.checks.EcumeneCheckHandler()
        self.errors = bot.errors.EcumeneErrorHandler()

        self.client.add_listener(
            self.ready, 
            'on_ready'
        )

    async def ready(self):
        """Trigger on bot ready."""
        self.log.info(f'Logged in as {self.client.user} (ID={self.client.user.id})')

    def run(self):
        self.client.run(self.token)
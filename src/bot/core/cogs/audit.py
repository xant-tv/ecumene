import discord

from discord.commands import slash_command, SlashCommandGroup
from discord.commands.errors import CheckFailure
from discord.ext import commands

from bot.core.checks import EcumeneCheck
from bot.core.shared import DATABASE, BNET, DICT_OF_ALL_COMMANDS
from util.time import get_current_time

CHECKS = EcumeneCheck()

class Audit(commands.Cog):
    """
    Cog holding all auditing functions.
    """
    def __init__(self, log):
        self.log = log
        super().__init__()
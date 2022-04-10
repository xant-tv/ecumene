import discord

from discord import CheckFailure
from discord.commands import slash_command, SlashCommandGroup
from discord.ext import commands

from bot.core.checks import EcumeneCheck
from bot.core.shared import DATABASE, BNET, DICT_OF_ALL_COMMANDS
from util.time import get_current_time

CHECKS = EcumeneCheck()

class Audit(commands.Cog):
    """
    Cog holding all auditing functions:
      - /audit all <period> (gets audit logs from period to now)
      - /audit command <command> <period> (gets audit logs for a specific command from period to now)
      - /audit user <user> <period> (gets audit logs for a specific user from period to now)
      - /audit target <user> <period> (gets audit logs that affected a specific target from period to now)
    """
    def __init__(self, log):
        self.log = log
        super().__init__()
import discord

from discord.commands import slash_command, SlashCommandGroup
from discord.commands.errors import CheckFailure
from discord.ext import commands

from bot.core.checks import EcumeneCheck
from bot.core.shared import DATABASE, BNET, GUILDS, DICT_OF_ALL_COMMANDS
from db.query import update_transaction
from util.encrypt import generate_state
from util.time import get_current_time

CHECKS = EcumeneCheck()

class Clan(commands.Cog):
    # CONTAINS /clan and all related subcommands
    pass
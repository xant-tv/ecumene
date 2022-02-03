import os
import yaml
import dotenv
import discord

from distutils.util import strtobool
from logging.config import dictConfig

from bot.client import Ecumene

if __name__ == '__main__':
    
    # Initialise logging.
    fpath = os.path.join('conf', 'log.yml')
    with open(fpath, 'r') as cfile:
        cfg = yaml.load(cfile, Loader=yaml.FullLoader)
    dictConfig(cfg)

    # Load variables from local .env file.
    dotenv.load_dotenv()

    # Force commands onto specific server to push instantly during debug.
    guild = os.getenv('DISCORD_GUILD_ID')
    guild_ids = None
    if guild:
        guild_ids = [int(guild)]

    # Create instance of Ecumene and attach functions.
    ecumene = Ecumene()

    @ecumene.client.slash_command(
        name='register', 
        description="Begin negotiations with Ecumene.", 
        guild_ids=guild_ids
    )
    async def register(ctx):
        await ecumene.events.register(ctx)

    @ecumene.client.slash_command(
        name='choose', 
        description="Wise one, make the choice for me.", 
        guild_ids=guild_ids
    )
    async def choose(ctx, choices):
        await ecumene.events.choose(ctx, *choices.split(' '))

    @ecumene.client.slash_command(
        name='bungo', 
        description="Test interaction with the Bungo API.", 
        guild_ids=guild_ids
    )
    async def bungo(ctx, clan):
        await ecumene.events.bungo(ctx, clan)

    @ecumene.client.slash_command(
        name='admin', 
        description="This is a top-secret communication.", 
        guild_ids=guild_ids
    )
    @ecumene.checks.is_guild_owner()
    async def admin(ctx):
        await ecumene.events.admin(ctx)

    @admin.error
    async def admin_error(ctx, error):
        await ecumene.errors.admin(ctx, error)

    @ecumene.client.slash_command(
        name='flawless', 
        description="I'm better than you.",
        options=[
            discord.Option(str, name='activity', description="Activity that I'm better than you at.", choices=['Raid', 'Dungeon']),
            discord.Option(discord.Member, description='Identify yourself.', name='user'),
            discord.Option(str, name='meme', description='Memes are always better.', choices=['Yes', 'No'], required=False)
        ],
        guild_ids=guild_ids
    )
    @ecumene.checks.user_has_role_permission()
    async def flawless(ctx, activity: str, user: discord.Member, meme: str):
        await ecumene.events.flawless(ctx, user, activity.lower())

    @flawless.error
    async def flawless_error(ctx, error):
        await ecumene.errors.flawless(ctx, error)

    @ecumene.client.slash_command(
        name='colour',
        description='You made this? I made this! 😀',
        options=[
            discord.Option(str, name='limit', description="Do you limit interactions?", choices=['Yes', 'No']),
        ],
        guild_ids=guild_ids, 
    )
    async def colour(ctx, limit):
        await ecumene.events.colour(ctx, strtobool(limit.lower()))

    @ecumene.client.slash_command(
        name='ping',
        description='You have a red dot now.',
        guild_ids=guild_ids, 
    )
    async def ping(ctx):
        await ecumene.events.ping(ctx)

    ecumene.run()

import os
import yaml
import dotenv
import logging.config

from bot.client import Ecumene

if __name__ == '__main__':
    
    # Initialise logging.
    fpath = os.path.join('conf', 'log.yml')
    with open(fpath, 'r') as cfile:
        cfg = yaml.load(cfile, Loader=yaml.FullLoader)
    logging.config.dictConfig(cfg)

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

    ecumene.run()

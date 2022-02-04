import os
import discord

from distutils.util import strtobool

from bot.core.client import EcumeneBot

# Force commands onto specific server to push instantly during debug.
guild = os.getenv('DISCORD_GUILD_ID')
guild_ids = None
if guild:
    guild_ids = [int(guild)]

# Create instance of Ecumene and attach functions.
ecumene = EcumeneBot()

# TODO: Commands that will need to be implemented.
#        - /register (50% completed already)
#        - /admin (~20% completed reusing functionality) - gated behind a role
#        - /whoami - let's users check they are registered correctly
#        - /clan <various> - gated behind specific clan admin roles or admins (will require roles.json in database)

# Enables register functionality.
@ecumene.client.slash_command(
    name='register', 
    description="Begin negotiations with Ecumene.", 
    guild_ids=guild_ids
)
async def register(ctx):
    await ecumene.events.register(ctx)

# Demonstration admin-restricted test function.
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

# Demonstration arguments and role-based access commmand.
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

# Demonstration interaction test command.
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

# Attach simple pign function.
@ecumene.client.slash_command(
    name='ping',
    description='You have a red dot now.',
    guild_ids=guild_ids, 
)
async def ping(ctx):
    await ecumene.events.ping(ctx)

def start():
    """Callable to run application."""
    ecumene.run()

if __name__ == '__main__':
    start()
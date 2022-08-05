import os
import discord
import logging

from bot.core.cogs.admin import Admin
from bot.core.cogs.audit import Audit
from bot.core.cogs.clan import Clan
from bot.core.cogs.guild import Guild
from bot.core.cogs.identity import Identity
from bot.core.cogs.example import Example

from bot.core.shared import DATABASE
from db.query.headers import get_guild_system_role, delete_system_role, publish_system_role
from db.query.members import get_members_matching, get_member_by_id
from util.local import get_guild_ids, get_system_role
from util.data import chunks

class EcumeneBot():
    """
    Bot client that should be used for primary Discord functionality.
    Will hold focus until terminated.
    """

    def __init__(self):
        self.log = logging.getLogger(f'{self.__module__}.{self.__class__.__name__}')
        self.client = discord.Bot(
            allowed_mentions=discord.AllowedMentions.all(), # Can mention all the things!
            intents=discord.Intents(guilds=True, members=True, emojis=True, reactions=True, scheduled_events=True),
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

        # Listen for new guilds being added.
        self.client.add_listener(
            self.new_guild, 
            'on_guild_join'
        )

        # On removal from a guild, clean up after ourselves.
        self.client.add_listener(
            self.leave_guild, 
            'on_guild_remove'
        )

        # Action when a new member joins one of our guilds.
        self.client.add_listener(
            self.sync_member, 
            'on_member_join'
        )

    async def ready(self):
        """Trigger on bot ready."""
        self.log.info(f'Logged in as {self.client.user} (ID={self.client.user.id})')

    async def new_guild(self, guild):
        """Trigger on joining a new guild."""
        self.log.info(f'Discovered a new guild "{guild.name}" (ID={guild.id})')
        
        # Check if the guild role already exists.
        results = get_guild_system_role(DATABASE, str(guild.id))
        if not results:
            self.log.info('Creating system role...')
            role = await guild.create_role(name=get_system_role(), color=discord.Colour.dark_theme())
            publish_system_role(DATABASE, str(guild.id), str(role.id))
        if results:
            # Someone removed me without deleting my system role!
            self.log.info('Outdated system role. Recreating...')
            delete_system_role(DATABASE, str(guild.id))
            role = await guild.create_role(name=get_system_role())
            publish_system_role(DATABASE, str(guild.id), str(role.id))

        # Now we would need to grant the role to all users in the guild registered with Ecumene.
        # This monstrosity could take forever on large servers.
        member_ids = list()
        for guild_member in guild.members:
            member_ids.append(str(guild_member.id))
        self.log.info(f"Found {len(member_ids)} members in guild")

        # Chunk members and process, adding role to each of them.
        member_chunks = list(chunks(member_ids, 1000))
        for chunk in member_chunks:
            matched = get_members_matching(DATABASE, 'discord_id', chunk)
            if not matched:
                continue
            for user_id in matched.get('discord_id'):
                member = guild.get_member(int(user_id))
                await member.add_roles(role)
        self.log.info('Proliferated member roles!')

    async def leave_guild(self, guild):
        """Trigger on losing access to a guild."""
        self.log.info(f'Halting transmissiong to guild "{guild.name}" (ID={guild.id})')

        # No way to remove the role from the guild itself because this action happens after being kicked.
        # At that point you no longer have server access.
        # We also can't delete the old role on rejoin because it will be above us in the permissions list.
        self.log.info('Removing system role...')
        delete_system_role(DATABASE, str(guild.id))

    async def sync_member(self, member):
        """Trigger on a new member joining any guild the bot is in."""

        # Check if the member exists in my database.
        matched = get_member_by_id(DATABASE, 'discord_id', str(member.id))
        if not matched:
            return

        # Thankfully we can limit the scope to just this guild.
        guild = member.guild

        # Get the role for the guild.
        results = get_guild_system_role(DATABASE, str(guild.id))
        if not results:
            return
        role = guild.get_role(int(results.get('role_id')[0]))

        # Give the member the role.
        await member.add_roles(role)

    def run(self):
        self.client.run(self.token)
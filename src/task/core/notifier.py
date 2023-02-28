import logging

from api.client import DiscordInterface, DiscordInterfaceError
from bnet.client import BungieInterface, BungieInterfaceError
from db.client import DatabaseService
from db.query.channels import get_guild_channels_by_purpose
from db.query.clans import get_clans_from_admins
from web.core.shared import WEB_RESOURCES

class EcumeneNotifier():

    def __init__(self, db: DatabaseService, api: DiscordInterface):
        self.log = logging.getLogger(f'{self.__module__}.{self.__class__.__name__}')
        self.db = db
        self.api = api

    def refresh_tokens_failed(self, failed):
        """Notify on tokens failing to refresh in scheduled job."""
        # Notification handling block.
        # Check if any admin updates failed.
        if not failed:
            return
        self.log.info('Notifying "refresh_tokens" failure...')
                    
        # Get respective clans for those admins, if they exist.
        details = get_clans_from_admins(self.db, failed)
        if not details:
            return
                    
        # Unpack guild and clan information.
        # Creates a dictionary keyed by guild containing a list of clan tuples.
        to_notify = dict()
        guild_ids = set(details.get('guild_id'))
        clan_data = zip(details.get('guild_id'), details.get('clan_id'), details.get('clan_name'), details.get('admin_id'))
        for guild_id in guild_ids:
            to_notify[guild_id] = list()
        for guild_id, clan_id, clan_name, admin_id in clan_data:
            clan_tuple = (clan_id, f"{clan_name}#{clan_id} ({admin_id})")
            to_notify[guild_id].append(clan_tuple)

        # Ugly sorting stuff.
        for guild_id in guild_ids:
            to_notify[guild_id] = sorted(to_notify[guild_id])

        # Loop all guilds to post relevant notifications.
        for guild_id, clan_tuples in to_notify.items():
            channel_configuration = get_guild_channels_by_purpose(self.db, guild_id, 'automation')
            channel_ids = channel_configuration.get('channel_id')
            if not channel_ids:
                # No channels to notify.
                continue
                    
            # Message generation.
            list_separator = "\n"
            description = 'High-priority transmission!'
            description += '\n\nFailed to update administrator credentials for the following clans managed in this server.'
            description += '\n\nAuthorisation via `/admin register` may be required.'
            clan_payloads = [c[1] for c in clan_tuples]
            field_info = f"{list_separator.join(clan_payloads)}"
            content = {
                'embeds': [
                    {
                        'title': 'Ecumene Automation — Notify',
                        'description': description,
                        'fields': [
                            {
                                'name': 'Payload',
                                'value': field_info,
                                'inline': False
                            }
                        ],
                        'footer': {
                            'text': 'ecumene.cc',
                            'icon_url': WEB_RESOURCES.logo
                        },
                        'thumbnail': {
                            'url': WEB_RESOURCES.logo
                        }
                    }
                ]
            }

            # If notifications are enabled, we want to post into respective channels.
            for channel_id in channel_ids:
                try:
                    self.api.create_message(channel_id, content)
                    self.log.info(f'Notification sent to "channel={channel_id}" successfully')
                except DiscordInterfaceError:
                    self.log.warn(f'Notification to "channel={channel_id}" unsuccessful')
                    continue
        
        # Succeeded notification.
        return
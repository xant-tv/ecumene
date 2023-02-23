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
        guilds = list(set(details.get('guild_id')))
        clans = zip(details.get('guild_id'), details.get('clan_id'), details.get('clan_name'), details.get('admin_id'))
        failed_in_guild = dict()
        for guild_id in guilds:
            failed_clans = list()
            for f_guild_id, f_clan_id, f_clan_name, f_admin_id in clans:
                f_data = f"{f_clan_name}#{f_clan_id} ({f_admin_id})"
                if guild_id == f_guild_id:
                    failed_clans.append(f_data)
            failed_in_guild[guild_id] = failed_clans

            # Loop all guilds to post relevant notifications.
            for g_id, clan_data in failed_in_guild.items():
                channel_configuration = get_guild_channels_by_purpose(self.db, g_id, 'automation')
                channel_ids = channel_configuration.get('channel_id')
                if not channel_ids:
                    # No channels to notify.
                    continue
                        
                # Message generation.
                list_separator = "\n"
                description = 'High-priority transmission!'
                description += '\n\nFailed to update administrator credentials for the following clans managed in this server.'
                description += '\n\nAuthorisation via `/admin register` may be required.'
                field_info = f"{list_separator.join(clan_data)}"
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
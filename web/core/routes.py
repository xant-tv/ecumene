import logging

from bnet.client import BungieInterface
from api.client import DiscordInterface, DiscordInterfaceError
from db.client import DatabaseService
from db.query import get_transaction, update_transaction, insert_or_update_member
from util.time import get_current_time

class EcumeneRouteHandler():

    def __init__(self):
        self.log = logging.getLogger(f'{self.__module__}.{self.__class__.__name__}')
        self.bnet = BungieInterface()
        self.api = DiscordInterface()
        self.db = DatabaseService(enforce_schema=True)

    def capture_login(self, request):
        """Complete account linkage between Destiny 2 and Discord."""
        # Capture code and state from login endpoint.
        capture = {
            'code': request.args.get('code')
        }

        # Update transaction to complete database record.
        update_transaction(self.db, capture, request.args.get('state'))
        result = get_transaction(self.db, request.args.get('state'))

        # Put this in a try-except block so we can notify the user.
        try:

            # Obtain both the Discord and Destiny 2 identifiers.
            token_data = self.bnet.get_token(request.args.get('code'))
            profile_data = self.bnet.get_linked_profiles(self.bnet.enum.mtype.bungie, token_data.get('membership_id'))
            bungie_name = f"{profile_data.get('bungieGlobalDisplayName')}#{profile_data.get('bungieGlobalDisplayNameCode')}"
            
            # Package all this information and capture in database.
            # Handles the case where the user is re-registering with either:
            #         - A new Discord ID
            #         - A new Destiny ID
            data = {
                'discord_id': result.get('discord_id')[0],
                'destiny_id': str(profile_data.get('membershipId')),
                'destiny_mtype': profile_data.get('membershipType'),
                'bnet_id': str(token_data.get('membership_id')),
                'bnet_mtype': self.bnet.enum.mtype.bungie,
                'registered_on': get_current_time()
            }
            insert_or_update_member(self.db, data)
            self.log.info('Captured registration request!')

            # Delete the initial registration message via the API.
            self.api.delete_message(result.get('channel_id')[0], result.get('message_id')[0])

            # Create an entirely new message to indicate the user is registered.
            content = {
                'embeds': [
                    {
                        'title': 'Ecumene Registration — Success',
                        'description': f'Well met, **{bungie_name}**. Stay tuned for further transmissions.'
                    }
                ]
            }
            self.api.create_message(result.get('channel_id')[0], content)

        # The general exception case where something failed along the line.
        # This might be a database error, or an API issue.
        except Exception as exc:

            # In this case, we want to ensure the initial registration message is deleted.
            try:
                self.api.delete_message(result.get('channel_id')[0], result.get('message_id')[0])
            except DiscordInterfaceError:
                # Message was already deleted.
                pass

            # Now create a new message to indicate that the registration failed.
            content = {
                'embeds': [
                    {
                        'title': 'Ecumene Registration — Failed',
                        'description': 'Unfortunately, something went wrong. Please re-initiate communications.'
                    }
                ]
            }
            self.api.create_message(result.get('channel_id')[0], content)

            # Re-raise the initial error so we can capture it through proper route error-handlers.
            raise exc

        return
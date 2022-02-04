import logging

from bnet.client import BungieInterface
from db.client import DatabaseService
from util.time import get_current_time

class EcumeneRouteHandler():

    def __init__(self):
        self.log = logging.getLogger(f'{self.__module__}.{self.__class__.__name__}')
        self.bnet = BungieInterface()
        self.db = DatabaseService(enforce_schema=True)

    def capture_login(self, request):
        """Complete account linkage between Destiny 2 and Discord."""
        # Capture code and state from login endpoint.
        capture = {
            'code': request.args.get('code')
        }

        # Update transaction and then obtain both the Discord and Destiny 2 identifiers.
        self.db.update('transactions', capture, 'state', request.args.get('state'))
        result = self.db.select('transactions', 'state', request.args.get('state'))
        token_data = self.bnet.get_token(request.args.get('code'))
        # We can hardcode the membership identifier as 254 here to represent a BNet profile.
        profile_data = self.bnet.get_linked_profiles(self.bnet.enum.mtype.bungie, token_data.get('membership_id'))
        
        # Package all this information and capture in database.
        # TODO: Handle the case where the user is re-registering with either:
        #         - A new Discord ID
        #         - A new Destiny ID
        data = {
            'discord_id': result.get('discord_id')[0],
            'destiny_id': profile_data.get('membershipId'),
            'destiny_mtype': profile_data.get('membershipType'),
            'bnet_id': token_data.get('membership_id'),
            'bnet_mtype': self.bnet.enum.mtype.bungie
        }
        self.db.insert('members', data)
        self.log.info('Captured registration request!')

        # TODO: Route to a nice-looking "you've registered" view.
        # TODO: Send a follow-up DM to notify user of successful registration.
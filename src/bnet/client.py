import os
import json
import requests
import logging

from urllib.parse import urlencode
from types import SimpleNamespace

MTYPES = dict(xbox=1, playstation=2, steam=3, blizzard=4, stadia=5, bungie=254)
MLEVELS = dict(beginner=1, member=2, admin=3, actingfounder=4, founder=5) # Just like with Halo - Bungie never made a 4th.

class BungieEnumerations():
    
    def __init__(self):
        self.mtype = SimpleNamespace(**MTYPES)
        self.mlevels = SimpleNamespace(**MLEVELS)

class BungieInterfaceError(Exception):

    def __init__(self, status, description):
        self.status = status
        self.description = description

    def __str__(self):
        return f'BungieInterface received a {self.status}.'

class BungieInterface():

    def __init__(self):
        self.log = logging.getLogger(f'{self.__module__}.{self.__class__.__name__}')
        self.web = os.getenv('BNET_ENDPOINT')
        self.root = f'{self.web}/Platform'
        self.key = os.getenv('BNET_API_KEY')
        self.id = os.getenv('BNET_CLIENT_ID')
        self.secret = os.getenv('BNET_CLIENT_SECRET')
        self.enum = BungieEnumerations()

    def _agent_(self):
        agent_app = f"{os.getenv('APPLICATION_NAME')}/{os.getenv('APPLICATION_VERSION')}"
        agent_bnet = f"{os.getenv('BNET_APP_NAME')}/{os.getenv('BNET_APP_ID')}"
        agent_contact = f"{os.getenv('WEB_URL')};{os.getenv('CONTACT_EMAIL')}"
        agent = f"{agent_app} {agent_bnet} (+{agent_contact})"
        return agent

    def _get_headers_(self):
        """Attach required API key for Bungie.net interaction."""
        headers = {
            'User-Agent': self._agent_(), # Bungie nicely asks for us to do this.
            'X-API-Key': self.key
        }
        return headers

    def _get_headers_with_token_(self, token):
        """Attach token to Bungie.net interaction to assume user responsibility."""
        # Note that the token is passed into the function and not stored within the class.
        # This is because we regularly have to rotate tokens or assume user identities.
        headers = self._get_headers_()
        headers = {
            'User-Agent': self._agent_(), # Bungie nicely asks for us to do this.
            'Authorization': f"Bearer {token}",
            'X-API-Key': self.key
        }
        return headers

    def _get_url_(self, *segments, root=None):
        """Build the API path."""
        path = '/'.join(map(str, segments))
        if not root:
            root = self.root
        url = f'{root}/{path}'
        return url

    def _execute_(self, method, url, headers=None, params=None, json=None, data=None):
        """Provide a `requests` method to execute."""
        self.log.info(f'{method.__name__.upper()} -> {url}')
        response = method(url, headers=headers, params=params, json=json, data=data)
        if not response.ok:
            try:
                body = response.json()
            except requests.exceptions.RequestException as e:
                raise BungieInterfaceError('RequestException', str(e)) from e
            raise BungieInterfaceError(body.get('ErrorStatus'), body.get('error_description'))
        return response.json()

    def _strip_outer_(self, body):
        return body.get('Response')

    def get_authorisation_url(self, state):
        url = self._get_url_('en', 'OAuth', 'Authorize', root=self.web)
        params = {
            'client_id': self.id,
            'response_type': 'code',
            'state': state
        }
        url_with_qry = f'{url}?{urlencode(params)}'
        return url_with_qry

    def get_token(self, code):
        url = self._get_url_('App', 'OAuth', 'Token')
        headers = self._get_headers_()
        data = {
            'client_id': self.id,
            'client_secret': self.secret,
            'grant_type': 'authorization_code',
            'code': code
        }
        response = self._execute_(requests.post, url, headers=headers, data=data)
        return response

    def refresh_token(self, refresh):
        url = self._get_url_('App', 'OAuth', 'Token')
        headers = self._get_headers_()
        data = {
            'client_id': self.id,
            'client_secret': self.secret,
            'grant_type': 'refresh_token',
            'refresh_token': refresh
        }
        response = self._execute_(requests.post, url, headers=headers, data=data)
        return response

    def get_destiny_player(self, display_name, display_code, membership_type):
        url = self._get_url_('Destiny2', 'SearchDestinyPlayerByBungieName', membership_type)
        headers = self._get_headers_()
        data = {
            'displayName': display_name, 
            'displayNameCode': int(display_code)
        }
        response = self._execute_(requests.post, url, headers=headers, json=data)
        content = next(iter(self._strip_outer_(response)), dict()) # Return first element of list or an empty structure.
        return content

    def find_destiny_player(self, display_name, display_code):
        # Use to attempt to find a player based on their display name and code.
        # There is no guarantee this player will be unique.
        # We have to search all membership types.
        membership_types = [
            self.enum.mtype.steam, 
            self.enum.mtype.playstation, 
            self.enum.mtype.xbox, 
            self.enum.mtype.stadia
        ]
        all_results = list()
        final_results = list()
        for membership_type in membership_types:
            results = self.get_destiny_player(display_name, display_code, membership_type)
            if results:
                all_results.append(results)
                # Check for cross-save membership type override.
                cross_save = results.get('crossSaveOverride')
                if not cross_save:
                    # Keep trying to find the player's information.
                    continue
                elif cross_save == membership_type:
                    final_results.append(results)
                    return final_results
                else:
                    results = self.get_destiny_player(display_name, display_code, cross_save)
                    final_results.append(results)
                    return final_results
        return all_results

    def get_linked_profiles(self, membership_type, membership_id):
        url = self._get_url_('Destiny2', membership_type, 'Profile', membership_id, 'LinkedProfiles')
        headers = self._get_headers_()
        response = self._execute_(requests.get, url, headers=headers)
        content = self._strip_outer_(response)
        return content

    def get_group_by_id(self, group_id):
        url = self._get_url_('GroupV2', group_id)
        headers = self._get_headers_()
        response = self._execute_(requests.get, url, headers=headers)
        detail = self._strip_outer_(response).get('detail')
        return detail

    def get_members_in_group(self, group_id):
        url = self._get_url_('GroupV2', group_id, 'Members')
        headers = self._get_headers_()
        response = self._execute_(requests.get, url, headers=headers)
        results = self._strip_outer_(response).get('results')
        return results

    def get_groups_for_user(self, membership_type, membership_id):
        # Path parameters support filters(?) and group type respectively.
        # Just hardcode these for now.
        url = self._get_url_('GroupV2', 'User', membership_type, membership_id, 0, 1)
        headers = self._get_headers_()
        response = self._execute_(requests.get, url, headers=headers)
        results = self._strip_outer_(response).get('results')
        return results

    def get_pending_in_group(self, token, group_id):
        url = self._get_url_('GroupV2', group_id, 'Members', 'Pending')
        headers = self._get_headers_with_token_(token)
        response = self._execute_(requests.get, url, headers=headers)
        results = self._strip_outer_(response).get('results')
        return results

    def get_invited_individuals(self, token, group_id):
        url = self._get_url_('GroupV2', group_id, 'Members', 'InvitedIndividuals')
        headers = self._get_headers_with_token_(token)
        response = self._execute_(requests.get, url, headers=headers)
        results = self._strip_outer_(response).get('results')
        return results

    def invite_user_to_group(self, token, group_id, membership_type, membership_id):
        url = self._get_url_('GroupV2', group_id, 'Members', 'IndividualInvite', membership_type, membership_id)
        headers = self._get_headers_with_token_(token)
        # For some reason this expects a body, even if it's empty.
        response = self._execute_(requests.post, url, headers=headers, json=dict())
        content = self._strip_outer_(response)
        return content

    def cancel_invite_to_group(self, token, group_id, membership_type, membership_id):
        url = self._get_url_('GroupV2', group_id, 'Members', 'IndividualInviteCancel', membership_type, membership_id)
        headers = self._get_headers_with_token_(token)
        response = self._execute_(requests.post, url, headers=headers)
        content = self._strip_outer_(response)
        return content

    def kick_member_from_group(self, token, group_id, membership_type, membership_id):
        url = self._get_url_('GroupV2', group_id, 'Members', membership_type, membership_id, 'Kick')
        headers = self._get_headers_with_token_(token)
        response = self._execute_(requests.post, url, headers=headers)
        results = self._strip_outer_(response).get('results')
        return results

    def set_membership_level(self, token, group_id, membership_type, membership_id, membership_level):
        url = self._get_url_('GroupV2', group_id, 'Members', membership_type, membership_id, 'SetMembershipType', membership_level)
        headers = self._get_headers_with_token_(token)
        response = self._execute_(requests.post, url, headers=headers)
        content = self._strip_outer_(response)
        return content
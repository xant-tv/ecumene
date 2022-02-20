import os
import json
import requests
import logging

from urllib.parse import urlencode
from types import SimpleNamespace

MTYPES = dict(xbox=1, playstation=2, steam=3, blizzard=4, stadia=5, bungie=254)

class BungieEnumerations():
    
    def __init__(self):
        self.mtype = SimpleNamespace(**MTYPES)

class BungieInterfaceError(Exception):

    def __init__(self, status):
        self.status = status

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
        body = response.json()
        if not response.ok:
            raise BungieInterfaceError(body.get('ErrorStatus', body.get('error_description')))
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

    def get_linked_profiles(self, membership_type, membership_id):
        url = self._get_url_('Destiny2', membership_type, 'Profile', membership_id, 'LinkedProfiles')
        headers = self._get_headers_()
        response = self._execute_(requests.get, url, headers=headers)
        profiles = self._strip_outer_(response).get('profiles')
        # Only return first profile (should only be one)
        return profiles[0]

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

    def kick_member_from_group(self, token, group_id, membership_type, membership_id):
        url = self._get_url_('GroupV2', group_id, 'Members', membership_type, membership_id, 'Kick')
        headers = self._get_headers_with_token_(token)
        response = self._execute_(requests.post, url, headers=headers)
        results = self._strip_outer_(response).get('results')
        return results
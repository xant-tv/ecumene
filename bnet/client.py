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

    def _get_headers_(self):
        """Attach required API key for Bungie.net interaction."""
        headers = {
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
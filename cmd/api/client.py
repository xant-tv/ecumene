import os
import json
import requests
import logging

class BungieInterfaceError(Exception):

    def __init__(self, status):
        self.status = status

    def __str__(self):
        return f'BungieInterface received a {self.status}.'

class BungieInterface():

    def __init__(self):
        self.log = logging.getLogger(f'{self.__module__}.{self.__class__.__name__}')
        self.root = os.getenv('BNET_ENDPOINT')
        self.key = os.getenv('BNET_API_KEY')

    def _get_headers_(self):
        """Attach required API key for Bungie.net interaction."""
        headers = {
            'X-API-Key': self.key
        }
        return headers

    def _get_url_(self, *segments):
        """Build the API path."""
        path = '/'.join(map(str, segments))
        url = f'{self.root}/{path}'
        return url

    def _execute_(self, method, url, headers=None, params=None, data=None):
        """Provide a `requests` method to execute."""
        self.log.info(f'{method.__name__.upper()} -> {url}')
        response = method(url, headers=headers, params=params, json=data)
        body = response.json()
        if not response.ok:
            raise BungieInterfaceError(body.get('ErrorStatus'))
        return response.json()

    def _strip_outer_(self, body):
        return body.get('Response')

    def find_clan_by_name(self, clan_name):
        self.log.info(f'Searching for clans matching "{clan_name}"')
        url = self._get_url_('GroupV2', 'Search')
        headers = self._get_headers_()
        data = {
            'name': clan_name,
            'groupType': 1
        }
        body = self._execute_(requests.post, url, headers=headers, data=data)
        clans = self._strip_outer_(body).get('results')
        # For now, return first result only.
        return clans[0]

    def is_flawless(self, membership_id, membership_type, activity):
        with open('conf/requirements.json') as fpath:
            reqs = json.load(fpath).get('requirements').get(activity)
            req_ids = [req['id'] for req in reqs]
        url = self._get_url_('Destiny2', membership_type, 'Profile', membership_id)
        headers = self._get_headers_()
        data = {
            'components': 900
        }
        body = self._execute_(requests.get, url, headers=headers, params=data)
        recs = self._strip_outer_(body).get('profileRecords').get('data').get('records')
        completed = list()
        for req_id in req_ids:
            if recs[str(req_id)]['objectives'][0]['complete']:
                completed.append(req_id)
        if completed == req_ids:
            return True
        return False

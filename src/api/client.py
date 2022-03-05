import os
import logging
import requests

class DiscordInterfaceError(Exception):

    def __init__(self, message):
        self.message = message

    def __str__(self):
        return f'DiscordInterface received an error with message "{self.message}".'

class DiscordInterface():
    """
    Non-interactive client intended for on-demand connection.
    Allows for Discord interaction via Web API directly.
    """

    def __init__(self):
        self.log = logging.getLogger(f'{self.__module__}.{self.__class__.__name__}')
        self.web = os.getenv('DISCORD_WEB_ROOT')
        self.root = f'{self.web}/api'
        self.token = os.getenv('DISCORD_TOKEN')

    def _get_headers_(self):
        """Attach required API key for Bungie.net interaction."""
        headers = {
            'Authorization': f'Bot {self.token}'
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
                raise DiscordInterfaceError('RequestException', str(e)) from e
            raise DiscordInterfaceError(body.get('message'))
        body = None
        if response.text:
            # This is necessary just because the /delete endpoint returns no content.
            body = response.json()
        return body

    def delete_message(self, channel_id, message_id):
        url = self._get_url_('channels', channel_id, 'messages', message_id)
        headers = self._get_headers_()
        response = self._execute_(requests.delete, url, headers=headers)
        return response

    def create_message(self, channel_id, data):
        url = self._get_url_('channels', channel_id, 'messages')
        headers = self._get_headers_()
        response = self._execute_(requests.post, url, headers=headers, json=data)
        return response

    def get_member(self, guild_id, user_id):
        url = self._get_url_('guilds', guild_id, 'members', user_id)
        headers = self._get_headers_()
        response = self._execute_(requests.get, url, headers=headers)
        return response

    def add_role_to_member(self, guild_id, user_id, role_id):
        url = self._get_url_('guilds', guild_id, 'members', user_id, 'roles', role_id)
        headers = self._get_headers_()
        response = self._execute_(requests.put, url, headers=headers)
        return response

    def delete_role_from_member(self, guild_id, user_id, role_id):
        url = self._get_url_('guilds', guild_id, 'members', user_id, 'roles', role_id)
        headers = self._get_headers_()
        response = self._execute_(requests.delete, url, headers=headers)
        return response
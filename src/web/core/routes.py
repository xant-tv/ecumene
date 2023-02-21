import logging

from api.client import DiscordInterface, DiscordInterfaceError
from bnet.client import BungieInterface
from bot.core.shared import DATABASE, EMOJIS, PLATFORMS
from web.core.shared import WEB_RESOURCES
from db.query.headers import get_guilds
from db.query.transactions import get_transaction, update_transaction
from db.query.members import insert_or_update_member
from db.query.admins import insert_or_update_admin
from db.query.clans import insert_or_update_clan
from util.time import get_current_time, bnet_to_time, epoch_to_time
from util.enum import TransactionType

class EcumeneRouteHandler():

    def __init__(self):
        self.log = logging.getLogger(f'{self.__module__}.{self.__class__.__name__}')
        self.bnet = BungieInterface()
        self.api = DiscordInterface()
        self.db = DATABASE

    def capture_login(self, request):
        """Complete account linkage between Destiny 2 and Discord."""

        # If the request has no arguments, then just exit.
        if not (request.args.get('code') or request.args.get('state')):
            return None, None # Will result in a redirect to the index page.

        # Capture code and state from login endpoint.
        capture = {
            'code': request.args.get('code')
        }

        # Check if state has been processed before.
        result = get_transaction(self.db, request.args.get('state'))
        if not result:
            raise ValueError('Failed to find specified state.')
        if result.get('code')[0]:
            # Handle cases where state has been processed before.
            raise ValueError('Specified state has already been processed.')

        # Update transaction to complete database record.
        update_transaction(self.db, capture, request.args.get('state'))

        # Split functionality depending on purpose enumeration.
        purpose = result.get('purpose')[0]
        if not TransactionType.has_value(purpose):
            raise NotImplementedError(f'Transaction purpose "{purpose}" not implemented.')
        elif purpose == TransactionType.USER:
            return self.capture_login_user(request, result)
        elif purpose == TransactionType.ADMIN:
            return self.capture_login_admin(request, result)
        raise ValueError('Transaction did not specify purpose.')

    def capture_login_user(self, request, result):
        """Login capture variant intended for user registration."""
        # Put this in a try-except block so we can notify the user.
        try:

            # Get linked profiles from token data.
            token_data = self.bnet.get_token(request.args.get('code'))
            linked_profiles = self.bnet.get_linked_profiles(self.bnet.enum.mtype.bungie, token_data.get('membership_id'))
            
            # Obtain both the Discord and Destiny 2 identifiers.
            # Rely on the fact that cross-save override will force out all other profiles into the "WithErrors" section.
            # This means the first profile will always be the cross-save profile if cross-save is enabled.
            bnet_data = linked_profiles.get('bnetMembership')
            profile_data = linked_profiles.get('profiles')
            if not profile_data:
                backup_name = bnet_data.get('bungieGlobalDisplayName')
                backup_code = bnet_data.get('bungieGlobalDisplayNameCode')
                backup_data = self.bnet.find_destiny_player(backup_name, backup_code)
                profile_data = backup_data
            primary_profile = profile_data[0]
            display_name = primary_profile.get('displayName')
            bungie_name = f"{primary_profile.get('bungieGlobalDisplayName')}#{str(primary_profile.get('bungieGlobalDisplayNameCode')).zfill(4)}"
            
            # If multiple platforms, choose based on most recently played.
            has_multiple = False
            if len(profile_data) > 1:
                has_multiple = True
                profile_map = dict()
                last_played = epoch_to_time(0)
                for profile in profile_data:
                    played = bnet_to_time(profile.get('dateLastPlayed'))
                    if played > last_played:
                        last_played = played
                    profile_map[played] = profile
                primary_profile = profile_map[last_played]

            # Inspect cross-save status as well.
            membership_id = primary_profile.get('membershipId')
            platform_id = primary_profile.get('membershipType')
            cross_save = False
            if primary_profile.get('crossSaveOverride'):
                cross_save = True
            
            # Package all this information and capture in database.
            # Handles the case where the user is re-registering with either:
            #         - A new Discord ID
            #         - A new Destiny ID
            user_id = result.get('request_id')[0]
            data = {
                'discord_id': user_id,
                'destiny_id': str(membership_id),
                'destiny_mtype': platform_id,
                'bnet_id': str(token_data.get('membership_id')),
                'bnet_mtype': self.bnet.enum.mtype.bungie,
                'registered_on': get_current_time()
            }
            _, delete_list = insert_or_update_member(self.db, data)
            self.log.info('Captured registration request!')

            # Update user roles in all guilds for this new member.
            headers = get_guilds(self.db)
            if headers:

                # Unfortunately, we have to do this guild-by-guild.
                # Could take a while at scale, thankfully there are multiple workers!
                for guild_id, role_id in zip(headers.get('guild_id'), headers.get('role_id')):

                    # Remove role for any members that we deleted.       
                    if delete_list:
                        for delete_id in delete_list:
                            if delete_id == user_id: 
                                continue
                            try:
                                self.api.get_member(guild_id, user_id)
                                self.api.delete_role_from_member(guild_id, delete_id, role_id)
                            except DiscordInterfaceError as e:
                                # Either member didn't exist in guild or unable to set roles.
                                pass

                    # Now try to grant the role for new registration.
                    try:
                        self.api.get_member(guild_id, user_id)
                        self.api.add_role_to_member(guild_id, user_id, role_id)
                    except DiscordInterfaceError as e:
                        # Either member didn't exist in guild or unable to set roles.
                        pass
                
                self.log.info('Proliferated user roles!')

            # Delete the initial registration message via the API.
            try:
                self.api.delete_message(result.get('channel_id')[0], result.get('message_id')[0])
            except DiscordInterfaceError as e:
                # Message was already deleted.
                pass

            # Generate content message for response.
            field_info = 'I have detected one profile linked to this account.'
            if cross_save:
                field_info = 'I detect you have cross-save enabled. Your cross-save platform has been chosen as your primary profile.'
            if has_multiple:
                field_info = 'It appears you have multiple active platforms. One has been chosen as your primary profile based on recent activity.'
            field_info += '\n\nYour primary profile is set to:'
            field_info += f'\n**{display_name}** ({membership_id}:{platform_id}) {getattr(EMOJIS, PLATFORMS.get(platform_id))}'
            if cross_save:
                field_info += f' {EMOJIS.cross_save}'
            field_info += '\n\nYou may change your active profile with `/profile` at any time.'

            # Create an entirely new message to indicate the user is registered.
            content = {
                'embeds': [
                    {
                        'title': 'Ecumene Registration — Success',
                        'description': f'Well met, **{bungie_name}**. Stay tuned for further transmissions.',
                        'fields': [
                            {
                                'name': 'Important Information',
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
                        'description': 'Unfortunately, something went wrong. Please re-initiate communications.',
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
            self.api.create_message(result.get('channel_id')[0], content)

            # Re-raise the initial error so we can capture it through proper route error-handlers.
            raise exc

        # We want to return the display name of the user.
        return result.get('purpose')[0], result.get('request_display')[0]

    def capture_login_admin(self, request, result):
        """Login capture variant intended for clan administrator registration."""
        # Put this in a try-except block so we can notify the user on failure.
        try:

            # Obtain the Destiny 2 token and record this administrator.
            # TODO: Handle the case where the administrator already exists.
            request_time = get_current_time()
            token_data = self.bnet.get_token(request.args.get('code'))
            admin = {
                'admin_id': str(token_data.get('membership_id')),
                'admin_mtype': self.bnet.enum.mtype.bungie,
                'access_token': str(token_data.get('access_token')),
                'access_expires_at': request_time + (1000 * token_data.get('expires_in')),
                'refresh_token': str(token_data.get('refresh_token')),
                'refresh_expires_at': request_time + (1000 * token_data.get('refresh_expires_in'))
            }
            insert_or_update_admin(self.db, admin)

            # Now we need to record or update information about the clan.
            detail = self.bnet.get_group_by_id(result.get('request_id')[0])
            clan_name = f"{detail.get('name')}#{result.get('request_id')[0]}"
            clan = {
                'guild_id': result.get('guild_id')[0],
                'clan_id': result.get('request_id')[0],
                'clan_name': detail.get('name'),
                'role_id': result.get('option_id')[0],
                'admin_id': str(token_data.get('membership_id'))
            }
            insert_or_update_clan(self.db, clan)

            # Complete registration request.
            self.log.info('Captured registration request!')

            # Delete the initial registration message via the API.
            self.api.delete_message(result.get('channel_id')[0], result.get('message_id')[0])

            # Create an entirely new message to indicate the user is registered.
            content = {
                'embeds': [
                    {
                        'title': 'Ecumene Registration — Success',
                        'description': f'Elevated privileges for **{clan_name}** have been recorded.',
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
                        'description': 'Unfortunately, something went wrong. Please re-initiate communications.',
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
            self.api.create_message(result.get('channel_id')[0], content)

            # Re-raise the initial error so we can capture it through proper route error-handlers.
            raise exc

        return result.get('purpose')[0], result.get('request_display')[0]
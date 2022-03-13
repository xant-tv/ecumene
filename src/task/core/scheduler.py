import sched
import time
import logging

from bnet.client import BungieInterface, BungieInterfaceError
from db.client import DatabaseService
from db.query.admins import insert_or_update_admin, get_tokens_to_refresh, get_orphans, delete_orphans, get_dead
from util.time import get_current_time

TOP_PRIORITY = 1
HIGH_PRIORITY = 2
LOW_PRIORITY = 3
NO_PRIORITY = 4

TOKEN_REFRESH_SCHEDULE = 15*60
TOKEN_REFRESH_URGENT_SCHEDULE = 5*60
CLEAN_ADMIN_SCHEDULE = 24*60*60

TOKEN_PROCESSING_BUFFER = 5*60

class EcumeneScheduler():

    def __init__(self):
        self.log = logging.getLogger(f'{self.__module__}.{self.__class__.__name__}')
        self.bnet = BungieInterface()
        self.db = DatabaseService(enforce_schema=True)
        self.schedule = sched.scheduler(time.time, time.sleep)
        self.initialise_schedule()

    def run(self):
        """Actually begin schedule execution."""
        self.schedule.run()

    def initialise_schedule(self):
        """Initialise schedule tasking."""
        # Run tasks on-demand to begin scheduling.
        self.clean_admin_cache()
        self.refresh_tokens()

    # This task must be run every fifteen minutes!
    def refresh_tokens(self, delay=TOKEN_REFRESH_SCHEDULE):
        """Refresh all stored database tokens."""
        self.log.info('Running "refresh_tokens" scheduled task...')

        # Put this whole thing into a try-except block to avoid scheduler death.
        try:

            # Get tokens either already expired or close to expiry.
            # These tokens must be able to be refreshed.
            records = get_tokens_to_refresh(self.db, delay, TOKEN_PROCESSING_BUFFER)
            if records:
                to_update = len(records.get('admin_id'))
                self.log.info(f"Refreshing {to_update} administrator credential(s)")
                
                # Naively loop these for now - shouldn't take long in practice.
                updated = 0
                for admin_id, refresh_token in zip(records.get('admin_id'), records.get('refresh_token')):
                    request_time = get_current_time()
                    try:
                        token_data = self.bnet.refresh_token(refresh_token)
                    except BungieInterfaceError as e:
                        self.log.error("There was an issue updating credentials!")
                        continue
                    admin = {
                        'admin_id': admin_id,
                        'access_token': str(token_data.get('access_token')),
                        'access_expires_at': request_time + (1000 * token_data.get('expires_in')),
                        'refresh_token': str(token_data.get('refresh_token')),
                        'refresh_expires_at': request_time + (1000 * token_data.get('refresh_expires_in'))
                    }
                    insert_or_update_admin(self.db, admin)
                    updated += 1

                # Check if any credentials failed to update.
                # Update delay if they have.
                failed_updated = to_update - updated
                if failed_updated:
                    self.log.warn(f"Ran into issues updating {failed_updated} credentials")
                    delay = TOKEN_REFRESH_URGENT_SCHEDULE
                if updated:
                    self.log.info("Administrator credentials updated")

        # If something goes wrong, log and reschedule again.
        except Exception as e:
            self.log.error(e)
            delay = TOKEN_REFRESH_URGENT_SCHEDULE

        # Ensure this task is rescheduled to run.
        # Note that we could modify delay on the next iteration.
        self.schedule.enter(
            delay, 
            TOP_PRIORITY, 
            self.refresh_tokens
        )

    def clean_admin_cache(self, delay=CLEAN_ADMIN_SCHEDULE):
        """Remove cached administrator tokens that are no longer referenced."""
        self.log.info('Running "clean_admin_cache" scheduled task...')

        # Put this whole thing into a try-except block to avoid scheduler death.
        try:

            # Get orphans first just to log if any are present.
            orphans = get_orphans(self.db)
            if orphans:
                self.log.info(f"Found {len(orphans.get('admin_id'))} orphaned credential(s)")
                delete_orphans(self.db)

            # Dead credentials are still referenced so we only check those.
            dead = get_dead(self.db, TOKEN_PROCESSING_BUFFER)
            if dead:
                self.log.info(f"Found {len(dead.get('admin_id'))} dead credential(s)")
                
                # TODO: There will need to be a message to Discord to notify of expiry.
                # This will have to wait until we have notification functions in place.
                # The idea is it would look up the clan this user administrates and then notify the guild(s).

        # If something goes wrong, log and reschedule again.
        except Exception as e:
            self.log.error(e)
        
        # Ensure this task is rescheduled to run in a day.
        # Set this as low in priority to avoid getting in the way of keep-alive tasking.
        self.schedule.enter(
            delay, 
            LOW_PRIORITY, 
            self.clean_admin_cache
        )

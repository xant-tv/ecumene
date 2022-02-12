import sched
import time
import logging

from bnet.client import BungieInterface
from db.client import DatabaseService

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
        self.refresh_tokens()

    def refresh_tokens(self):
        """Refresh all stored database tokens."""
        self.log.info('Running "refresh_tokens" scheduled task...')

        # TODO: Actually do things...
        # ...

        # Ensure this task is rescheduled to run in a day.
        self.schedule.enter(60, 1, self.refresh_tokens)
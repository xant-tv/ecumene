import os
import logging
import flask

from web.core.routes import EcumeneRouteHandler

class EcumeneWeb():

    # TODO: Fix logging format for native Flask behaviour.

    def __init__(self):
        self.log = logging.getLogger(f'{self.__module__}.{self.__class__.__name__}')
        self.client = flask.Flask(__name__)
        self.port = os.getenv('WEB_PORT', 8080)
        self.routes = EcumeneRouteHandler()

    def run(self):
        self.client.run(port=self.port)
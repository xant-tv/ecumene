import os
import logging
import click
import flask

from web.core.routes import EcumeneRouteHandler

# Fix start-up logging format for native Flask behaviour.
# https://stackoverflow.com/a/57086684
def secho(text, file=None, nl=None, err=None, color=None, **styles):
    pass

def echo(text, file=None, nl=None, err=None, color=None, **styles):
    pass

click.echo = echo
click.secho = secho

class EcumeneWeb():

    def __init__(self):
        self.log = logging.getLogger(f'{self.__module__}.{self.__class__.__name__}')
        self.client = flask.Flask(
            __name__, 
            template_folder='../templates', # This is relative to the path of _this_ file.
            static_url_path='/static', # Serve images from "/static" paths.
            static_folder='../static' # Again, relative to this file.
        )
        self.port = os.getenv('WEB_PORT', 8080)
        self.routes = EcumeneRouteHandler()

    def log_request(self, request, response):
        self.log.info(f'{request.remote_addr} | {request.scheme.upper()} | {request.method} | {request.full_path} | {response.status}')

    def run(self):
        self.client.run(port=self.port)
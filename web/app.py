import os

from flask import request

from web.core.client import EcumeneWeb

# Create instance of Ecumene and attach functions.
ecumene = EcumeneWeb()

# TODO: Implement background tasks.
#       - Admin token freshness.
#       - Channel-based notifications (requires moving channels.json into database). Maybe front-end command?

# TODO: Workflow logic.
#       - Member update rather than insert.
#       - Admin storage equivalent.
#       - Ability to retry on BNet 401 Unauthorized errors with a (hopefully new) token.

@ecumene.client.route("/login", methods=['GET'])
def login():
    ecumene.routes.capture_login(request)
    return "Thanks for the password, suckas!"

def start():
    """Callable to run application."""
    ecumene.run()

if __name__ == '__main__':
    start()
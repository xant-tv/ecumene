from flask import request, render_template, send_from_directory
from werkzeug.exceptions import HTTPException

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

@ecumene.client.errorhandler(500)
def server_error(error):
    return render_template('view/500.html'), 500

@ecumene.client.errorhandler(404)
def page_not_found(error):
    return render_template('view/404.html'), 404

@ecumene.client.route("/success", methods=['GET'])
def success():
    return render_template('view/reg_success.html')

@ecumene.client.route("/failure", methods=['GET'])
def failure():
    return render_template('view/reg_failure.html')

@ecumene.client.route("/login", methods=['GET'])
def login():
    ecumene.routes.capture_login(request)
    return render_template('view/reg_success.html')

@ecumene.client.route("/", methods=['GET'])
def index():
    return render_template('view/index.html')

@ecumene.client.after_request
def after_request(response):
    ecumene.log_request(request, response)
    return response

def start():
    """Callable to run application."""
    ecumene.run()

if __name__ == '__main__':
    start()
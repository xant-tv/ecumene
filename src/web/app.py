import logging

from flask import request, render_template, redirect, url_for

from web.core.client import EcumeneWeb
from util.enum import TransactionType

# Create instance of Ecumene and attach functions.
ecumene = EcumeneWeb()
client = ecumene.client

# TODO: Workflow logic.
#       - Member update rather than insert.
#       - Admin storage equivalent.
#       - Ability to retry on BNet 401 Unauthorized errors with a (hopefully new) token.

# Error handlers will redirect to the error page.
# This strips any garbage arguments from the URL.
@client.errorhandler(500)
def raw_server_error(error):
    return redirect(url_for('server_error'))

@client.errorhandler(404)
def raw_page_not_found(error):
    return redirect(url_for('page_not_found'))

# These are error handler routes to serve pages.
# Avoids the issue with a direct render.
@client.route("/500", methods=['GET'])
def server_error():
    return render_template('view/page-500.html'), 500

@client.route("/404", methods=['GET'])
def page_not_found():
    return render_template('view/page-404.html'), 404

# This route will serve the success page.
@client.route("/success", methods=['GET'])
def success():
    return render_template('view/reg-success.html', displayName=request.args.get('displayName'))

# This route will serve the admin success page.
@client.route("/admin", methods=['GET'])
def admin():
    return render_template('view/reg-admin.html', displayName=request.args.get('displayName'))

# On failure we want to serve a failure page but still status this as an internal error code.
@client.route("/failure", methods=['GET'])
def failure():
    return render_template('view/reg-failure.html'), 500

# This is the redirect route to send users to after Bungie authorisation.
@client.route("/login", methods=['GET'])
def login():
    try:
        purpose, display = ecumene.routes.capture_login(request)
        if not purpose:
            return redirect(url_for('index'))
        elif not TransactionType.has_value(purpose):
            raise NotImplementedError(f'Transaction purpose "{purpose}" not implemented.')
        elif purpose == TransactionType.USER:
            return redirect(url_for('success', displayName=display))
        elif purpose == TransactionType.ADMIN:
            return redirect(url_for('admin', displayName=display))
        else:
            raise ValueError('Transaction did not specify purpose.')
    except Exception as exc:
        ecumene.log.error(exc)
        return redirect(url_for('failure'))

@client.route("/", methods=['GET'])
def index():
    return render_template('view/index.html')

@client.after_request
def after_request(response):
    ecumene.log_request(request, response)
    return response

def start():
    """Callable to run application."""
    ecumene.start()

if __name__ == '__main__':
    start()
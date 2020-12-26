"""
Note: This file was adapted from the unoffiicial Python Fitbit client Git repo:
https://raw.githubusercontent.com/orcasgit/python-fitbit/master/gather_keys_oauth2.py
"""
import cherrypy
import os
import sys
import threading
import traceback
import webbrowser
import json
import inspect

from urllib.parse import urlparse
from fitbit.api import Fitbit
from oauthlib.oauth2.rfc6749.errors import MismatchingStateError, MissingTokenError

# This is to replace cherrypy.quickstart
class _StateEnum(object):

    class State(object):
        name = None

        def __repr__(self):
            return 'states.%s' % self.name

    def __setattr__(self, key, value):
        if isinstance(value, self.State):
            value.name = key
        object.__setattr__(self, key, value)

states = _StateEnum()
states.STOPPED = states.State()
states.STARTING = states.State()
states.STARTED = states.State()
states.STOPPING = states.State()
states.EXITING = states.State()

# filepathes for details-files
dp_thisdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
CLIENT_DETAILS_FILE = os.path.join(dp_thisdir, 'client_details.json')  # configuration for for the client
USER_DETAILS_FILE = os.path.join(dp_thisdir, 'user_details.json') # user details file


class OAuth2Server:
    def __init__(self, client_id, client_secret,
                 redirect_uri='http://127.0.0.1:8080/'):
        """ Initialize the FitbitOauth2Client """
        self.success_html = """
            <h1>You are now authorized to access the Fitbit API!</h1>
            <br/><h3>You can close this window</h3>"""
        self.failure_html = """
            <h1>ERROR: %s</h1><br/><h3>You can close this window</h3>%s"""

        self.fitbit = Fitbit(
            client_id,
            client_secret,
            redirect_uri=redirect_uri,
            timeout=10,
        )

        self.redirect_uri = redirect_uri

    def browser_authorize(self):
        """
        Open a browser to the authorization url and spool up a CherryPy
        server to accept the response
        """
        url, _ = self.fitbit.client.authorize_token_url()
        # Open the web browser in a new thread for command-line browser support
        threading.Timer(1, webbrowser.open, args=(url,)).start()
        print()
        print('URL for authenticating is:')
        print(url)
        print()

        # Same with redirect_uri hostname and port.
        urlparams = urlparse(self.redirect_uri)
        cherrypy.config.update({'server.socket_host': urlparams.hostname,
                                'server.socket_port': urlparams.port})

        # The following is to replace: cherrypy.quickstart(self)
        cherrypy.tree.mount(self)
        engine = cherrypy.engine
        
        engine.signals.subscribe()
        engine.start()  
        
        try:
            engine.wait(states.EXITING, interval=0.1, channel='main')
        except (KeyboardInterrupt, IOError):
            # The time.sleep call might raise
            # "IOError: [Errno 4] Interrupted function call" on KBInt.
            engine.log('Keyboard Interrupt: shutting down bus')
            engine.exit()
        except SystemExit:
            engine.log('SystemExit raised: shutting down bus')
            engine.exit()
            raise

    @cherrypy.expose
    def index(self, state, code=None, error=None):
        """
        Receive a Fitbit response containing a verification code. Use the code
        to fetch the access_token.
        """
        error = None
        if code:
            try:
                self.fitbit.client.fetch_access_token(code)
            except MissingTokenError:
                error = self._fmt_failure(
                    'Missing access token parameter.</br>Please check that '
                    'you are using the correct client_secret')
            except MismatchingStateError:
                error = self._fmt_failure('CSRF Warning! Mismatching state')
        else:
            error = self._fmt_failure('Unknown error while authenticating')
        # Use a thread to shutdown cherrypy so we can return HTML first
        self._shutdown_cherrypy()
        return error if error else self.success_html

    def _fmt_failure(self, message):
        tb = traceback.format_tb(sys.exc_info()[2])
        tb_html = '<pre>%s</pre>' % ('\n'.join(tb)) if tb else ''
        return self.failure_html % (message, tb_html)

    def _shutdown_cherrypy(self):
        """ Shutdown cherrypy in one second, if it's running """
        if cherrypy.engine.state == cherrypy.engine.states.STARTED:
            threading.Timer(1, cherrypy.engine.exit).start()


def main(ID:str, SECRET:str):
    """ to authorize user and generate user and client details

    Parameters
    ----------
    ID : str
        User ID string. 
    SECRET : str
        User secret string.

    Returns
    -------
    None.
    """

    client_id = ID
    client_secret = SECRET
    server = OAuth2Server(client_id, client_secret)
    server.browser_authorize()

    profile = server.fitbit.user_profile_get()
    print('You are authorized to access data for the user: {}'.format(
        profile['user']['fullName']))

    print('TOKEN\n=====\n')
    for key, value in server.fitbit.client.session.token.items():
        print('{} = {}'.format(key, value))

    print("Writing client details to file for usage on next collection.")
    client_details = {'client_id': client_id, 'client_secret': client_secret}  # Details of application
    with open(CLIENT_DETAILS_FILE, 'w') as f:
        json.dump(client_details, f)

    print("Writing user details to file for usage on next collection.")
    with open(USER_DETAILS_FILE, 'w') as f:
        json.dump(server.fitbit.client.session.token, f)

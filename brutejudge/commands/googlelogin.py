import webbrowser, http.server, threading, json, shlex
from .._http.ejudge import get, post
from ..http import login, login_type
from ..error import BruteError
from urllib.parse import urlencode, unquote

HTTP_RESPONSE = b'''\
<html>
<head>
<title>brutejudge Google OAuth success</title>
</head>
<body>
<p>brutejudge has successfully authenticated against Google OAuth servers. You may now close this window.</p>
</body>
</html>'''

class LoginCodeReceiver(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        code = unquote(self.path.split('?code=', 1)[1].split('&', 1)[0])
        self.server.login_code = code
        threading.Thread(target=self.server.shutdown).start()
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(HTTP_RESPONSE)))
        self.end_headers()
        self.wfile.write(HTTP_RESPONSE)

def get_login_code(scope, client_id):
    srv = http.server.HTTPServer(('127.0.0.1', 0), LoginCodeReceiver)
    redirect_uri = 'http://%s:%d'%srv.socket.getsockname()
    webbrowser.open('https://accounts.google.com/o/oauth2/auth?'+urlencode({'redirect_uri': redirect_uri, 'scope': scope, 'response_type': 'code', 'client_id': client_id}))
    srv.serve_forever()
    return srv.login_code, redirect_uri

def get_auth_token(login_code, redirect_uri, client_id, client_secret):
    code, headers, data = post('https://oauth2.googleapis.com/token', {'code': login_code, 'client_id': client_id, 'client_secret': client_secret, 'redirect_uri': redirect_uri, 'grant_type': 'authorization_code'}, {'Content-Type': 'application/x-www-form-urlencoded'})
    assert code == 200, data
    return json.loads(data)['access_token']

def do_login(scope, client_id, client_secret):
    login_code, redirect_uri = get_login_code(scope, client_id)
    return get_auth_token(login_code, redirect_uri, client_id, client_secret)

def do_googlelogin(self, cmdline):
    """
    usage: googlelogin [--client-id <client_id>] [--client-secret <client_secret>] <url>

    Login to the testing system using Google OAuth (the testing system must support such logins).
    """
    cmdline = shlex.split(cmdline)
    client_id = '158805258134-fk2gef9qi727b7rncel01p582md374a0.apps.googleusercontent.com'
    client_secret = 'scWWMjrZmnQxA6BPz_4dYgxa'
    if cmdline and cmdline[0] == '--client-id':
        client_id = cmdline[1]
        del cmdline[:2]
    if cmdline and cmdline[0] == '--client-secret':
        client_secret = cmdline[1]
        del cmdline[:2]
    if len(cmdline) != 1:
        return self.do_help('googlelogin')
    url = cmdline[0]
    x = [i for i in login_type(url) if i.startswith('goauth:')]
    if len(x) != 1:
        raise BruteError("Google OAuth is not supported by this testing system.")
    scope = x[0][7:]
    token = do_login(scope, client_id, client_secret)
    self.url, self.cookie = login(url, None, None, token=token)

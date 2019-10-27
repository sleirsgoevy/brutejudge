import brutejudge.cheats
from brutejudge.error import BruteError
from brutejudge._http.ejudge import Ejudge

def do_hijack(self, cmd):
    """
    usage: hijack <stolen_cookie>

    Set the SID and cookie to the stolen ones.
    """
    brutejudge.cheats.cheating(self)
    if cmd.strip() == '':
        return self.do_help('hijack')
    try:
        a, b = cmd.strip().split('-')
        int(a, 16)
        int(b, 16)
    except Exception:
        raise BruteError("Invalid cookie: "+cmd.strip())
    if not isinstance(self.url, Ejudge):
        raise BruteError("Testing system is not ejudge")
    self.url.urls = {k: v.replace(self.url['sid'], a) for k, v in self.url.items()}
    self.url.cookie = 'EJSID='+b

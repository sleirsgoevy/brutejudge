from brutejudge.error import BruteError

def do_hijack(self, cmd):
    """
    usage: hijack <stolen_cookie>

    Set the SID and cookie to the stolen ones.
    """
    if cmd.strip() == '':
        return self.do_help('hijack')
    try:
        a, b = cmd.strip().split('-')
        int(a, 16)
        int(b, 16)
    except Exception:
        raise BruteError("Invalid cookie: "+cmd.strip())
    self.url = {k: v.replace(self.url['sid'], a) for k, v in self.url.items()}
    self.cookie = 'EJSID='+b

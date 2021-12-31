from brutejudge.http import locales, set_locale

def do_locale(self, cmd):
    """
    usage: locale [which]

    If called without arguments, list available locales.
    If called with an argument, set the current locale to <which>.
    """
    cmd = cmd.strip()
    if cmd:
        set_locale(self.url, self.cookie, cmd)
    else:
        print('Available locales:', ', '.join(i[1] for i in locales(self.url, self.cookie)))

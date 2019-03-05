import brutejudge.cheats

def do_nocheats(self, cmd):
    """
    usage: nocheats

    Disable cheat functions for current session.
    """
    brutejudge.cheats.cheating(self)
    if not (cmd+' ').isspace():
        return self.do_help('nocheats')
    self.no_cheats = True

from .scoreboard import do_scoreboard

def do_standings(self, cmd):
    """
    usage: standings

    Show current standings.
    """
    return do_scoreboard(self, cmd, command_name='standings')

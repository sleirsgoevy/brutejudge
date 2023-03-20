from brutejudge.http import do_action
from brutejudge.error import BruteError

def do_control(self, cmd):
    """
    usage: do_control <action> [args]

    `action` can be one of:
        start-virtual
        Start virtual contest.

        stop-virtual
        Stop virtual contest.
    """
    cmd = cmd.strip()
    if cmd == 'start-virtual':
        if not do_action(self.url, self.cookie, 'start_virtual'):
            raise BruteError("Failed to start virtual contest")
    elif cmd == 'stop-virtual':
        if not do_action(self.url, self.cookie, 'stop_virtual'):
            raise BruteError("Failed to stop virtual contest")
    else:
        return self.do_help('control')

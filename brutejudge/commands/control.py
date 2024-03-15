from brutejudge.http import action_list, do_action
from brutejudge.error import BruteError

SIMPLE_ACTIONS = {
    'start-virtual': ('start_virtual', 'start virtual contest'),
    'stop-virtual': ('stop_virtual', 'stop virtual contest'),
    'restart-virtual': ('restart_virtual', 'restart virtual contest'),
    'register': ('register', 'register'),
    'rated-register': ('rated_register', 'register as a rated participant'),
    'unrated-register': ('unrated_register', 'register as an unrated participant'),
}

ACTION_TO_COMMAND = {j[0]: i for i, j in SIMPLE_ACTIONS.items()}

def do_control(self, cmd):
    """
    usage: do_control [action] [args]

    `action` can be one of:
        start-virtual
        Start a virtual contest.

        stop-virtual
        Stop the virtual contest.

        restart-virtual
        Restart the virtual contest.

        register
        Register to the competition, if a registration is required.

        rated-register
        Register to the competition as a rated participant.

        unrated-register
        Register to the competition as an unrated participant.

    If no action is specified, prints the list of supported actions. Not all actions are supported on every judging system.
    """
    cmd = cmd.strip()
    if not cmd:
        actions = [ACTION_TO_COMMAND[i] for i in action_list(self.url, self.cookie) if i in ACTION_TO_COMMAND]
        if not actions:
            print("No actions supported on this judging system.")
        else:
            print("Supported actions:", ' '.join(actions))
    elif cmd in SIMPLE_ACTIONS:
        actions = [ACTION_TO_COMMAND[i] for i in action_list(self.url, self.cookie) if i in ACTION_TO_COMMAND]
        action, message = SIMPLE_ACTIONS[cmd]
        if action not in actions:
            raise BruteError(cmd+" is not supported on this judging system.")
        elif not do_action(self.url, self.cookie, action):
            raise BruteError("Failed to %s."%message)
    else:
        return self.do_help('control')

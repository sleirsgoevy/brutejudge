from brutejudge.http import submit, task_list, submission_list
from brutejudge.error import BruteError
import os.path

def do_asubmit(self, cmd):
    """
    usage: asubmit [-x <extension>] <task> <lang_id> <file>

    Submit a new solution, using style-fixed version.
    Uses a specific style fixer if -x is specified.
    """
    modname = None
    sp = cmd.split()
    if len(sp) not in (3, 5):
        return self.do_help('asubmit')
    if sp[0] == '-x':
        modname = sp[1]
        del sp[:2]
        if modname[:1] == '.': modname = 'brutejudge.commands.asubmit'+modname
    if len(sp) != 3:
        return self.do_help('asubmit')
    tasks = task_list(self.url, self.cookie)
    try: task_id = tasks.index(sp[0])
    except ValueError:
        raise BruteError("No such task.")
    if not sp[1].isnumeric():
        raise BruteError("lang_id must be a number")
    try:
        name = sp[2]
        if not os.path.exists(name):
            raise BruteError("File not found.")
        module = None
        ext = os.path.splitext(name)[1][1:]
        if modname == None: modname = 'brutejudge.commands.asubmit.format_'+ext
        try:
            module = __import__(modname, fromlist=True)
        except ImportError: pass
        if hasattr(module, 'read_file'):
            data = module.read_file(name)
        else:
            with open(name, 'rb') as file:
                data = file.read()
        if hasattr(module, 'format'):
            data = module.format(data)
    except UnicodeDecodeError:
        raise BruteError("File is binary.")
    before = submission_list(self.url, self.cookie)[0]
    submit(self.url, self.cookie, task_id, int(sp[1]), data)
    after = submission_list(self.url, self.cookie)[0]
    if before == after:
        raise BruteError("Error while sending.")
    else:
        print('Submission ID is', after[0])

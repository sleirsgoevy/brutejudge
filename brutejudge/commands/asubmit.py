from brutejudge.http import submit, task_list, submission_list
from brutejudge.error import BruteError
import os.path

def do_asubmit(self, cmd):
    """
    usage: asubmit <task> <lang_id> <file>

    Submit a new solution, using style-fixed version if available.
    """
    sp = cmd.split()
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
        names = [name[:-4]+'.autoifwhileforswitchspaced'+name[-4:],
                 name[:-3]+'.autodefnled'+name[-3:],
                 name]
        for name in names:
            if os.path.exists(name):
                with open(name, 'r') as file:
                    data = file.read()
                    break
        else:
            raise BruteError("File not found.")
    except UnicodeDecodeError:
        raise BruteError("File is binary.")
    before = submission_list(self.url, self.cookie)[0]
    submit(self.url, self.cookie, task_id, int(sp[1]), data)
    after = submission_list(self.url, self.cookie)[0]
    if before == after:
        raise BruteError("Error while sending.")

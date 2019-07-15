from brutejudge.http import task_list
from brutejudge.error import BruteError

class TaskList:
    def __init__(self, obj):
        self.obj = obj
        self.k2v = {}
        self.v2k = {}
    def __call__(self):
        return [self.k2v.get(i, i) for i in type(self.obj).task_list(self.obj)]

def setup_taskalias(self):
    if not isinstance(self.task_list, TaskList):
        self.task_list = TaskList(self)

def do_taskalias(self, cmd):
    """
    usage: taskalias <old=new> [old2=new2]...
           taskalias <new>...

    Rename tasks (for your convenience). This does not have any effect for other contestants.
    If using the second prototype, the number of arguments must match the number of tasks.
    """
    cmd = cmd.split()
    eq = ['=' in i for i in cmd]
    if not (cmd and (all(eq) or not any(eq))):
        return self.do_help('taskalias')
    setup_taskalias(self.url)
    if any(eq):
        pairs = [i.split('=', 1) for i in cmd]
    else:
        tasks = task_list(self.url, self.cookie)
        if len(tasks) != len(cmd):
            raise BruteError("The number of arguments must match the number of tasks.")
        pairs = list(zip(tasks, cmd))
    for k, v in pairs:
        try: k1 = self.url.task_list.v2k[k]
        except KeyError: pass
        else:
            del self.url.task_list.v2k[k]
            k = k1
        self.url.task_list.v2k[v] = k
        self.url.task_list.k2v[k] = v

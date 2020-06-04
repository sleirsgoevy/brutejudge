import collections
from brutejudge.http import task_list
from brutejudge.error import BruteError

class TaskAlias:
    def __init__(self, parent):
        self.parent = parent
        self.taskalias_k2v = {}
        self.taskalias_v2k = {}
    def task_list(self):
        return [self.taskalias_k2v.get(i, i) for i in self.parent.task_list()]
    def submission_list(self):
        a, b = self.parent.submission_list()
        return a, [self.taskalias_k2v.get(i, i) for i in b]
    def status(self):
        return collections.OrderedDict((self.taskalias_k2v.get(k, k), v) for k, v in self.parent.status().items())
    def scores(self):
        return collections.OrderedDict((self.taskalias_k2v.get(k, k), v) for k, v in self.parent.scores().items())
    def __getattr__(self, attr):
        return getattr(self.parent, attr)

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
    if not isinstance(self.url, TaskAlias): self.url = TaskAlias(self.url)
    if any(eq):
        pairs = [i.split('=', 1) for i in cmd]
    else:
        tasks = task_list(self.url, self.cookie)
        if len(tasks) != len(cmd):
            raise BruteError("The number of arguments must match the number of tasks.")
        pairs = list(zip(tasks, cmd))
    for k, v in pairs:
        try: k1 = self.url.taskalias_v2k[k]
        except KeyError: pass
        else:
            del self.url.taskalias_v2k[k]
            k = k1
        self.url.taskalias_v2k[v] = k
        self.url.taskalias_k2v[k] = v

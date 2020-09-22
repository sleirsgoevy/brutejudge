from brutejudge.http import tasks, problem_info, contest_info
from brutejudge.error import BruteError

def do_info(self, cmd):
    """
    usage: info [task]

    Show testing information and problem statement for a task, or for the whole contest if task is not specified.
    """
    cmd = cmd.strip()
    if cmd == '--help':
        return self.do_help('info')
    if cmd:
        try: task_id = next(i.id for i in tasks(self.url, self.cookie) if i.short_name == cmd)
        except StopIteration:
            raise BruteError("No such task.")
        a, b = problem_info(self.url, self.cookie, task_id)
    else:
        b, a, j = contest_info(self.url, self.cookie)
        print(j)
    for k, v in a.items(): print(k+': '+v)
    print()
    print(b)

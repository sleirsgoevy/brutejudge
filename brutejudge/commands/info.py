from brutejudge.http import task_list, task_ids, problem_info, contest_info
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
        tasks = task_list(self.url, self.cookie)
        try: task_id = task_ids(self.url, self.cookie)[tasks.index(cmd)]
        except (ValueError, IndexError):
            raise BruteError("No such task.")
        a, b = problem_info(self.url, self.cookie, task_id)
    else:
        b, a, j = contest_info(self.url, self.cookie)
        print(j)
    for k, v in a.items(): print(k+': '+v)
    print()
    print(b)

from brutejudge.http import task_list, task_ids, problem_info

def do_info(self, cmd):
    """
    usage: info <task>

    Show testing information and problem statement for a task.
    """
    cmd = cmd.strip()
    if not cmd:
        return self.do_help('info')
    tasks = task_list(self.url, self.cookie)
    try: task_id = task_ids(self.url, self.cookie)[tasks.index(cmd)]
    except (ValueError, IndexError):
        raise BruteError("No such task.")
    a, b = problem_info(self.url, self.cookie, task_id)
    for k, v in a.items(): print(k+': '+v)
    print()
    print(b)

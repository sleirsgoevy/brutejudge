import subprocess
from brutejudge.http import tasks, download_file
from brutejudge.error import BruteError

def do_getfile(self, cmd):
    """
    usage: getfile <prob_id> <file> <shell command>

    Retrieve a file attached to a task.
    """
    id, file, cmd = (cmd.strip()+'  ').split(' ', 2)
    if not id or not file:
        return self.do_help('getfile')
    try: task_id = next(i.id for i in tasks(self.url, self.cookie) if i.short_name == id)
    except StopIteration:
        raise BruteError("No such task.")
    data = download_file(self.url, self.cookie, task_id, file)
    p = subprocess.Popen('cat '+cmd, stdin=subprocess.PIPE, shell=True)
    p.stdin.write(data)
    p.stdin.close()
    p.wait()

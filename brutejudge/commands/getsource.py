import subprocess
from brutejudge.http import submission_source
from brutejudge.error import BruteError

def do_getsource(self, cmd):
    """
    usage: getsource <submission_id> <shell command>

    Retrieve the source code of a submission.
    """
    id, cmd = (cmd.strip()+' ').split(' ', 1)
    if not id.isnumeric():
        return self.do_help('getsource')
    src = submission_source(self.url, self.cookie, int(id))
    if src == None:
        raise BruteError('Source code is not available')
    p = subprocess.Popen('cat '+cmd, stdin=subprocess.PIPE, shell=True)
    p.stdin.write(src)
    p.stdin.close()
    p.wait()

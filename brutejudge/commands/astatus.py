import sys
from brutejudge.http import submissions
from brutejudge.error import BruteError

def still_running(s):
    return s.endswith('...') or ', ' in s or s in ('Compiling', 'Running', 'Judging', 'Check failed', 'Available for testing', 'Full rejudge', 'Pending check', 'Pending judgement', 'Queue judge', 'In queue', 'Running on pretest', 'Waiting for judging')

def do_astatus(self, cmd):
    """
    usage: astatus <subm_id>

    Fancy testing progress display
    """
    subm_id = cmd.strip() 
    if not subm_id.isnumeric():
        return self.do_help('astatus')
    chars = '\\|/-'
    idx = 0
    prev = ''
    subm_id = int(subm_id)
    while True:
        try:
            cur = next(i.status for i in submissions(self.url, self.cookie) if i.id == subm_id)
        except StopIteration:
            raise BruteError('No such submission')
        cur = cur.strip()
        sys.stderr.write(' '*len(prev)+'\r')
        sys.stderr.flush()
        if still_running(cur):
            prev = '%%%ds' % len(prev) % (cur + ' ' + chars[idx])
            idx = (idx + 1) % 4
#           print(prev)
            sys.stderr.write(prev+'\r')
            sys.stderr.flush()
        else:
            print(cur)
            break

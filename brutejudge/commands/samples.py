from brutejudge.http import get_samples
from brutejudge.error import BruteError
import os.path

def do_samples(self, cmd):
    """
    usage: samples <submission_id> <dump_dir>

    Dump sample test cases from a submission.
    """
    if len(cmd.split(' ')) < 2:
        return self.do_help("samples")
    cmd, ddir = cmd.split(' ', 1)
    if not cmd.isnumeric():
        raise BruteError("Submission ID must be a number")
    tests = get_samples(self.url, self.cookie, int(cmd))
    os.makedirs(ddir)
    for k, v in tests.items():
        for what, data in v.items():
            if what == 'Input':
                suff = ''
            elif what == 'Correct':
                suff = '.a'
            else:
                suff = '_'+what.replace(' ', '_')+'.txt'
            with open(os.path.join(ddir, '%02d' % k + suff), 'w') as file:
                file.write(data)

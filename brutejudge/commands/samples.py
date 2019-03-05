from brutejudge.http import compile_error
from brutejudge.error import BruteError
import os.path

def get_samples(url, cookie, subm_id):
    err = compile_error(url, cookie, subm_id)
    if err == None: err = ''
    err = err.strip()
    if not err.startswith("====== Test #"):
        raise BruteError("No test cases available")
    lines = iter(err.split('\n'))
    tests = {}
    curr = None
    for line in lines:
        if line.startswith("====== Test #"):
            num = int(line[13:-7])
            curr = tests[num] = {}
        elif line.startswith('--- '):
            line = line[4:-4]
            if ': size ' not in line: continue
            what, size = line.split(': size ')
            size = int(size) + 1
            data = ''
            while len(data) < size:
                try: data += '\n' + next(lines)
                except StopIteration: break
            data = data[1:]
            curr[what] = data
    return tests

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
    tests = get_samples(self.url, self.cookie, cmd)
    os.makedirs(ddir)
    for k, v in tests.items():
        for what, data in v.items():
            if what == 'Input':
                suff = ''
            elif what == 'Correct':
                suff = '.a'
            else:
                suff = '_'+what.replace('_', ' ')+'.txt'
            with open(os.path.join(ddir, '%02d' % k + suff), 'w') as file:
                file.write(data)

from brutejudge.http import get_samples
from brutejudge.error import BruteError
import os.path, sys

def do_samples(self, cmd):
    """
    usage: samples <submission_id> (<dump_dir> || --input || --output || --correct || --stderr || --checker)

    Dump sample test cases from a submission. If a flag is specified, dump the corresponding files to standard output.
    """
    if len(cmd.split(' ')) < 2:
        return self.do_help("samples")
    cmd, ddir = cmd.split(' ', 1)
    if not cmd.isnumeric():
        raise BruteError("Submission ID must be a number")
    tests = get_samples(self.url, self.cookie, int(cmd))
    flags = {'--input': 'Input', '--output': 'Output', '--correct': 'Correct', '--stderr': 'Stderr', '--checker': 'Checker output'}
    if ddir not in flags:
        os.makedirs(ddir)
    out_sep = False
    for k, v in tests.items():
        for what, data in v.items():
            if ddir in flags:
                if what == flags[ddir]:
                    if out_sep: print('#'*20)
                    else: out_sep = True
                    sys.stdout.write(data)
                    sys.stdout.flush()
                continue
            if what == 'Input':
                suff = ''
            elif what == 'Correct':
                suff = '.a'
            else:
                suff = '_'+what.replace(' ', '_')+'.txt'
            with open(os.path.join(ddir, '%02d' % k + suff), 'w') as file:
                file.write(data)

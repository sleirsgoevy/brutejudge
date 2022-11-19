from brutejudge.http import get_samples, has_feature
from brutejudge.error import BruteError
import os.path, sys

def do_samples(self, cmd):
    """
    usage: samples [--binary] <submission_id> (<dump_dir> || --input || --output || --correct || --stderr || --checker)

    Dump sample test cases from a submission. If a flag is specified, dump the corresponding files to standard output.
    """
    if len(cmd.split(' ')) < 2:
        return self.do_help("samples")
    cmd, ddir = cmd.split(' ', 1)
    kwargs = {}
    if cmd == '--binary':
        if not has_feature(self.url, self.cookie, 'get_samples', 'binary'):
            raise BruteError("This system does not support --binary in samples.")
        kwargs['binary'] = True
        if len(ddir.split(' ')) < 2:
            return self.do_help("samples")
        cmd, ddir = ddir.split(' ', 1)
    if not cmd.isnumeric():
        raise BruteError("Submission ID must be a number")
    tests = get_samples(self.url, self.cookie, int(cmd), **kwargs)
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
                    (sys.stdout.buffer if 'binary' in kwargs else sys.stdout).write(data)
                    (sys.stdout.buffer if 'binary' in kwargs else sys.stdout).flush()
                    if 'binary' not in kwargs and not data.endswith('\n'):
                        print()
                continue
            if what == 'Input':
                suff = ''
            elif what == 'Correct':
                suff = '.a'
            else:
                suff = '_'+what.replace(' ', '_')+'.txt'
            with open(os.path.join(ddir, '%02d' % k + suff), 'wb' if 'binary' in kwargs else 'w') as file:
                file.write(data)

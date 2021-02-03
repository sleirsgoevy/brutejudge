import brutejudge.cheats
from brutejudge.commands.asubmit import get_possible_lang_id
from brutejudge.commands.astatus import still_running
from brutejudge.commands.samples import get_samples
from brutejudge.http import tasks, submit_solution, submission_list, submission_status, compile_error
from brutejudge._http.codeforces import CodeForces
from brutejudge.error import BruteError
import shlex, sys, random

base64_filter = r"""
string alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
string s2;
int zzz_cnt = 0;
while(included_s.size() % 3)
{
    zzz_cnt++;
    included_s.push_back('\0');
}
for(int i = 0; i < included_s.size(); i += 3)
{
#define char2int(x) (((unsigned int)(x))&255)
    int num = 65536 * char2int(included_s[i]) + 256 * char2int(included_s[i + 1]) + char2int(included_s[i + 2]);
    s2.push_back(alphabet[num >> 18]);
    s2.push_back(alphabet[(num >> 12) & 63]);
    s2.push_back(alphabet[(num >> 6) & 63]);
    s2.push_back(alphabet[num & 63]);
#undef char2int
}
for(int i = -zzz_cnt; i < 0; i++)
    s2[s2.size() - i] = '=';
included_s = s2;
"""

def do_incat(self, cmd):
    """
    usage: incat [--base64] <task> <filepath> [savepath]

    Tries to retrieve the specified ASCII file using .incbin directive.
    The data will be base64-encoded if --base64 is specified.
    """
    brutejudge.cheats.cheating(self)
    data = shlex.split(cmd)
    filter = ''
    if data and data[0] == '--base64':
        filter = base64_filter
        del data[0]
    if len(data) not in (2, 3):
        return self.do_help('incat')
    data.append(None)
    task, filepath, savepath = data[:3]
    task_list = tasks(self.url, self.cookie)
    for i in task_list:
        if i[1] == task:
            task_id = i[0]
            break
    else:
        raise BruteError("No such task.")
    if savepath == None:
        f = sys.stdout
    else:
        f = open(savepath, "w")
    incat(self, task, task_id, filepath, f, filter=filter)
    if savepath != None: f.close()

class IncatCompileError(BruteError):
    def __init__(self, msg, err):
        BruteError.__init__(self, msg)
        self.err = err

def incat(self, task, task_id, filepath, f, filter='', custom_include=None):
    if isinstance(filepath, str): filepath = (filepath,)
    filepath = tuple('/'.join(['..']*15)+i if i.startswith('/') else i for i in filepath)
    lans = 0
    rot_str = '\\|/-'
    idx = 0
    while True:
        sys.stderr.write(rot_str[idx])
        sys.stderr.flush()
        subm1 = list(zip(*submission_list(self.url, self.cookie)))
        idx = (idx + 1) % 4
        sys.stderr.write('\b'+rot_str[idx])
        sys.stderr.flush()
        include_code = ('.incbin \\"%s\\"\\n' if custom_include == None else custom_include) % filepath
        cerr_output = r"""
    if(%d < included_s.size())
        cerr << included_s.substr(%d, 65536);"""%(lans + 65536, lans + 65536)
        submit_solution(self.url, self.cookie, task_id, get_possible_lang_id(self, ('g++', 'g++-32'), task_id), r"""
asm("included:\n%s.byte 0\nincluded_length:\n.long included_length-included-1");

//random: %r

#include <bits/stdc++.h>

using namespace std;

extern char included[];
extern int included_length;

int main()
{
    string included_s(included, included_length);
    %sif(%d < included_s.size())
        %s << included_s.substr(%d, 65536);%s
    return 0;
}
"""%(include_code, random.random(), (filter.strip()+'\n').replace('\n', '\n    '), lans, 'ifstream("%s")'%self.input_file if hasattr(self, 'input_file') else 'cout', lans, cerr_output if not isinstance(self.url, CodeForces) else ''))
        idx = (idx + 1) % 4
        sys.stderr.write('\b'+rot_str[idx])
        sys.stderr.flush()
        subm2 = list(zip(*submission_list(self.url, self.cookie)))
        if subm2[1:] != subm1 or not subm2 or subm2[0][1] != task:
            raise BruteError("Error while sending.")
        subm_id = subm2[0][0]
        while True:
            idx = (idx + 1) % 4
            sys.stderr.write('\b'+rot_str[idx])
            sys.stderr.flush()
            if not still_running(submission_status(self.url, self.cookie, subm_id)): break
        sys.stderr.write('\b \b')
        sys.stderr.flush()
        idx = (idx + 1) % 4
        if submission_status(self.url, self.cookie, subm_id) in ('Compilation error', 'Compiler failed'):
            raise IncatCompileError("Compilation error.", compile_error(self.url, self.cookie, subm_id))
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

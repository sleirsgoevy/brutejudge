import brutejudge.cheats
from brutejudge.http import compile_error, submission_status
from brutejudge.error import BruteError
import os.path

def get_tailcode(self, subm_id, suf):
    if submission_status(self.url, self.cookie, subm_id) != 'Compilation error':
        raise BruteError("Submission didn't fail to compile")
    err = compile_error(self.url, self.cookie, subm_id)
    if err == None: err = ''
    err = err.strip()
    lines = {}
    it = iter(err.split('\n'))
    for line in it:
        if not line[:1].isspace():
            l = (line + ':::').split(':')
            if l[0].endswith(suf) and l[1].isnumeric() and l[2].isnumeric():
                lineno = int(l[1])
                if lineno not in lines:
                    try: lines[lineno] = next(it).strip()
                    except StopIteration: break
    if not lines: return ''
    minno = min(lines)
    maxno = max(lines)
    ans = ''
    for i in range(minno, maxno+1):
        ans += lines.get(i, '###### FAILED TO FETCH ######')+'\n'
    return ans

def do_tailcode(self, cmd):
    """
    usage: tailcode <submission_id> <dump_path> [filename_suffix]

    Dump tail code used for testing.
    """
    brutejudge.cheats.cheating(self)
    if len(cmd.split(' ')) not in (2, 3):
        return self.do_help("tailcode")
    cmd, dpath = cmd.split(' ', 1)
    if ' ' in dpath:
        dpath, suf = dpath.rsplit(' ', 1)
    else:
        suf = ".cpp"
    if not cmd.isnumeric():
        raise BruteError("Submission ID must be a number")
    with open(dpath, 'w') as file:
        file.write(get_tailcode(self, int(cmd), suf))

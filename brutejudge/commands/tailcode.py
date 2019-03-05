from brutejudge.http import compile_error, submission_status
from brutejudge.error import BruteError
import os.path

def do_tailcode(self, cmd):
    """
    usage: tailcode <submission_id> <dump_path> [filename_suffix]

    Dump tail code used for testing.
    """
    if len(cmd.split(' ')) not in (2, 3):
        return self.do_help("tailcode")
    cmd, dpath = cmd.split(' ', 1)
    if ' ' in dpath:
        dpath, suf = dpath.split(' ', 1)
    else:
        suf = ".cpp"
    if not cmd.isnumeric():
        raise BruteError("Submission ID must be a number")
    if submission_status(self.url, self.cookie, int(cmd)) != 'Compilation error':
        raise BruteError("Submission didn't fail to compile")
    err = compile_error(self.url, self.cookie, cmd)
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
    minno = min(lines)
    maxno = max(lines)
    with open(dpath, 'w') as file:
        for i in range(minno, maxno+1):
            print(lines.get(i, '###### FAILED TO FETCH ######'), file=file)

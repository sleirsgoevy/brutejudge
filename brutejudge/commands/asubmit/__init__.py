from brutejudge.http import submit_solution, tasks, submissions, compiler_list, may_cache
from brutejudge.error import BruteError
import os.path, shlex, sys

def get_lang_id(self, lang_name, task_id):
    lang_id = [i for i, j, k in compiler_list(self.url, self.cookie, task_id) if j == lang_name]
    try: lang_id, = lang_id
    except ValueError: raise BruteError("Unknown language: "+lang_name)
    return lang_id

def get_possible_lang_id(self, lang_names, task_id):
    lang_id = [i for i, j, k in compiler_list(self.url, self.cookie, task_id) if j in lang_names]
    lang_id.append(None)
    return lang_id[0]

def check_exists(fname, options=set()):
    return os.path.exists(fname) or '-exist' in options

def do_asubmit(self, cmd, *, afmt=False):
    """
    usage: asubmit [-w] [-x <extension>] <task> <lang_id> <file>

    Submit a new solution, using style-fixed version.
    Uses a specific style fixer if -x is specified.
    Waits until testing ends if -w is specified.
    """
    modname = ''
    wait = False
    sp = shlex.split(cmd)
    if len(sp) not in (range(3, 7) if not afmt else (1, 3)):
        return self.do_help('aformat' if afmt else 'asubmit')
    if not afmt and sp[0] == '-w':
        wait = True
        del sp[0]
    if len(sp) not in ((3, 5) if not afmt else (1, 3)):
        return self.do_help('aformat' if afmt else 'asubmit')
    if sp[0] == '-x':
        modname = sp[1]
        del sp[:2]
        if modname[:1] == '.': modname = 'brutejudge.commands.asubmit.format_'+modname[1:]
    if len(sp) != (1 if afmt else 3):
        return self.do_help('aformat' if afmt else 'asubmit')
    try:
        name = sp[-1]
        module = None
        ext = os.path.splitext(name)[1][1:]
        modname, *modargs = modname.split(',')
        modargs = set(modargs)
        if not modname: modname = 'brutejudge.commands.asubmit.format_'+ext
        try:
            module = __import__(modname, fromlist=True)
        except ImportError: pass
        if hasattr(module, 'cheats'):
            import brutejudge.cheats
            brutejudge.cheats.cheating(self)
        if not getattr(module, 'check_exists', check_exists)(name, modargs):
            raise BruteError("File not found.")
        if hasattr(module, 'read_file'):
            data = module.read_file(name, modargs)
        else:
            with open(name, 'rb') as file:
                data = file.read()
        if hasattr(module, 'format'):
            data = module.format(data, modargs)
    except UnicodeDecodeError:
        raise BruteError("File is binary.")
    if afmt:
        if isinstance(data, str): data = data.encode('utf-8')
        sys.stdout.buffer.write(data)
        sys.stdout.buffer.flush()
        return
    with may_cache(self.url, self.cookie):
        try: task_id = next(i.id for i in tasks(self.url, self.cookie) if i.short_name == sp[0])
        except StopIteration:
            raise BruteError("No such task.")
        if not sp[1].isnumeric():
            sp[1] = get_lang_id(self, sp[1], task_id)
        before = submissions(self.url, self.cookie)
        submit_solution(self.url, self.cookie, task_id, int(sp[1]), data)
    after = submissions(self.url, self.cookie)
    if before == after:
        raise BruteError("Error while sending.")
    else:
        print('Submission ID is', after[0].id)
        if wait: self.do_astatus(str(after[0].id))

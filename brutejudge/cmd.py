import cmd, sys, traceback, os, shlex
from .http import login, tasks, submissions, submission_protocol, submit_solution, status, scores, compile_error, submission_source, compiler_list, submission_stats, has_feature, contest_list
from .error import BruteError
import brutejudge.commands

def isspace(s):
    return not s or s.isspace()

class BruteCMD(cmd.Cmd):
    prompt = 'brutejudge> '
    def __init__(self):
        cmd.Cmd.__init__(self)
        self._url = None
        self._cookie = None
    @property
    def url(self):
        if self._url != None: return self._url
        raise BruteError("Not logged in")
    @url.setter
    def url(self, val):
        self._url = val
    @property
    def cookie(self):
        if self._cookie != None: return self._cookie
        raise BruteError("Not logged in")
    @cookie.setter
    def cookie(self, val):
        self._cookie = val
    def do_login(self, cmd):
        """
        usage: login <login_page_url> <username>

        Login to CMS.
        """
        data = cmd.split(' ')
        if len(data) != 2:
            return self.do_help('login')
        import getpass
        x = getpass.getpass()
        self.url, self.cookie = login(data[0], data[1], x)
    def do_logout(self, cmd):
        """
        usage: logout

        Logout from CMS.
        """
        if not isspace(cmd):
            return self.do_help('logout')
        self.url = self.cookie = None
    def do_lsc(self, cmd):
        """
        usage: lsc [url]

        List all contests for the given URL, and their corresponding login URLs.
        """
        if isspace(cmd):
            url, cookie = self.url, self.cookie
        else:
            url = cmd
            cookie = None
        data = contest_list(url, cookie)
        print("URL\tTitle")
        for url, title, _ in data:
            print(url+'\t'+title)
    def do_tasks(self, cmd):
        """
        usage: tasks [--verbose]

        Show task list. If --verbose is specified, also show additional information.
        """
        if not isspace(cmd) and cmd.strip() != '--verbose':
            return self.do_help('tasks')
        data = tasks(self.url, self.cookie)
        if cmd.strip() == '--verbose':
            print('Short name\tLong name')
            for i, j, k in data: print(j, k, sep='\t\t')
        else:
            print(*[i[1] for i in data])
    def do_submissions(self, cmd):
        """
        usage: submissions [subm_id]

        Show a list of submissions or detailed log for a single submission.
        """
        if not (isspace(cmd) or cmd.strip().isnumeric()):
            return self.do_help('submissions')
        if isspace(cmd):
            print('Submission ID\tTask\tStatus\t\t\tScore\tTests passed')
            for x in reversed(submissions(self.url, self.cookie)):
                print('%d\t\t%s\t%s\t%s\t%s'%tuple(i if i != None else '' for i in x))
        else:
            print('Test\tVerdict\t\tTime usage\tMemory usage\t...')
            for t, (i, j) in enumerate(submission_protocol(self.url, self.cookie, int(cmd))):
                tl = ''
                if 'time_usage' in j:
                    tl = '%0.3f'%j['time_usage']
                    del j['time_usage']
                ml = ''
                if 'memory_usage' in j:
                    ml = j['memory_usage']
                    del j['memory_usage']
                    if ml < 2**10: ml = '%d B' % ml
                    elif ml < 2**20: ml = '%.1f KiB' % (ml / 2**10)
                    elif ml < 2**30: ml = '%.1f MiB' % (ml / 2**20)
                    elif ml < 2**40: ml = '%.1f GiB' % (ml / 2**30)
                    elif ml < 2**50: ml = '%.1f TiB' % (ml / 2**40)
                    elif ml < 2**60: ml = '%.1f PiB' % (ml / 2**50)
                    else: ml = '%.1f EiB' % (ml / 2**60)
                print('%03d\t%s\t%s\t\t%s\t%s'%(t+1, i, tl, ml, repr(j) if j else ''))
    def do_submit(self, cmd):
        """
        usage: submit <task> <lang_id> <file>

        Submit a new solution.
        """
        sp = cmd.split()
        if len(sp) != 3:
            return self.do_help('submit')
        task_list = tasks(self.url, self.cookie)
        try: task_id = next(i.id for i in task_list if i.short_name == sp[0])
        except StopIteration:
            raise BruteError("No such task.")
        if not sp[1].isnumeric():
            raise BruteError("lang_id must be a number")
        try:
            with open(sp[2], 'rb') as file:
                data = file.read()
        except FileNotFoundError:
            raise BruteError("File not found.")
#       except UnicodeDecodeError:
#           raise BruteError("File is binary.")
        submit_solution(self.url, self.cookie, task_id, int(sp[1]), data)
    def do_shell(self, cmd):
        """
        usage: shell <command>

        Run a shell command.
        """
        os.system('bash -c '+shlex.quote(cmd))
    def do_status(self, cmd):
        """
        usage: status [submission_id]

        Show summary.
        """
        if not (isspace(cmd) or cmd.strip().isnumeric()):
            return self.do_help('status')
        if not isspace(cmd):
            splitted = cmd.split()
            if len(splitted) != 1:
                return self.do_help('status')
            for i in submissions(self.url, self.cookie):
                if i.id == int(splitted[0]):
                    print(i.status)
            return
        ans = status(self.url, self.cookie)
        print('Task\tStatus')
        for k, v in list(ans.items()):
            print(k+'\t'+str(v))
    def do_scores(self, cmd):
        """
        usage: scores [subm_id]

        Show score for a solution if subm_id is specified.
        Show scores for each task if subm_id is not specified.
        """
        if isspace(cmd):
            if has_feature(self.url, self.cookie, 'scores', 'total'):
                ans = scores(self.url, self.cookie, total=True)
            else:
                ans = scores(self.url, self.cookie)
            print('Task\tScore')
            for k, v in ans.items():
                if k is not True:
                    print(k+'\t'+str(v))
            if True in ans:
                print('Total score:', ans[True])
        else:
            if len(cmd.split()) != 1:
                return self.do_help('scores')
            try: subm_id = int(cmd)
            except ValueError:
                return self.do_help('scores')
            for i in submissions(self.url, self.cookie):
                if i.id == subm_id:
                    print(i.score)
    def do_source(self, cmd):
        """
        usage: source <submission_id>

        Show program source code for a solution.
        """
        if not cmd.strip().isnumeric():
            return self.do_help('source')
        src = submission_source(self.url, self.cookie, int(cmd))
        if src == None:
            raise BruteError('Source code is not available')
        print(src.decode('utf-8', 'replace'))
    def onecmd(self, c):
        try:
            try: return cmd.Cmd.onecmd(self, c)
            except (BruteError, SystemExit): raise
            except BaseException:
                raise BruteError(traceback.format_exc())
        except BruteError as e:
            self.print_error(e)
    def print_error(self, e):
        print(e, file=sys.stderr)
    def __getattr__(self, cmd):
        if not cmd.startswith('do_'): raise AttributeError(cmd)
        cmd = cmd[3:]
        try: __import__('brutejudge.commands.' + cmd)
        except ImportError: raise AttributeError(cmd)
        return type(self.__getattr__)(getattr(getattr(brutejudge.commands, cmd), 'do_'+cmd), self)
    def get_names(self):
        dir0 = set(dir(type(self)))
        import pkgutil
        try: cmds = list(pkgutil.iter_modules(brutejudge.commands.__path__))
        except: pass
        else: dir0 |= {'do_'+i[1] for i in cmds if not i[1].startswith('_')}
        return list(dir0)
    def default(self, cmd):
#       cmd, arg = (cmd.strip()+' ').split(' ', 1)
#       arg = arg.strip()
#       try: __import__('brutejudge.commands.' + cmd)
#       except ImportError:
        raise BruteError('No such command: ' + cmd.split()[0])
#       return getattr(getattr(brutejudge.commands, cmd), 'do_'+cmd)(self, arg)
    def do_EOF(self, cmd=None):
        print(file=sys.stderr)
        sys.exit(0)
    def do_python(self, cmd):
        if cmd and not cmd.isspace():
            exec(compile(cmd, '<string>', 'single'))
        else:
            import code
            code.interact(local={'self': self})
    def do_geterror(self, cmd):
        """
        usage: geterror [--binary] [--kind <kind>] <subm_id>

        Get errors for submission (if any).
        Possible kinds (default order):
           --. Judge comment
            2. Valuer comment
            1. Compilation error
            3. Binary executable file (JJS only)
        """
        sp = cmd.split()
        kwargs = {}
        if sp and sp[0] == '--binary':
            if not has_feature(self.url, self.cookie, 'compile_error', 'binary'):
                raise BruteError('This system does not support --binary in geterror.')
            del sp[0]
            kwargs['binary'] = True
        if len(sp) >= 2 and sp[0] == '--kind':
            if not has_feature(self.url, self.cookie, 'compile_error', 'kind'):
                raise BruteError('This system does not support --kind in geterror.')
            try: kwargs['kind'] = int(sp[1])
            except ValueError:
                raise BruteError('Kind must be a number')
            del sp[:2]
        if len(sp) != 1:
            return self.do_help('geterror')
        try: sp[0] = int(sp[0])
        except ValueError:
            raise BruteError('Submission ID must be a number')
        ans = compile_error(self.url, self.cookie, sp[0], **kwargs)
#       except IndexError:
#           print('Success')
        if isinstance(ans, bytes):
            sys.stdout.buffer.raw.write(ans)
        else:
            print(ans)
    def do_compilers(self, cmd):
        """
        usage: compilers <task>

        Get list of all all available compilers
        """
        task = cmd.strip()
        if not task:
            return self.do_help('compilers')
        try:
            prob_id = next(i.id for i in tasks(self.url, self.cookie) if i.short_name == task)
        except StopIteration:
            raise BruteError("No such task")
        ans = compiler_list(self.url, self.cookie, prob_id)
        print("ID\tCompiler")
        for i, j, k in ans:
            print(i, j+' - '+k, sep='\t')
    def do_stats(self, cmd):
        """
        usage: stats <subm_id>

        Show statistics for a given submission
        """
        sp = cmd.split()
        if len(sp) != 1:
            return self.do_help('stats')
        if not sp[0].isnumeric():
            raise BruteError('Submission ID must be a number')
        stats, stats_str = submission_stats(self.url, self.cookie, int(sp[0]))
        if stats_str != None: print(stats_str.strip())
        import pprint
        pprint.pprint(stats)

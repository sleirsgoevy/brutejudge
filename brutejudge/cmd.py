import cmd, sys, traceback, os
from .http import login, task_list, submission_list, submission_results, submission_status, submit, status, scores, compile_error
from .error import BruteError
import brutejudge.commands

def isspace(s):
    return not s or s.isspace()

class BruteCMD(cmd.Cmd):
    prompt = 'brutejudge> '
    def __init__(self):
        cmd.Cmd.__init__(self)
        self.url = None
        self.cookie = None
    def do_login(self, cmd):
        """
        usage: login <login_page_url> <username>

        Login to ejudge.
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

        Logout from ejudge.
        """
        if not isspace(cmd):
            return self.do_help('logout')
        self.url = self.cookie = None
    def do_tasks(self, cmd):
        """
        usage: tasks

        Show task list.
        """
        if not isspace(cmd):
            return self.do_help('tasks')
        data = task_list(self.url, self.cookie)
        print(*data)
    def do_submissions(self, cmd):
        """
        usage: submissions [subm_id]

        Show a list of submissions or detailed log for a single submission.
        """
        if not (isspace(cmd) or cmd.strip().isnumeric()):
            return self.do_help('submissions')
        if isspace(cmd):
            print('Submission ID\tTask')
            for i, j in zip(*submission_list(self.url, self.cookie)):
                print('%s\t\t%s'%(i, j))
        else:
            for i, j in zip(*submission_results(self.url, self.cookie, int(cmd))):
                print(i, j)
    def do_submit(self, cmd):
        """
        usage: submit <task> <lang_id> <file>

        Submit a new solution.
        """
        sp = cmd.split()
        if len(sp) != 3:
            return self.do_help('submit')
        tasks = task_list(self.url, self.cookie)
        try: task_id = tasks.index(sp[0])
        except ValueError:
            raise BruteError("No such task.")
        if not sp[1].isnumeric():
            raise BruteError("lang_id must be a number")
        try:
            with open(sp[2], 'r') as file:
                data = file.read()
        except FileNotFoundError:
            raise BruteError("File not found.")
        except UnicodeDecodeError:
            raise BruteError("File is binary.")
        submit(self.url, self.cookie, task_id, int(sp[1]), data)
    def do_shell(self, cmd):
        """
        usage: shell <command>

        Run a shell command.
        """
        os.system(cmd)
    def do_status(self, cmd):
        """
        usage: status [submission_id]

        Show summary.
        """
        if not isspace(cmd):
            splitted = cmd.split()
            if len(splitted) != 1:
                return self.do_help('status')
            print(submission_status(self.url, self.cookie, int(splitted[0])))
            return
        ans = status(self.url, self.cookie)
        print('Task\tStatus')
        for k, v in ans.items():
            print(k+'\t'+v)
    def do_scores(self, cmd):
        """
        usage: scores

        Show scores for each task.
        """
        if not isspace(cmd):
            return self.do_help('status')
        ans = scores(self.url, self.cookie)
        print('Task\tScore')
        for k, v in ans.items():
            print(k+'\t'+str(v))
    def onecmd(self, c):
        try:
            try: return cmd.Cmd.onecmd(self, c)
            except BruteError: raise
            except Exception:
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
    def default(self, cmd):
#       cmd, arg = (cmd.strip()+' ').split(' ', 1)
#       arg = arg.strip()
#       try: __import__('brutejudge.commands.' + cmd)
#       except ImportError:
        raise BruteError('No such command: ' + cmd.split()[0])
#       return getattr(getattr(brutejudge.commands, cmd), 'do_'+cmd)(self, arg)
    def do_EOF(self, cmd=None):
        print()
        exit()
    def do_geterror(self, cmd):
        """
        usage: geterror <subm_id>

        Get compile-time errors for submission (if any).
        """
        sp = cmd.split()
        if len(sp) != 1:
            return self.do_help('geterror')
        try: print(compile_error(self.url, self.cookie, int(sp[0])))
        except ValueError:
            raise BruteError('Submission ID must be a number')
        except IndexError:
            print('Success')

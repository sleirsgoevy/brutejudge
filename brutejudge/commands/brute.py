import brutejudge.cheats
from brutejudge.http import task_list
from brutejudge.search import Searcher
from brutejudge.error import BruteError

def do_brute(self, cmd):
    """
    usage: brute <task> <reader> [dump_path] [max_count]

    Tries to retrieve the test cases using binary search.
    """
    brutejudge.cheats.cheating(self)
    sp = cmd.split()
    if len(sp) not in range(2, 5):
        return self.do_help('brute')
    tasks = task_list(self.url, self.cookie)
    try: task_id = tasks.index(sp[0])
    except ValueError:
        raise BruteError("No such task.")
    try:
        with open(sp[1]) as file:
            code = file.read()
    except FileNotFoundError:
        raise BruteError("File not found.")
    srch = Searcher(self.url, self.cookie, task_id, input_file=getattr(self, 'input_file', None), output_file=getattr(self, 'output_file', None))
    max_tests = -1
    if len(sp) == 4:
        try: max_tests = int(sp[3])
        except ValueError:
            raise BruteError("max_tests must be a number")
    srch.execute(code, max_tests)
    if len(sp) == 2 or sp[2] == '-':
        from sys import stdout as file
        do_close = False
    else:
        try: file = open(sp[2], "a")
        except IOError as e:
            raise BruteError("Error creating output file: " + str(e))
        do_close = True
    for i, t in enumerate(srch.tests):
        print("---------- test #", i, sep='', file=file)
        print(t, file=file)
    

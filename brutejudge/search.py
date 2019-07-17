import brutejudge.cheats
from brutejudge.commands.asubmit import get_possible_lang_id
import brutejudge.http as http
from .error import BruteError
from .injector import Injector

class Finished(BaseException):
    pass

class Searcher:
    def __init__(self, url, cookie, task, input_file=None, output_file=None):
        self.url = url
        self.cookie = cookie
        self.task = task
        self.injector = Injector()
        self.testno = 0
        self.itemno = 0
        self.index = 0
        self.test_data = []
        self.answer = ''
        self.tests = []
        self.input_file = input_file
        self.output_file = output_file
    def __getattr__(self, attr):
        def func(*args):
            print("#brute:", attr, args)
            submissions0 = http.submission_list(self.url, self.cookie)
            http.submit(self.url, self.cookie, self.task, get_possible_lang_id(self, ('python3', 'pypy3'), self.task), self.injector.call(attr, *args, input_file=self.input_file, output_file=self.output_file))
            result = [[]]
            submissions = http.submission_list(self.url, self.cookie)
            if submissions == submissions0:
                raise BruteError("Error sending.")
            while not result[0]:
                result = http.submission_results(self.url, self.cookie, submissions[0][0])
            if self.testno >= len(result[0]):
                raise Finished
            print("#result:", result[0][self.testno])
            return result[0][self.testno] in ('OK', 'Wrong answer', 'Presentation error')
        return func
    def int(self, start, stop):
        assert self.index == 0
        while stop - start > 1:
            mid = (start + stop) // 2
            if self.bin_int(self.itemno, mid):
                stop = mid
            else:
                start = mid
        self.test_data.append(start)
        self.itemno += 1
        return start
    def char(self, values=''.join(map(chr, range(128)))):
        values = list(map(ord, values))
        values.sort()
        start = 0
        stop = len(values) + 1
        while stop - start > 1:
            mid = (start + stop) // 2
            if self.bin_char(self.itemno, self.index, values[mid]):
                stop = mid
            else:
                start = mid
        if start == len(values):
            return None
        self.index += 1
        self.test_data.append(chr(values[start]))
        return self.test_data[-1]
    def space(self):
        self.index = 0
        self.test_data.append(' ')
    def newline(self):
        self.index = 0
        self.test_data.append('\n')
    def print(self, *args, sep=' ', end='\n'):
        self.answer += sep.join(map(str, args)) + end
    def next_test(self):
        test = ''.join(map(str, self.test_data))
        self.injector.add_test(test, self.answer)
        self.test_data = []
        self.answer = ''
        self.testno += 1
        self.itemno = 0
        self.index = 0
        self.tests.append(test)
    def execute(self, code, max_tests=-1):
        new_globals = dict(globals())
        new_globals['brute'] = self
        try:
            while max_tests != 0:
                exec(code, new_globals, {'brute': self})
                self.next_test()
                max_tests -= 1
        except Finished:
            pass


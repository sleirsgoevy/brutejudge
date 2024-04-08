import brutejudge.cheats
import os
from .injected import injected

class Injector:
    def __init__(self):
        self.tests = {}
    @staticmethod
    def superstrip(v):
        return '\n'.join(i.rstrip() for i in v.strip().split('\n'))
    def add_test(self, k, v):
        self.tests[self.superstrip(k)] = self.superstrip(v)
    def call(self, func, *args, input_file=None, output_file=None):
        if input_file == None:
            stdin = "sys.stdin"
        else:
            stdin = "open(%r)" % input_file
        if output_file == None:
            stdout = "sys.stdout"
        else:
            stdout = "open(%r, 'w')" % output_file
        return '#nonce: %s\n\nTESTS = %r\n%s\n%s%r\n'%(os.urandom(16).hex(), self.tests, injected % (stdin, stdout), func, args)


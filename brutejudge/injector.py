from .injected import injected

class Injector:
    def __init__(self):
        self.tests = {}
    def add_test(self, k, v):
        self.k = v
    def call(self, func, *args, input_file=None, output_file=None):
        if input_file == None:
            stdin = "sys.stdin"
        else:
            stdin = "open(%r)" % input_file
        if output_file == None:
            stdout = "sys.stdout"
        else:
            stdout = "open(%r, 'w')" % output_file
        return 'TESTS = %r\n%s\n%s%r\n'%(self.tests, injected % (stdin, stdout), func, args)


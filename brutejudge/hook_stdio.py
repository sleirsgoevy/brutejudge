import sys, threading, io, subprocess

class TLDProxy:
     def __init__(self, default):
         object.__setattr__(self, '_default', default)
         object.__setattr__(self, '_tld', threading.local())
     @property
     def _the_tld(self):
         try: return self._tld.value
         except AttributeError: return self._default
     def __getattr__(self, attr):
         return getattr(self._the_tld, attr)
     def __setattr__(self, attr, val):
         setattr(self._the_tld, attr, val)
     def __delattr__(self, attr):
         delattr(self._the_tld, attr)

class MonkeyPopen(subprocess.Popen):
    def __init__(self, *args, **kwds):
        args = list(args)
        if len(args) or 'args' in kwds:
            for i, (k, d) in enumerate((('args', None), ('bufsize', -1), ('executable', None), ('stdin', None), ('stdout', None), ('stderr', None))):
                if len(args) <= i:
                    args.append(kwds.pop(k, d))
            if args[3] == None: args[3] = sys.stdin
            if args[4] == None: args[4] = sys.stdout
            if args[5] == None: args[5] = sys.stderr
            if args[5] == subprocess.STDOUT: args[5] = sys.stdout
        super().__init__(*args, **kwds)

def hook_stdio():
    sys.stdin = io.TextIOWrapper(TLDProxy(sys.stdin.buffer), line_buffering=True)
    sys.stdout = io.TextIOWrapper(TLDProxy(sys.stdout.buffer), line_buffering=True)
    sys.stderr = io.TextIOWrapper(TLDProxy(sys.stderr.buffer), line_buffering=True)
    subprocess.Popen = MonkeyPopen

hook_stdio()

class RedirectSTDIO:
    def __init__(self, stdin, stdout, stderr):
        self.old_stdin = sys.stdin.buffer._the_tld
        self.old_stdout = sys.stdout.buffer._the_tld
        self.old_stderr = sys.stderr.buffer._the_tld
        self.new_stdin = stdin
        self.new_stdout = stdout
        self.new_stderr = stderr
    def __enter__(self):
        sys.stdin.buffer._tld.value = self.new_stdin
        sys.stdout.buffer._tld.value = self.new_stdout
        sys.stderr.buffer._tld.value = self.new_stderr
    def __exit__(self, *args):
        sys.stdin.flush()
        sys.stdout.flush()
        sys.stderr.flush()
        sys.stdin.buffer._tld.value = self.old_stdin
        sys.stdout.buffer._tld.value = self.old_stdout
        sys.stderr.buffer._tld.value = self.old_stderr

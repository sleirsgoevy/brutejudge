import time, threading, sys, io
from brutejudge.hook_stdio import RedirectSTDIO

class Watch(threading.Thread):
    def __init__(self, bj, interval, cmd):
        self.bj = bj
        self.interval = interval
        self.cmd = cmd
        self.running = True
        self.prev_out = self.exec()
        threading.Thread(target=self.run).start()
    def exec(self):
        stdin = io.BytesIO()
        stdout = io.BytesIO()
        with RedirectSTDIO(stdin, stdout, stdout):
            self.bj.onecmd(self.cmd)
        return stdout.getvalue().decode('utf-8', 'replace')
    def run(self):
        while True:
            time.sleep(self.interval)
            if not self.running: break
            cur = self.exec()
            if cur != self.prev_out:
                print('Note: `'+self.cmd+'` changed!')
                if cur.startswith(self.prev_out):
                    print('(append)')
                    print(cur[len(self.prev_out):])
                else:
                    print('<<<<<<< Was')
                    print(self.prev_out)
                    print('=======')
                    print(cur)
                    print('<<<<<<< Now')
                self.prev_out = cur

def do_watch(self, args):
    """
    usage: watch [options] [command]

        watch [-l <interval>] <command>
            Run <command> each <interval> (default=10) seconds and notify if the output changes.

        watch -d <watchno>
            Delete (cancel) watchpoint <watchno>. You will no longer receive notifications for that watchpoint.
    """
    if not hasattr(self, 'watches'):
        self.watches = {}
        self.watchno = 1
    if args.startswith('-d '):
        sp = args.split(' ')
        if len(sp) != 2 or not sp[1].isnumeric():
            return self.do_help('watch')
        idx = int(sp[1])
        if idx not in self.watches:
            print('No such watch:', idx)
        self.watches[idx].running = False
        del self.watches[idx]
    else:
        l = 10
        if args.startswith('-l '):
            sp = args.split(' ', 2)
            if len(sp) < 3 or not sp[1].isnumeric():
                return self.do_help('watch')
            l = int(sp[1])
            args = sp[2]
        args = args.strip()
        if args == '' or args.startswith('-'):
            return self.do_help('watch')
        self.watches[self.watchno] = Watch(self, l, args)
        print('Watch %d: %s'%(self.watchno, args))
        self.watchno += 1

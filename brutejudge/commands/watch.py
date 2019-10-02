import time, threading

class Watch:
    def __init__(self, bj, interval, cmd):
        self.bj = bj
        self.interval = interval
        self.cmd = cmd
        threading.Thread(target=self.run).start()

def do_watch(self, args):
    pass

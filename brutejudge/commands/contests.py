import brutejudge.cheats
from brutejudge.http import contest_name
from concurrent.futures import ThreadPoolExecutor

def do_contests(self, cmd):
    """
    usage: contests [-threads <thread_num>] <url>

    Get all contest names from login page <url>.
    `thread_num` defaults to 16.
    """
    brutejudge.cheats.cheating(self)
    if not cmd or cmd.isspace():
        return self.do_help('contests')
    cmd = cmd.split(' ')
    thread_num = 16
    if cmd[0] == '-threads':
        thread_num = int(cmd[1])
        del cmd[:2]
    cmd = ' '.join(cmd)
    x = cmd.split('contest_id=', 1)
    url = x[0]+'contest_id=%d'+'&'.join(['']+x[1].split('&', 1)[1:])
    def try_one(idx):
        name = contest_name(url % idx)
        if name != None: return '%s\t%s'%(idx, name)
    tpe = ThreadPoolExecutor(thread_num)
    try:
        i = 1
        while True:
            i2 = i + thread_num
            for i in tpe.map(try_one, range(i, i2)):
                if i != None: print(i)
            i = i2
    except KeyboardInterrupt: pass

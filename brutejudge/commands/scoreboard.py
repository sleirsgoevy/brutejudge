from brutejudge.http import task_list, scoreboard
from brutejudge.error import BruteError

def do_scoreboard(self, cmd):
    """
    usage: scoreboard

    Show current standings.
    """
    cmd = cmd.strip()
    if cmd:
        return self.do_help('scoreboard')
    tasks = task_list(self.url, self.cookie)
    scb = scoreboard(self.url, self.cookie)
    table = [['']+tasks]
    for u, i in scb:
        table.append([u]+['' if j == None else '%d (%s)'%(j[0], '+' if j[1] == 0 else '+%d'%j[1] if j[1] >= 0 else str(j[1])) for j in i])
    clens = [max(len(j[i]) for j in table) for i in range(len(tasks)+1)]
    fmt_s = ' '.join('%%%ds'%i for i in clens)
    for i in table: print(fmt_s % tuple(i))

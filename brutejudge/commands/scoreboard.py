from brutejudge.http import task_list, scoreboard
from brutejudge.error import BruteError

def format_single(data):
    score = data.get('score', None)
    attempts = data.get('attempts', None)
    ans = []
    if score != None: ans.append(str(score))
    if attempts != None and attempts * 0 == 0:
        if attempts == 0: ans.append('+')
        elif attempts > 0: ans.append('+'+str(attempts))
        else: ans.append(str(attempts))
    return ('', '%s', '%s (%s)')[len(ans)] % tuple(ans)

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
        table.append([u.get('name', '')]+['' if j == None else format_single(j) for j in i])
    if table:
        clens = [max(len(j[i]) for j in table) for i in range(len(tasks)+1)]
        fmt_s = ' '.join('%%%ds'%i for i in clens)
        for i in table: print(fmt_s % tuple(i))

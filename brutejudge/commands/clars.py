import shlex
from brutejudge.http import tasks, clar_list, submit_clar, read_clar

def do_clars(self, cmd):
    """
    usage: clars <command> [args...]

    `command` can be one of:
        list
        List clars.

        send <task> <subject>
        Send clar from stdin.

        read <clar_id>
        Read clar.
    """
    cmd = shlex.split(cmd)
    if not cmd: cmd = ['list']
    if cmd[0] not in ('list', 'send', 'read'):
        return self.do_help('clars')
    elif cmd[0] == 'list':
        if len(cmd) != 1: return self.do_help('clars')
        print('Clar ID\tSubject')
        for k, v in clar_list(self.url, self.cookie):
            print('%d\t%s'%(k, v))
    elif cmd[0] == 'read':
        if len(cmd) != 2 or not cmd[1].strip().isnumeric(): return self.do_help('clars')
        print(read_clar(self.url, self.cookie, int(cmd[1])))
    elif cmd[0] == 'send':
        if len(cmd) != 3: return self.do_help('clars')
        try: task = next(i.id for i in tasks(self.url, self.cookie) if i.short_name == cmd[1])
        except StopIteration:
            raise BruteError("No such task")
        data = ''
        while not data.endswith('\n\n'):
            try: data += input()+'\n'
            except EOFError: break
        submit_clar(self.url, self.cookie, task, cmd[2], data.strip())

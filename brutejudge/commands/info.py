import html
from brutejudge.http import tasks, problem_info, contest_info
from brutejudge.error import BruteError

def split_tex(data):
    i = 0
    while True:
        j = data.find('$', i)
        if j < 0:
            yield ('normal', data[i:])
            return
        elif j and data[j-1] == '\\':
            yield ('normal', data[i:j-1]+'$')
            i = j + 1
        else:
            yield ('normal', data[i:j])
            i = j
            while j < len(data) and data[j] == '$':
                j += 1
            if j == len(data):
                yield ('normal', data[i:j])
                return
            ss = data[i:j]
            i = j
            j = data.find(ss, i)
            if j < 0:
                yield ('normal', ss+data[i:])
                return
            elif max(map(ord, data[i:j])) >= 128:
                yield ('normal', ss+data[i:j]+ss)
                i = j + len(ss)
            else:
                yield ('tex', data[i:j])
                i = j + len(ss)

def brmap(s):
    it = iter(enumerate(s))
    stack = []
    mapp = {}
    for i, c in it:
        if c == '\\':
            next(it)
        elif c == '{':
            stack.append(i)
        elif c == '}' and stack:
            j = stack.pop()
            mapp[i] = j
            mapp[j] = i
    return mapp

def match(s, bm, i, what):
    i0 = i
    ans = []
    j = 0
    while j < len(what) and i < len(s):
        if what[j] == ' ':
            while i < len(s) and s[i].isspace():
                i += 1
        elif what[j:j+2] == '\\ ':
            if s[i] != ' ':
                return None, i0
            i += 1
            j += 1
        elif what[j] == '{':
            if s[i] != '{' or i not in bm:
                ans.append(s[i])
                i += 1
            else:
                jj = bm[i]
                ans.append(s[i+1:jj])
                i = jj + 1
        else:
            if s[i] != what[j]:
                return None, i0
            i += 1
        j += 1
    if j < len(what):
        return None, i0
    return ans, i

backslashes = {k: chr(v) for k, v in html.entities.name2codepoint.items()}
backslashes['ldots'] = backslashes['hellip']
backslashes['cdot'] = backslashes['middot']
backslashes['rightarrow'] = '\u2192'
backslashes['bmod'] = ' mod '
backslashes['operatorname'] = ''

def fn_underline(s, bm, i):
    q, i = peek(s, bm, i)
    ch = '\u0332'
    return ch + ch.join(q), i
backslashes['underline'] = fn_underline

def fn_limits(s, bm, i):
    q, i = match(s, bm, i, '_{^{')
    if q is None:
        return '', i
    return '[from ' + untex_expr(q[0]) + ' to ' + untex_expr(q[1]) + ']', i
backslashes['limits'] = fn_limits

def peek(s, bm, i):
    if s[i] == '{' and i in bm:
        return s[i+1:bm[i]], bm[i]+1
    return s[i], i+1

def untex_expr(s):
    bm = brmap(s)
    ans = ''
    i = 0
    while i < len(s):
        if s[i] == '\\':
            if i + 1 >= len(s):
                break
            elif not s[i + 1].isalnum():
                ans += s[i + 1]
                i += 2
                continue
            else:
                j = i + 1
                while j < len(s) and s[j].isalnum():
                    j += 1
                cmd = s[i+1:j]
                i = j
                if cmd in backslashes:
                    if isinstance(backslashes[cmd], str):
                        ans += backslashes[cmd]
                    else:
                        q, i = backslashes[cmd](s, bm, i)
                        ans += q
                else:
                    ans += '\\' + cmd
        elif s[i] == '_' and i + 1 < len(s):
            ss, i = peek(s, bm, i + 1)
            ans += '[' + untex_expr(ss) + ']'
        elif s[i] == '{' or s[i] == '}':
            i += 1
            continue
        else:
            ans += s[i]
            i += 1
    return ans

def untex(s):
    ans = ''
    for kind, i in split_tex(s):
        if kind == 'normal':
            ans += i
        elif kind == 'tex':
            ans += ' '.join(untex_expr(i).split())
    return ans

def do_info(self, cmd):
    """
    usage: info [-t] [task]

    Show testing information and problem statement for a task, or for the whole contest if task is not specified.
    If -t is specified, attempt to decode embedded TeX expressions into human-readable form.
    """
    cmd = cmd.strip()
    tex = False
    if cmd[:2] == '-t' and (len(cmd) == 2 or cmd[2:3].isspace()):
        tex = True
        cmd = cmd[2:].strip()
    if cmd == '--help':
        return self.do_help('info')
    if cmd:
        try: task_id = next(i.id for i in tasks(self.url, self.cookie) if i.short_name == cmd)
        except StopIteration:
            raise BruteError("No such task.")
        a, b = problem_info(self.url, self.cookie, task_id)
    else:
        b, a, j = contest_info(self.url, self.cookie)
        print(j)
    for k, v in a.items(): print(k+': '+v)
    print()
    print(untex(b) if tex else b)

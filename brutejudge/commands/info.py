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
        else:
            if j and data[j-1] == '\\':
                k = j
                while k and data[k-1] == '\\':
                    k -= 1
                if (j - k) % 2:
                    yield data[:k] + '\\'*((j - k)//2) + '$'
                    i = j + 1
                    continue
            yield ('normal', data[i:j])
            i = j
            while j < len(data) and data[j] == '$':
                j += 1
            if j == len(data):
                yield ('normal', data[i:j])
                return
            ss = j-i
            i = j
            brlevel = 0
            ss1 = 0
            while j < len(data) and (brlevel or ss1 < ss):
                if data[j] == '\\':
                    ss1 = 0
                    j += 2
                    continue
                elif data[j] == '$':
                    ss1 += 1
                    j += 1
                else:
                    ss1 = 0
                    if data[j] == '{':
                        brlevel += 1
                    elif data[j] == '}':
                        brlevel -= 1
                    j += 1
            if brlevel or ss1 < ss:
                yield ('normal', '$'*ss+data[i:])
                return
            elif max(map(ord, data[i:j])) >= 128:
                yield ('normal', '$'*ss+data[i:j])
                i = j
            else:
                yield ('tex', data[i:j-ss])
                i = j

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

def peek(s, bm, i):
    if s[i] == '{' and i in bm:
        return s[i+1:bm[i]], bm[i]+1
    return s[i], i+1

backslashes = {k: chr(v) for k, v in html.entities.name2codepoint.items()}
backslashes['dots'] = '...'
backslashes['ldots'] = '...'
backslashes['cdot'] = backslashes['middot']
backslashes['rightarrow'] = '\u2192'
backslashes['bmod'] = ' mod '
backslashes['operatorname'] = ''
backslashes['geq'] = backslashes['ge']
backslashes['leq'] = backslashes['le']
backslashes['neq'] = backslashes['ne']
backslashes['nless'] = '\u226e'
backslashes['ngtr'] = '\u226f'
backslashes['nleq'] = '\u2270'
backslashes['ngeq'] = '\u2271'

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

def fn_text(s, bm, i):
    s, i = peek(s, bm, i)
    return untex(s), i
backslashes['text'] = fn_text
backslashes['mathrm'] = peek

def fn_xrightarrow(s, bm, i):
    args = []
    if s[i] == '[':
        j = s.find(']', i+1)
        if j >= 0:
            args.append(untex_expr(s[i+1:j]))
            i = j + 1
    ss, i = peek(s, bm, i)
    args.append(untex_expr(ss))
    return '\u2192 ['+', '.join(args)+']', i
backslashes['xrightarrow'] = fn_xrightarrow

def fn_frac(s, bm, i):
    q, i = match(s, bm, i, '{{')
    if q is None:
        return '', i
    return '('+untex_expr(q[0])+')/('+untex_expr(q[1])+')', i
backslashes['frac'] = fn_frac
backslashes['dfrac'] = fn_frac

def fn_not(s, bm, i):
    q, i = match(s, bm, i, '{')
    if q is None:
        return chr(824), i
    return chr(824)+untex_expr(q[0]).lstrip(), i
backslashes['not'] = fn_not

def fn_pmod(s, bm, i):
    q, i = match(s, bm, i, '{')
    if q is None:
        return '(mod)', i
    return '(mod '+untex_expr(q[0])+')', i
backslashes['pmod'] = fn_pmod
backslashes['enspace'] = '  '

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

import sys, os.path

def read_file(name, options=set(), includes=None):
    name = os.path.realpath(name)
    if includes == None:
        includes = set()
    if name in includes: return ''
    includes.add(name)
    with open(name) as file:
        lines = file.read().split('\n')
    if '+include' in options:
        for i in range(len(lines)):
            l = lines[i]
            if l.startswith('#include "'):
                p2 = os.path.join(os.path.split(name)[0], eval(l[9:]))
                lines[i] = read_file(p2, includes=includes)+'\n'
    ans = '\n'.join(lines)
    ans2 = ''
    c = 0
    for i in ans:
        if i == '\n':
            c += 1
            if c >= 3: continue
        else:
            c = 0
        ans2 += i
    includes.remove(name)
    return ans2

def escape_strings(s):
    instr = None
    ans = ''
    for c in s:
        if instr == None:
            ans += c
            if c in ('"', "'"):
                instr = c
        elif instr.endswith('\\'):
            ans += '\\x%02x'%ord(c)
            instr = instr[:1]
        elif c == '\\':
            ans += '\\x%02x'%ord(c)
            instr += '\\'
        elif instr == c:
            instr = None
            ans += c
        else:
            ans += '\\x%02x'%ord(c)
    return ans

def unescape_strings(s):
    ans = ''
    i = 0
    while i < len(s):
        i1 = s.find('"', i)
        i2 = s.find("'", i)
        if i1 < 0: i1 = i2
        if i2 < 0: i2 = i1
        if i1 < 0:
            ans += s[i:]
            break
        j = min(i1, i2)
        ans += s[i:j]
        c = s[j]
        i = s.find(c, j+1)
        chars = ''.join(chr(int(i, 16)) for i in s[j+1:i].split('\\x')[1:])
        ans += c + chars + c
        i += 1
    return ans

def format(original, options=set(), cplusplus=True):
    original = escape_strings(original)
    i = 0
    s = [i.rstrip() for i in original.split('\n')]
    while i < len(s):
        if s[i] == '#pragma cut before':
            del s[:i+1]
            i = 0
            continue
        if s[i] in ('#pragma cut', '#pragma cut after'):
            del s[i:]
            break
        i += 1
    for i, j in enumerate(s):
        stripped = j.strip()
        if cplusplus and '+mods' in options and stripped in ('public:', 'private:', 'protected:'):
            l = j.find(stripped)
            while l % 4 != 1:
                l += 1
            s[i] = ' ' * l + stripped
        if (not cplusplus and '+funcvoid' in options) and j == stripped and j.endswith('()'):
            s[i] = j[:-2]+'(void)'
        if '+cexpr' in options and j.startswith('#pragma cexpr '):
            from .format_cexpr import format as format_cexpr
            s[i] = escape_strings(format_cexpr(unescape_strings(j[14:]), options, stdio=False).strip())
    s = [i.rstrip() for i in '\n'.join(s).split('\n')]
    i = 0
    while i < len(s):
        j = s[i]
        stripped = j.strip()
        if stripped != '{' and i and (s[i-1].endswith(')') or s[i-1].endswith('else') and not s[i-1][-5:-4].isalnum() and s[i-1][-5:-4] != '_') and ('+forcebraces' in options or s[i-1].strip() == '} else'):
            indent = s[i-1][:s[i-1].find(s[i-1].strip())]
            s.insert(i, indent+'{')
            ii = i + 1
            while ii < len(s) and s[ii].startswith(indent) and not s[ii][len(indent):len(indent)+1].strip():
                ii += 1
            s.insert(ii, indent+'}')
            continue
        if '+braces' in options:
            if stripped == '{' and i and not s[i-1].endswith('{'):
                s[i-1] += ' {'
                if s[i-1].strip() == 'else {':
                    s[i-1] = s[i-1].replace('else', '} else')
                    indent = s[i-1][:s[i-1].find(s[i-1].strip())]
                    ii = i - 2
                    while ii >= 0 and s[ii].startswith(indent) and not s[ii][len(indent):len(indent)+1].strip():
                        ii -= 1
                    if not ii:
                        s.insert(0, indent+'{')
                    else:
                        s[ii] += ' {'
                del s[i]
                continue
            elif stripped == 'else' and i and s[i-1].endswith('}'):
                s[i-1] += ' ' + stripped
                del s[i]
                continue
        i += 1
    s = '\n'.join(s)
    while ' \n' in s: s = s.replace(' \n', '\n')
    if '+ifspc' in options:
        i = 0
        while i < len(s):
            for j in ('if', 'while', 'for', 'switch'):
                if s[i:i+len(j)+1] == j + '(' and (not i or not s[i-1].isalnum() and s[i-1] != '_'):
                    s = s[:i+len(j)] + ' ' + s[i+len(j):]
                    break
            else: i += 1
    if '+pointers' in options:
        last_not_star = -1
        i = 0
        while i < len(s):
            if s[i] != '*':
                if last_not_star >= 0 and i - last_not_star > 1:
                    if not s[last_not_star].isspace() and s[i].isspace():
                        s = s[:last_not_star+1] + s[i] + s[last_not_star+1:i] + s[i+1:]
                    else:
                        last_not_star = i
                else:
                    last_not_star = i
            i += 1
    if '+funcgrep' in options:
        s = [i.rstrip() for i in s.split('\n')]
        for i, j in enumerate(s):
            if j[:1].isspace() or j.startswith('typedef') and not j[7:8].isalnum() and j[7:8] != '_':
                continue
            j = j.split('(')
            for k in range(1, len(j)):
                if j[k-1][-1:].isalnum() or j[k-1][-1:] == '_':
                    jj = len(j[k-1]) - 1
                    while jj >= 0 and (j[k-1][jj].isalnum() or j[k-1][jj] == '_'):
                        jj -= 1
                    jj += 1
                    if jj >= 0 and (jj > 0 or k == 1):
                        j[k-1] = j[k-1][:jj].rstrip() + '\n' + j[k-1][jj:]
            s[i] = '('.join(j)
        s = '\n'.join(s)
    return unescape_strings(s)

import sys, os.path

def read_file(name, options=set(), includes=None):
    name = os.path.realpath(name)
    if includes == None:
        includes = set()
    if name in includes: return ''
    includes.add(name)
    with open(name) as file:
        lines = file.read().split('\n')
    if '-include' not in options:
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

def format(original, options=set(), cplusplus=True):
    i = 0
    s = [i.rstrip() for i in original.split('\n')]
    for i, j in enumerate(s):
        stripped = j.strip()
        if cplusplus and '-mods' not in options and stripped in ('public:', 'private:', 'protected:'):
            l = j.find(stripped)
            while l % 4 != 1:
                l += 1
            s[i] = ' ' * l + stripped
        if (not cplusplus and '-funcvoid' not in options) and j == stripped and j.endswith('()'):
            s[i] = j[:-2]+'(void)'
        if '+cexpr' in options and j.startswith('#pragma cexpr '):
            from .format_cexpr import format as format_cexpr
            s[i] = format_cexpr(j[14:], options, stdio=False).strip()
    s = '\n'.join(s)
    while ' \n' in s: s = s.replace(' \n', '\n')
    i = 0
    if '-ifspc' not in options:
        while i < len(s):
            for j in ('if', 'while', 'for', 'switch'):
                if s[i:i+len(j)+1] == j + '(':
                    s = s[:i+len(j)] + ' ' + s[i+len(j):]
                    break
            else: i += 1
    return s

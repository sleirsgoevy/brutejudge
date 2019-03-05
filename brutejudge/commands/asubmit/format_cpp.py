import sys, os.path

def read_file(name, includes=None):
    name = os.path.realpath(name)
    if includes == None:
        includes = set()
    if name in includes: return ''
    includes.add(name)
    with open(name) as file:
        lines = file.read().split('\n')
    for i in range(len(lines)):
        l = lines[i]
        if l.startswith('#include "'):
            p2 = os.path.join(os.path.split(name)[0], eval(l[9:]))
            lines[i] = read_file(p2, includes)+'\n'
    ans = '\n'.join(lines)
    while '\n\n\n' in ans:
        ans = ans.replace('\n\n\n', '\n\n')
    includes.remove(name)
    return ans

def format(original):
    i = 0
    s = original.replace('; ', ';').replace(';', '; ').replace("'; '", "';'").split('\n')
    for i, j in enumerate(s):
        stripped = j.strip()
        if stripped in ('public:', 'private:', 'protected:'):
            l = j.find(stripped)
            while l % 4 != 1:
                l += 1
            s[i] = ' ' * l + stripped
    s = '\n'.join(s)
    while ' \n' in s: s = s.replace(' \n', '\n')
    i = 0
    while i < len(s):
        for j in ('if', 'while', 'for', 'switch'):
            if s[i:i+len(j)+1] == j + '(':
                s = s[:i+len(j)] + ' ' + s[i+len(j):]
                break
        else: i += 1
    return s

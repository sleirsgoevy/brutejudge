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
            if l.startswith('%include "') and l != '%include "io.inc"':
                p2 = os.path.join(os.path.split(name)[0], eval(l[9:]))
                lines[i] = read_file(p2, includes=includes)
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

def format(original, options=set()):
    if '-indent' in options: return original
    lines = [i.strip() for i in original.split('\n')]
    i = 0
    j = 0
    whole_comment = True
    have_label = False
    while j < len(lines):
        if lines[j] == '':
            if not whole_comment:
                for i in range(i, j):
                    is_label = lines[i].split(';', 1)[0].strip().endswith(':')
                    is_directive = lines[i].split()[0] in ('global', 'section')
                    if is_label: have_label = True
                    if have_label and not (is_label or is_directive):
                        lines[i] = '    ' + lines[i]
            while j < len(lines) and lines[j] == '': j += 1
            i = j
            whole_comment = True
            continue
        if not lines[j].startswith(';'): whole_comment = False
        j += 1
    return '\n'.join(lines)

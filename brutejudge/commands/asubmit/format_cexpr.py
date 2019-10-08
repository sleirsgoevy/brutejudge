def check_exists(file):
    return True

def read_file(name):
    return name

def get_fmt_name(s):
    s = s.split()
    for i in s:
        if i.startswith('__%'):
            return '%'+i[3:]
    spec = 'd'
    if 'unsigned' in s: spec = 'u'
    if 'char' in s: spec = 'c'
    if 'float' in s: spec = 'f'
    if 'double' in s: spec = 'lf'
    if '__char' in s: spec = 'c'
    if '__int' in s: spec = 'd'
    if '__unsigned' in s: spec = 'u'
    if '__hex' in s: spec = 'x'
    mod = ''
    if 'char' in s and spec != 'c': mod = 'hh'
    else: mod += 'h'*s.count('short')+'l'*s.count('long')
    return '%'+mod+spec

def get_spec_name(s):
    return ' '.join(i for i in s.split() if i not in ('__char', '__int', '__unsigned', '__hex') and not i.startswith('__%'))

def format(s):
    args, exprs = s.split(':', 1)
    args, retvals = args.rsplit('->', 1)
    args = [i.strip() for i in args.split(',')]
    retvals = [i.strip() for i in retvals.split(',')]
    exprs = exprs.strip()
    code = '''\
#include <stdio.h>

int main(void)
{
'''
    for i in args:
        code += '    '+get_spec_name(i.rsplit(' ', 1)[0])+' '+i.rsplit(' ', 1)[1]+';\n'
    code += '    scanf("'
    for i in args:
        code += get_fmt_name(i.rsplit(' ', 1)[0])
    code += '"'
    for i in args:
        code += ', &'+i.rsplit(' ', 1)[1]
    code += ');\n'
    code += '    printf("'
    b = False
    for i in retvals:
        if b: code += ' '
        else: b = True
        code += get_fmt_name(i)
    code += '\\n", '+exprs+');\n'
    code += '''\
    return 0;
}
'''
    return code

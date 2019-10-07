def check_exists(file):
    return True

def read_file(name):
    return name

def get_fmt_name(s):
    s = s.split()
    spec = 'd'
    if 'unsigned' in s: spec = 'u'
    if 'char' in s: spec = 'c'
    if '__char' in s: spec = 'c'
    if '__int' in s: spec = 'd'
    if '__unsigned' in s: spec = 'u'
    if '__hex' in s: spec = 'x'
    mod = ''
    if 'char' in s and spec != 'c': mod = 'hh'
    else: mod += 'h'*s.count('short')+'l'*s.count('long')
    return '%'+mod+spec

def get_spec_name(s):
    return ' '.join(i for i in s.split() if i not in ('__char', '__int', '__unsigned', '__hex'))

def format(s):
    args, expr = s.split(':', 1)
    args, retval = args.rsplit('->', 1)
    args = [i.strip() for i in args.split(',')]
    retval = retval.strip()
    expr = expr.strip()
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
    code += get_fmt_name(retval)
    code += '", '+expr+');\n'
    code += '''\
    return 0;
}
'''
    return code

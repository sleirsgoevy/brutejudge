from brutejudge.http import backend_path
from inspect import getsource
from functools import lru_cache

def get_methods(cls):
    return set(i for i in cls.__dict__ if i[:1] != '_')

@lru_cache(None)
def check_method_status(cls, m_s):
    try: m = getattr(cls, m_s)
    except AttributeError: return 'missing'
    try: src = getsource(m)
    except OSError: pass
    else:
        src = src.split(':', 1)[1].strip()
        if src.startswith('raise') and not (src[5].isalnum() or src[5] == '_') or '#STUB' in src:
            return 'stub'
    if m_s not in cls.__dict__: return 'inherit'
    return 'OK'

methods = set()

for i in backend_path: methods |= get_methods(i)

methods = list(methods)
methods.sort()

column_width = [max(map(len, methods))]
for i in backend_path: column_width.append(max(len(i.__name__), max(len(check_method_status(i, m)) for m in methods)))

def print_column(args):
    s = ''
    for i, t in enumerate(args):
        t = str(t)
        t += ' ' * (column_width[i] - len(t))
        s += t + ' '
    print(s[:-1])

print_column(['']+[i.__name__ for i in backend_path])
for m in methods:
    print_column([m]+[check_method_status(i, m) for i in backend_path])

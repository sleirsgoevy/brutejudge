import collections

task_t = collections.namedtuple('task_t', ('id', 'short_name', 'long_name'))
submission_t = collections.namedtuple('submission_t', ('id', 'task', 'status', 'score', 'oktests'))
test_t = collections.namedtuple('test_t', ('status', 'stats'))
compiler_t = collections.namedtuple('compiler_t', ('id', 'short_name', 'long_name'))
clar_t = collections.namedtuple('clar_t', ('id', 'subject'))


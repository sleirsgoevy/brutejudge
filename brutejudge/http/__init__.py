import brutejudge._http.ejudge, brutejudge._http.ejudge.ejfuse, brutejudge._http.pcms, brutejudge._http.jjs, brutejudge._http.informatics, brutejudge._http.informatics_new, brutejudge._http.codeforces, brutejudge._http.gcj, urllib.request
from brutejudge._http.ejudge import contest_name
from brutejudge.error import BruteError

backend_path = [brutejudge._http.ejudge.ejfuse.EJFuse, brutejudge._http.jjs.JJS, brutejudge._http.informatics.Informatics, brutejudge._http.informatics_new.Informatics, brutejudge._http.codeforces.CodeForces, brutejudge._http.gcj.GCJ, brutejudge._http.pcms.PCMS, brutejudge._http.ejudge.Ejudge]

def login(url, login, password):
    for i in backend_path:
        try: f = i.detect(url)
        except Exception: f = False
        if f:
            return (i(url, login, password), True)
    raise BruteError("Unknown CMS")

def login_type(url):
    for i in backend_path:
        try: f = i.detect(url)
        except Exception: pass
        if f: return i.login_type(url)
    return []

def _create_wrapper(name):
    def func(*args, **kwds):
        return getattr(args[0], name)(*args[2:], **kwds)
    globals()[name] = func

for _w in ['task_list', 'submission_list', 'submission_results', 'task_ids', 'submit', 'status', 'scores', 'compile_error', 'submission_status', 'submission_source', 'do_action', 'compiler_list', 'submission_stats', 'problem_info', 'download_file', 'submission_score', 'clars', 'submit_clar', 'read_clar', 'get_samples', 'may_cache', 'scoreboard']:
    _create_wrapper(_w)

del _create_wrapper, _w

def has_feature(url, cookie, methodname, argname):
    if not hasattr(url, methodname): return False
    m = getattr(url, methodname).__func__.__code__
    return argname in m.co_varnames[:m.co_argcount+m.co_kwonlyargcount]

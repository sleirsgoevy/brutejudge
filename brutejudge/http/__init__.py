import brutejudge._http.ejudge, brutejudge._http.ejudge.ejfuse, brutejudge._http.pcms, brutejudge._http.jjs, brutejudge._http.informatics, brutejudge._http.codeforces, brutejudge._http.gcj, brutejudge._http.cache, brutejudge._http.file, brutejudge._http.yacontest, brutejudge._http.cupsonline, brutejudge._http.ejudge.infopen, brutejudge._http.atcoder, urllib.request
from brutejudge._http.ejudge import contest_name
from brutejudge.error import BruteError
from brutejudge._http.types import *

backend_path = [brutejudge._http.cache.AggressiveCacheBackend, brutejudge._http.file.FileBackend, brutejudge._http.ejudge.ejfuse.EJFuse, brutejudge._http.jjs.JJS, brutejudge._http.informatics.Informatics, brutejudge._http.codeforces.CodeForces, brutejudge._http.gcj.GCJ, brutejudge._http.cupsonline.CupsOnline, brutejudge._http.yacontest.YaContest, brutejudge._http.ejudge.infopen.InfOpen, brutejudge._http.atcoder.AtCoder, brutejudge._http.pcms.PCMS, brutejudge._http.ejudge.Ejudge]

def login(url, login, password, **kwds):
    for i in backend_path:
        try: f = i.detect(url)
        except Exception: f = False
        if f:
            return (i(url, login, password, **kwds), True)
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

for _w in ['tasks', 'submissions', 'submission_protocol', 'task_ids', 'submit_solution', 'status', 'scores', 'compile_error', 'submission_source', 'do_action', 'compiler_list', 'submission_stats', 'contest_info', 'problem_info', 'download_file', 'clar_list', 'submit_clar', 'read_clar', 'get_samples', 'may_cache', 'scoreboard', 'change_password', 'locales', 'set_locale']:
    _create_wrapper(_w)

del _create_wrapper, _w

def has_feature(url, cookie, methodname, argname):
    if not hasattr(url, methodname): return False
    m = getattr(url, methodname).__func__.__code__
    return argname in m.co_varnames[:m.co_argcount+m.co_kwonlyargcount]

def contest_list(url, cookie):
    if cookie == None: # anonymous, url is string with url
        for i in backend_path:
            try: f = i.detect(url)
            except Exception: f = False
            if f:
                return i.contest_list(url)
        return []
    else: # non-anonymous, url is the backend object
        return url.contest_list()

def task_list(url, cookie):
    return [i[1] for i in tasks(url, cookie)]

def submission_list(url, cookie):
    sl = submissions(url, cookie)
    return [i[0] for i in sl], [i[1] for i in sl]

def submission_results(url, cookie, subm_id):
    sr = submission_protocol(url, cookie, subm_id)
    return [i[0] for i in sr], ['%0.3f'%i[1]['time_usage'] if 'time_usage' in i[1] else '?.???' for i in sr]

def task_ids(url, cookie):
    return [i[0] for i in tasks(url, cookie)]

def submit(url, cookie, task, lang, text):
    try: task = task_ids(url, cookie)[task]
    except IndexError: return
    submit_solution(url, cookie, task, lang, text)

def submission_status(url, cookie, subm_id):
    for i in submissions(url, cookie):
        if i[0] == subm_id: return i[2]
    return None

def submission_score(url, cookie, subm_id):
    for i in submissions(url, cookie):
        if i[0] == subm_id: return i[3]
    return None

def clars(url, cookie):
    c = clar_list(url, cookie)
    return [i[0] for i in c], [i[1] for i in c]

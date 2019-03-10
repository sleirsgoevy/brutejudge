import brutejudge.http.ejudge, brutejudge.http.pcms, brutejudge.http.jjs, brutejudge.http.informatics, brutejudge.http.codeforces, urllib.request
from brutejudge.http.ejudge import contest_name
from brutejudge.error import BruteError

backend_path = [jjs.JJS, informatics.Informatics, pcms.PCMS, codeforces.CodeForces, ejudge.Ejudge]

def login(url, login, password):
    for i in backend_path:
        try: f = i.detect(url)
        except Exception: f = False
        if f:
            return (i(url, login, password), True)
    raise BruteError("Unknown CMS")

def _create_wrapper(name):
    def func(*args, **kwds):
        return getattr(args[0], name)(*args[2:], **kwds)
    globals()[name] = func

for _w in ['task_list', 'submission_list', 'submission_results', 'task_ids', 'submit', 'status', 'scores', 'compile_error', 'submission_status', 'submission_source', 'do_action', 'compiler_list', 'submission_stats', 'problem_info', 'download_file', 'submission_score', 'clars', 'submit_clar', 'read_clar', 'get_samples']:
    _create_wrapper(_w)

del _create_wrapper, _w

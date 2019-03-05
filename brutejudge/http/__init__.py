import brutejudge.http.ejudge, brutejudge.http.pcms, urllib.request

def login(url, login, password):
    try:
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor)
        req = opener.open(url)
        data = req.read().decode('utf-8')
    except:
#       import traceback
#       traceback.print_exc()
        data = ''
#   print(req.getheaders(), data)
    if '<input type="hidden" name="javax.faces.ViewState" id="j_id1:javax.faces.ViewState:0" value="' in data:
        return (brutejudge.http.pcms.PCMS(url, login, password), True)
    return (brutejudge.http.ejudge.Ejudge(url, login, password), True)

def _create_wrapper(name):
    def func(*args, **kwds):
        return getattr(args[0], name)(*args[2:], **kwds)
    globals()[name] = func

for _w in ['task_list', 'submission_list', 'submission_results', 'task_ids', 'submit', 'status', 'scores', 'compile_error', 'submission_status', 'submission_source', 'do_action', 'compiler_list']:
    _create_wrapper(_w)

del _create_wrapper, _w

import urllib.request, urllib.parse, json, collections, html
from .ejudge import Ejudge
from .base import Backend
from .openerwr import OpenerWrapper
from ..error import BruteError
import brutejudge._http.html2md as html2md

SUBM_LIST_URL = "/py/problem/0/filter-runs?problem_id=0&from_timestamp=-1&to_timestamp=-1&group_id=0&user_id=%s&lang_id=-1&status_id=-1&statement_id=&count=%d&with_comment=&page=%d"

class Informatics(Ejudge):
    @staticmethod
    def detect(url):
        sp = url.split('/', 3)
        sp[2] = '.'.join(sp[2].split('.')[-3:])
        url = '/'.join(sp)
        for proto in ('http', 'https'):
            for domain in ('mccme', 'msk'):
                if (url+'/').startswith('%s://informatics.%s.ru/'%(proto, domain)):
                    for path in ('cgi-bin', 'ej'):
                        if (url+'/').startswith('%s://informatics.%s.ru/%s/'%(proto, domain, path)):
                            break
                    else:
                        return True
        return False
    def __init__(self, url, login, password):
        Backend.__init__(self)
        sp = url.split('/', 3)
        sp[2] = '.'.join(sp[2].split('.')[-3:])
        url = '/'.join(sp)
        for proto in ('http', 'https'):
            for domain in ('mccme', 'msk'):
                if (url+'/').startswith('%s://informatics.%s.ru/'%(proto, domain)):
                    for vt in (('', ''), ('', '3'), ('moodle/', ''), ('moodle/', '3')):
                        if url.startswith('%s://informatics.%s.ru/%smod/statements/view%s.php?'%((proto, domain)+vt)):
                            if not vt[1]:
                                url = url.replace('view', 'view3', 1)
                            if vt[0]:
                                url = url.replace('/moodle/', '/', 1)
                            break
                    else:
                        raise BruteError("URL must point to a contest or a task.")
                    if domain == 'mccme':
                        url = url.replace('mccme', 'msk', 1)
                    break
            else: continue
            break
        else:
            raise BruteError("Not an informatics.msk.ru URL")
        self.url = url
        self.opener = OpenerWrapper(urllib.request.build_opener(urllib.request.HTTPCookieProcessor))
        self.opener.open("https://informatics.msk.ru/")
        req = self.opener.open("https://informatics.msk.ru/login/index.php", urllib.parse.urlencode({
            'username': login,
            'password': password,
            'testcookies': 1
        }).encode('ascii'))
        if req.geturl() != 'https://informatics.msk.ru/':
            raise BruteError("Login failed.")
        self.registered = False
        data = self.opener.open(url).read().decode('utf-8', 'replace')
        query = dict(tuple(i.split('=', 1)) for i in url.split('#', 1)[0].split('?', 1)[1].split('&'))
        if 'id' in query and '<form action="view3.php?id='+query['id']+'&register=1" method="post">' in data:
            return
        self._init_full(data)
    def _init_full(self, data=None):
        if data == None:
            data = self.opener.open(url).read().decode('utf-8', 'replace')
        self.user_id = int(data.split('<div id="user_id" style="display: none">', 1)[1].split('</div>', 1)[0])
        query = dict(tuple(i.split('=', 1)) for i in self.url.split('#', 1)[0].split('?', 1)[1].split('&'))
        if 'id' in query:
            tasks = []
            cur_task = int(data.split('<div id="problem_id" style="display: none">', 1)[1].split('</div>', 1)[0])
            data = data.split('<div class="statements_toc_alpha"><font size="-1"><ul>', 1)[1].split('</ul>', 1)[0]
            for i in data.split('<li>')[1:]:
                i = i.split('</li>', 1)[0]
                if i.startswith('<a href="view3.php?'):
                    tasks.append(int(i.split('chapterid=', 1)[1].split('"', 1)[0].split('&', 1)[0]))
                else:
                    tasks.append(cur_task)
        else:
            tasks = [int(query['chapterid'])]
        self.tasks = tasks
        self.subm_list = []
        self.subm_list_partial = []
        self.subm_set = {}
        self._cache = {}
        self.registered = True
        self.submission_list()
    def _cache_get(self, url):
        with self.cache_lock:
            if url in self._cache: return self._cache[url]
        ans = self.opener.open("https://informatics.msk.ru"+url).read()
        with self.cache_lock:
            if self.caching: self._cache[url] = ans
        return ans
    def _request_json(self, url):
        return json.loads(self._cache_get(url).decode('utf-8', 'replace'))
    def task_list(self):
        if not self.registered: return []
        return list(map(str, self.tasks))
    def submission_list(self):
        if not self.registered: return [], []
        subms = []
        subms_partial = []
        page_cnt = self._request_json(SUBM_LIST_URL%(self.user_id, 100, 1))['metadata']['page_count']
        for i in range(page_cnt):
            data = self._request_json(SUBM_LIST_URL%(self.user_id, 100, i+1))
            if 'data' not in data: break #FIXME
            data = data['data']
            for i in data:
                task_id = i['problem']['id']
                si = i['id']
                if si in self.subm_set: break
                subms.append([si, task_id])
                if int(task_id) in self.tasks: subms_partial.append([si, task_id])
            else: continue
            break
        idx = -len(self.subm_list)-len(subms)
        for a, b in subms:
            self.subm_set[a] = idx
            idx += 1
        self.subm_list[:0] = subms
        self.subm_list_partial[:0] = subms_partial
        return ([i[0] for i in self.subm_list_partial], [str(i[1]) for i in self.subm_list_partial])
    def submission_results(self, id):
        data = self._request_json("/py/protocol/get/%d"%int(id)).get('tests', {})
        ans1 = []
        ans2 = []
        status_codes = dict(
            OK='OK',
            RT='Run-time error',
            TL='Time-limit exceeded',
            PE='Presentation error',
            WA='Wrong answer',
            CF='Check failed',
            ML='Memory limit exceeded',
            SE='Security violation',
            SV='Style violation',
            WT='Wall time limit exceeded',
            SK='Skipped'
        )
        for k in sorted(map(int, data)):
            ans1.append(status_codes[data[str(k)]['status']])
            ans2.append('%.3f'%(data[str(k)]['time']/1000))
        return ans1, ans2
    def task_ids(self):
        if not self.registered: return []
        return list(self.tasks)
    def submit(self, task, lang, text):
        if not self.registered: return
        if isinstance(text, str): text = text.encode('utf-8')
        try: task = self.task_ids()[task]#task += 1
        except IndexError: return
        data = []
        data.append(b'"lang_id"\r\n\r\n'+str(lang).encode('ascii'))
        data.append(b'"file"; filename="brute.txt"\r\nContent-Type'
                    b': text/plain\r\n\r\n'+text)
#       data.append(b'"action_40"\r\n\r\nSend!')
        import random
        while True:
            x = b'----------'+str(random.randrange(1, 1000000000)).encode('ascii')
            for i in data:
                if x in i: break
            else: break
    #   x = '-----------------------------850577185583170701784494929'
        data = b'\r\n'.join(b'--'+x+b'\r\nContent-Disposition: form-data; name='+i for i in data)+b'\r\n--'+x+b'--\r\n'
        self.opener.open(urllib.request.Request("https://informatics.msk.ru/py/problem/%d/submit"%task, data, {'Content-Type': 'multipart/form-data; boundary='+x.decode('ascii')}))
    def status(self):
        if not self.registered: return {}
        self.submission_list()
        by_task = {}
        for a, b in self.subm_list_partial:
            c = self._submission_status(a)
            if b not in by_task or by_task[b][1] < c[1]:
                by_task[b] = c
        return collections.OrderedDict((i, by_task.get(i, (None,))[0]) for i in self.task_list())
    def scores(self):
        if not self.registered: return {}
        self.submission_list()
        by_task = {}
        for a, b in self.subm_list_partial:
            d = self.submission_score(a)
            if d != None and (b not in by_task or by_task[b] < d):
                by_task[b] = d
        return collections.OrderedDict((i, by_task.get(i, None)) for i in self.task_list())
    def compile_error(self, id):
        data = self._request_json("/py/protocol/get/%d"%int(id))
        return data.get('compiler_output', data.get('protocol', '')) or None
    def _submission_object(self, id):
        id = int(id)
        if id not in self.subm_set: return None
        match = len(self.subm_list) + self.subm_set[id]
#       print(id, self.subm_list[match])
        ans = self._request_json(SUBM_LIST_URL%(self.user_id, 100, match // 100 + 1))['data'][match % 100]
#       print('submission_object', id, '=', ans)
        return ans
    def _submission_status(self, id):
        statuses = {
            0: ('OK', 2),
            98: ('Compiling...', -1),
            96: ('Running...', -1),
            1: ('Compilation error', 0),
            7: ('Partial solution', 1)
        }
        status = self._submission_object(id)['ejudge_status']
        return statuses.get(status, ('Unknown status #%d'%status, 0))
    def submission_status(self, id):
        return self._submission_status(id)[0]
    def submission_source(self, id):
        data = self._request_json("/py/problem/run/%d/source"%int(id))
        return data.get('data', {}).get('source', None).encode('utf-8')
    def do_action(self, action, *args):
        if action == 'start_virtual':
            if self.registered: return False
            data = self.opener.open(self.url).read().decode('utf-8', 'replace')
            query = dict(tuple(i.split('=', 1)) for i in self.url.split('#', 1)[0].split('?', 1)[1].split('&'))
            if 'id' not in query or '<form action="view3.php?id='+query['id']+'&register=1" method="post">' not in data:
                return False
            data = self.opener.open('https://informatics.msk.ru/mod/statements/view3.php?id='+query['id']+'&register=1', b'').read().decode('utf-8', 'replace')
            if '<script type="text/javascript">\n//<![CDATA[\n\n  function redirect() {\n      document.location.replace(\'view3.php?id='+query['id']+'\');\n  }\n  setTimeout("redirect()", 3000);\n//]]>\n</script>' not in data: return False
            self._init_full()
        raise BruteError("NYI")
    def compiler_list(self, prob_id):
        known_compilers = {1: 'fpc', 2: 'gcc', 3: 'g++', 22: 'php', 23: 'python', 24: 'perl', 25: 'mcs', 26: 'ruby', 27: 'python3'}
        data = self._cache_get("/mod/statements/view3.php?chapterid=%d"%prob_id).decode('utf-8', 'replace')
        ans = []
        for i in data.split('<select name="lang_id" id="lang_id" ', 1)[1].split('>', 1)[1].split('</select>', 1)[0].replace('<option value="', "<option value='").split("<option value='")[1:]:
            a = int(i.split("'", 1)[0].split('"', 1)[0])
            c = html.unescape(i.split('</option>', 1)[0].split('>', 1)[1])
            b = known_compilers.get(a, str(a))
            ans.append((a, b, c.strip()))
        return ans
    def submission_stats(self, id):
        data = self._request_json("/py/protocol/get/%d"%int(id))
        ans = {}
        score = self.submission_score(id)
        if score != None:
            ans['score'] = score
        if 'tests' in data:
            ans['tests'] = {}
            ans['tests']['total'] = len(data['tests'])
            ans['tests']['success'] = sum(1 for k, v in data['tests'].items() if v['status'] == 'OK')
            ans['tests']['fail'] = ans['tests']['total'] - ans['tests']['success']
        return (ans, None)
    def submission_score(self, id):
        data = self._submission_object(id)
        return data['ejudge_score'] if data['ejudge_score'] >= 0 else None
    def problem_info(self, id):
        url = "/mod/statements/view3.php?chapterid=%d"%id
        data = self._cache_get(url).decode('utf-8', 'replace')
        if '<div class="legend">' in data: the_html = data.split('<div class="legend">', 1)[1]
        elif '<div class="statements_content">' in data:
            the_html = data.split('<div class="statements_content">', 1)[1]
            the_html = the_html.split('<h1>', 2)
            the_html = '<h1>'+the_html[0]+the_html[2]
        else: return ({}, None)
        return ({}, html2md.html2md(the_html.split("<div id='submit' ", 1)[0], None, "https://informatics.msk.ru"+url))
    def download_file(self, prob_id, filename):
        raise BruteError("File download doesn't exist on informatics.msk.ru")
    def clars(self):
        raise BruteError("Clarifications don't exits on informatics.msk.ru")
    def submit_clar(self, *args):
        raise BruteError("Clarifications don't exits on informatics.msk.ru")
    def read_clar(self, id):
        raise BruteError("Clarifications don't exits on informatics.msk.ru")
    def get_samples(self, subm_id):
        raise BruteError("Can't get samples on informatics.msk.ru")
    def scoreboard(self):
        raise BruteError("Scoreboard is not supported on informatics.msk.ru")
    def stop_caching(self):
        self._cache.clear()    

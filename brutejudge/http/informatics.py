import urllib.request, urllib.parse, json, collections, html
from .ejudge import Ejudge
from .base import Backend
from .openerwr import OpenerWrapper
from ..error import BruteError

class Informatics(Ejudge):
    @staticmethod
    def detect(url):
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
        self.opener = OpenerWrapper(urllib.request.build_opener(urllib.request.HTTPCookieProcessor))
        self.opener.open("https://informatics.msk.ru/")
        req = self.opener.open("https://informatics.msk.ru/login/index.php", urllib.parse.urlencode({
            'username': login,
            'password': password,
            'testcookies': 1
        }).encode('ascii'))
        if req.geturl() != 'https://informatics.msk.ru/':
            raise BruteError("Login failed.")
        data = self.opener.open(url).read().decode('utf-8', 'replace')
        self.user_id = int(data.split('<div id="user_id" style="display: none">', 1)[1].split('</div>', 1)[0])
        query = dict(tuple(i.split('=', 1)) for i in url.split('#', 1)[0].split('?', 1)[1].split('&'))
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
        self.subm_set = set()
        self._cache = {}
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
        return list(map(str, self.tasks))
    def submission_list(self):
        statuses = {
            'OK': ('OK', 2),
            'Компилирование...': ('Compiling...', -1),
            'Тестирование...': ('Running...', -1),
            'Ошибка компиляции': ('Compilation error', 0),
            'Частичное решение': ('Partial solution', 1)
        }
        subms = []
        to_add = set()
        page_cnt = self._request_json("/moodle/ajax/ajax.php?problem_id=0&objectName=submits&group_id=0&user_id=%d&from_timestamp=-1&to_timestamp=-1&status_id=-1&lang_id=-1&count=20&with_comment=&statement_id=0&action=getPageCount"%self.user_id)['result']['page_count']
        for i in range(page_cnt):
            data = self._request_json("/moodle/ajax/ajax.php?problem_id=0&objectName=submits&group_id=0&user_id=%d&from_timestamp=-1&to_timestamp=-1&status_id=-1&lang_id=-1&count=20&with_comment=&statement_id=0&page=%d&action=getHTMLTable"%(self.user_id, i))['result']['text']
            for i in data.split('<tr>')[1:]:
                if '<td><a href="/moodle/mod/statements/view3.php?chapterid=' in i:
                    i = i.split('<td><a href="/moodle/mod/statements/view3.php?chapterid=', 1)[1]
                    task_id, other = i.split('&run_id=', 1)
                    si1, si2 = other.split('"', 1)[0].split('r')
                    si = int(si1) * 1000000 + int(si2)
                    if si in self.subm_set: break
                    score = i.split('<td><a onclick="', 1)[0].rsplit('</td>', 1)[0].rsplit('<td>', 1)[1]
                    score = None if not score else int(score)
                    status = i.split('<td><a onclick="', 1)[0].rsplit('</td>', 3)[0].rsplit('<td>', 1)[1].strip()
                    status = statuses.get(status, (status, 0))
                    if int(task_id) in self.tasks: subms.append([si, task_id, status, score])
                    if not status[0].endswith('...'):
                        to_add.add(si)
                    else:
                        to_add.clear()
            else: continue
            break
        self.subm_list[:0] = subms
        return ([i[0] for i in self.subm_list], [i[1] for i in self.subm_list])
    def submission_results(self, id):
        data = self._request_json("/py/protocol/get/%d/%d"%divmod(int(id), 1000000)).get('tests', {})
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
        return list(self.tasks)
    def submit(self, task, lang, text):
        if isinstance(text, str): text = text.encode('utf-8')
        try: task = self.task_ids()[task]#task += 1
        except IndexError: return
        data = []
        data.append(b'"lang_id"\r\n\r\n'+str(lang).encode('ascii'))
        data.append(b'"file"; filename="brute.txt"\r\nContent-Type'
                    b': text/plain\r\n\r\n'+text)
        data.append(b'"action_40"\r\n\r\nSend!')
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
        self.submission_list()
        by_task = {}
        for a, b, c, d in self.subm_list:
            if b not in by_task or by_task[b][1] < c[1]:
                by_task[b] = c
        return collections.OrderedDict((i, by_task.get(i, (None,))[0]) for i in self.task_list())
    def scores(self):
        self.submission_list()
        by_task = {}
        for a, b, c, d in self.subm_list:
            if d != None and (b not in by_task or by_task[b] < d):
                by_task[b] = d
        return collections.OrderedDict((i, by_task.get(i, None)) for i in self.task_list())
    def compile_error(self, id):
        data = self._request_json("/py/protocol/get/%d/%d"%divmod(int(id), 1000000))
        return data.get('compiler_output', data.get('protocol', '')) or None
    def submission_status(self, id):
        self.submission_list()
        try: return [c[0] for a, b, c, d in self.subm_list if a == id][0]
        except IndexError: return None
    def submission_source(self, id):
        req = self._cache_get("/moodle/ajax/ajax_file.php?objectName=source&contest_id=%d&run_id=%d"%divmod(int(id), 1000000)).decode('utf-8', 'replace')
        try: return html.unescape(req.split('<textarea ', 1)[1].split('>', 1)[1].split('</textarea>', 1)[0]).encode('utf-8')
        except IndexError: return None
    def do_action(self, *args):
        raise BruteError("NYI")
    def compiler_list(self, prob_id):
        known_compilers = {1: 'fpc', 2: 'gcc', 3: 'g++', 22: 'php', 23: 'python', 24: 'perl', 25: 'mcs', 26: 'ruby', 27: 'python3'}
        data = self._cache_get("/mod/statements/view3.php?chapterid=%d"%prob_id).decode('utf-8', 'replace')
        ans = []
        for i in data.split('<select name="lang_id" id="lang_id" ', 1)[1].split('>', 1)[1].split('</select>', 1)[0].split("<option value='")[1:]:
            a = int(i.split("'", 1)[0])
            c = html.unescape(i.split('</option>', 1)[0].split('>', 1)[1])
            b = known_compilers.get(a, str(a))
            ans.append((a, b, c.strip()))
        return ans
    def submission_stats(self, id):
        data = self._request_json("/py/protocol/get/%d/%d"%divmod(int(id), 1000000))
        ans = {}
        try:
            score = [d for a, b, c, d in self.subm_list if a == id][0]
        except IndexError: pass
        else:
            if score != None:
                ans['score'] = score
        if 'tests' in data:
            ans['tests'] = {}
            ans['tests']['total'] = len(data['tests'])
            ans['tests']['success'] = sum(1 for k, v in data['tests'].items() if v['status'] == 'OK')
            ans['tests']['fail'] = ans['tests']['total'] - ans['tests']['success']
        return (ans, None)
    def submission_score(self, id):
        self.submission_list()
        try: return [d for a, b, c, d in self.subm_list if a == id][0]
        except (ValueError, IndexError): return None
    def problem_info(self, id):
        data = urllib.request.urlopen("https://informatics.msk.ru/mod/statements/view3.php?chapterid=%d"%id).read().decode('utf-8', 'replace')
        if '<div class="legend">' not in data: return ({}, None)
        data = data.split('<div class="legend">', 1)[1].split('<')
        ans = data[0]
        for i in data[1:]:
            if i.startswith('a href="'):
                href, i = i[8:].split('">', 1)
                href = html.unescape(href)
                ans += '[['+html.escape(urllib.parse.urljoin("https://informatics.msk.ru/mod/statements/view3.php?chapterid=%d"%id, href))+' | '+i
            elif any(i.startswith(x) for x in ('br/>', '/h1', '/h2', '/h3', '/p')):
                ans += '\n' + i.split('>', 1)[1]
            elif i.startswith('/a>'):
                ans += ']]'+i.split('>', 1)[1]
            else:
                ans += i.split('>', 1)[1]
        return ({}, html.unescape(ans.strip()))
    def download_file(self, prob_id, filename):
        raise BruteError("File download doesn't exist on informatics.msk.ru")
    def clars(self):
        raise BruteError("Clarifications don't exits on informatics.msk.ru")
    def submit_clar(self, *args):
        raise BruteError("Clarifications don't exits on informatics.msk.ru")
    def read_clar(self, id):
        raise BruteError("Clarifications don't exits on informatics.msk.ru")
    def stop_caching(self):
        self._cache.clear()

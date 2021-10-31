import urllib.request, urllib.parse, html, json
from brutejudge._http.base import Backend
from brutejudge.error import BruteError
from brutejudge._http.openerwr import OpenerWrapper
import brutejudge._http.html2md as html2md
import brutejudge._http.types as bjtypes

class CodeForces(Backend):
    @staticmethod
    def detect(url):
        url = url.split('/')
        return url[:2] == ['https:', ''] and ('.'+url[2]).endswith('.codeforces.com') and url[3] in ('contest', 'contests')
    @staticmethod
    def _get_csrf(data):
        return data.split('<meta name="X-Csrf-Token" content="', 1)[1].split('"', 1)[0]
    def __init__(self, url, login, password):
        Backend.__init__(self)
        if url.find('/contest') == url.find('/contests'):
            url = '/contest'.join(url.split('/contests', 1))
        self.base_url = url
        self.handle = login
        self.host = url.split('/')[2]
        self.opener = OpenerWrapper(urllib.request.build_opener(urllib.request.HTTPCookieProcessor))
        csrf = self._get_csrf(self.opener.open('https://%s/enter?back=%%2F'%self.host).read().decode('utf-8', 'replace'))
        ln = self.opener.open('https://%s/enter?back=%%2F'%self.host, urllib.parse.urlencode({
            'csrf_token': csrf,
            'action': 'enter',
            'ftaa': '',
            'bfaa': '',
            'handleOrEmail': login,
            'password': password
        }).encode('ascii'))
        if ln.geturl() != 'https://%s/'%self.host:
            raise BruteError("Login failed.")
        self._gs_cache = None
        self._st_cache = None
        self._subms_cache = {}
    def _get_submit(self):
        data = self.opener.open(self.base_url+'/submit')
        if data.geturl() != self.base_url+'/submit':
            return [], [], None
        data = data.read().decode('utf-8', 'replace')
        csrf = self._get_csrf(data)
        data1 = data.split('name="submittedProblemIndex">', 1)[1].split('</select>', 1)[0].split('<option value="')
        tasks = [i.split('"', 1)[0] for i in data1[2:]]
        data2 = data.split('name="programTypeId">', 1)[1].split('</select>', 1)[0].split('<option value="')
        langs = [(int(i.split('"', 1)[0]), html.unescape(i.split('>', 1)[1].split('</option>', 1)[0].strip())) for i in data2[1:]]
        short_codes = {43: 'gcc', 42: 'g++11', 50: 'g++14', 54: 'g++', 2: 'msvc2010', 59: 'msvc2017', 9: 'mcs', 7: 'python', 31: 'python3', 40: 'pypy', 41: 'pypy3'}
        langs_ans = []
        for i, j in langs:
            langs_ans.append(bjtypes.compiler_t(i, short_codes.get(i, str(i)), j))
        return (tasks, langs_ans, csrf)
    def _get_submissions(self):
        with self.cache_lock:
            if self._gs_cache != None: return self._gs_cache
        data = self.opener.open(self.base_url+'/my')
        if data.geturl() != self.base_url+'/my':
            raise BruteError("Failed to fetch submission list")
        data = data.read().decode('utf-8', 'replace')
        csrf = self._get_csrf(data)
        data = data.replace('<tr class="last-row" data-submission-id="', '<tr data-submission-id="').split('<tr data-submission-id="')
        subms = []
        for i in data[1:]:
            subm_id = int(i.split('"', 1)[0])
            meta = {}
            data2 = i.split('>', 1)[1].split('</tr>', 1)[0].split('<td')
            for j in data2[1:]:
                try: cls = j.split('class="', 1)[1].split('"', 1)[0]
                except IndexError: cls = None
                data = j.split('>', 1)[1].split('</td>', 1)[0]
                meta[cls] = data
            subms.append((subm_id, meta))
        ans = (subms, csrf)
        with self.cache_lock:
            if self.caching: self._gs_cache = ans
        return ans
    def _get_submission(self, idx, csrf):
        if idx in self._subms_cache: return self._subms_cache[idx]
        req = self.opener.open('https://'+self.host+'/data/submitSource', urllib.parse.urlencode(
        {
            'submissionId': idx,
            'csrf_token': csrf
        }).encode('ascii'))
        ans = json.loads(req.read().decode('utf-8', 'replace'))
        if self.caching: self._subms_cache[idx] = ans
        return ans
    def tasks(self):
        q = self._get_submit()[0]
        if not q:
            data = self.opener.open(self.base_url).read().decode('utf-8')
            ans = []
            sp = data.split('<a href="'+self.base_url.rsplit('codeforces.com', 1)[1]+'/problem/')
            if sp[0].rfind('<') > sp[0].rfind('>'):
                return ans
            for i in sp[1:]:
                ans.append(i.split('"', 1)[0])
            return [bjtypes.task_t(i, j, None) for i, j in enumerate(ans[::2])]
        return [bjtypes.task_t(i, j, None) for i, j in enumerate(q)]
    def submissions(self):
        data = self._get_submissions()[0]
        return [bjtypes.submission_t(
            i[0],
            i[1]['status-small'].split('<a href="', 1)[1].split('"', 1)[0].rsplit('/', 1)[1],
            self._format_total_status(i[1]['status-cell status-small status-verdict-cell'].split('>', 1)[-1]),
            None,
            self._get_oktests(i[1]['status-cell status-small status-verdict-cell'].split('>', 1)[-1])
        ) for i in data]
    @staticmethod
    def _format_status(st):
        if st == 'OK': return 'OK'
        st = st.replace('_', ' ')
        return st[:1].upper()+st[1:].lower()
    @staticmethod
    def _format_total_status(st):
        v = st.split('<')
        v = v[0]+''.join(i.split('>', 1)[1] for i in v[1:])
        v = v.split(' on test ', 1)[0]
        v = v.split(' on pretest ', 1)[0]
        v = v.split('&nbsp;(', 1)[0]
        v = v.strip()
        return 'OK' if v == 'Accepted' else v
    @staticmethod
    def _get_oktests(st):
        v = st.split('<')
        v = v[0]+''.join(i.split('>', 1)[1] for i in v[1:])
        v = v.split(' on test ', 1)[-1]
        v = v.split(' on pretest ', 1)[-1]
        q = v.split('&nbsp;(')
        if len(q) == 2:
            q[-1] = q[-1].strip()
            assert q[-1].endswith(')')
            try: return int(q[-1][:-1])
            except ValueError: pass
        v = v.strip()
        try: return int(v) - 1
        except ValueError: return None
    def submission_protocol(self, subm_id):
        data = self._get_submission(subm_id, self._get_submissions()[1])
        ntests = int(data.get('testCount', 0))
        ans = []
        for i in range(ntests):
            stats = {}
            try: stats['time_usage'] = float(data['timeConsumed#'+str(i+1)])/1000
            except KeyError: pass
            try: stats['memory_usage'] = int(data['memoryConsumed#'+str(i+1)])
            except KeyError: pass
            try: ans.append(bjtypes.test_t(self._format_status(data['verdict#'+str(i+1)]), stats))
            except KeyError: pass
        return ans
    def _submit(self, task, lang, text, csrf):
        if isinstance(text, str): text = text.encode('utf-8')
        data = []
        data.append(b'"ftaa"\r\n\r\n')
        data.append(b'"bfaa"\r\n\r\n')
        data.append(b'"action"\r\n\r\nsubmitSolutionFormSubmitted')
        data.append(b'"submittedProblemIndex"\r\n\r\n'+task.encode('utf-8'))
        data.append(b'"programTypeId"\r\n\r\n'+str(lang).encode('utf-8'))
        data.append(b'"source"\r\n\r\n'+text)
        import random
        while True:
            x = b'----------'+str(random.randrange(1, 1000000000)).encode('ascii')
            for i in data:
                if x in i: break
            else: break
        data = b'\r\n'.join(b'--'+x+b'\r\n'+b'Content-Disposition: form-data; name='+i for i in data)+b'\r\n--'+x+b'--\r\n'
        try:
            self.opener.open(urllib.request.Request(self.base_url+'/submit?csrf_token='+csrf,
                                data=data,
                                headers={'Content-Type': 'multipart/form-data; boundary='+x.decode('ascii')},
                                method='POST'))
        except urllib.request.URLError: pass
    def submit_solution(self, task, lang, text):
        tasks, langs, csrf = self._get_submit()
        self._submit(tasks[task], lang, text, csrf)
        with self.cache_lock: self.stop_caching()
    def status(self):
        subms = self._get_submissions()[0]
        ans = {j: None for i, j, k in self.tasks()}
        for i, j in subms:
            task = j['status-small'].split('<a href="', 1)[1].split('"', 1)[0].rsplit('/', 1)[1]
            status = self._format_total_status(j['status-cell status-small status-verdict-cell'].split('>', 1)[-1])
            if status in ('Accepted', 'Pretests passed'): status = 'OK'
            if ans.get(task, None) == None or status == 'OK': ans[task] = status
        return ans
    def scores(self):
        with self.cache_lock: data = self._st_cache
        if data == None:
            data = self.opener.open(self.base_url+'/standings').read().decode('utf-8', 'replace')
            with self.cache_lock:
                if self.caching: self._st_cache = data
        tasks = (i.split('href="/contest/', 1)[1].split('"', 1)[0].rsplit('/', 1)[1] for i in data.split('<th ')[5:])
        for i in data.split('<tr participantId="')[1:]:
            i = i.split('</tr>', 1)[0]
            handle = i.split('<a href="/profile/', 1)[1].split('"', 1)[0]
            if handle != self.handle: continue
            ans = {}
            for j in i.replace('<td\r\n'+' '*16+'problemId="', '<td\r\n'+' '*16+'>').split('<td\r\n'+' '*16+'>')[1:]:
                j = j.split('<span class="cell-', 1)[1].split('>', 1)[1].split('</span>', 1)[0]
                try: j = int(j)
                except ValueError: j = -1
                ans[next(tasks)] = j if j >= 0 else None
            return ans
        return {}
    def scoreboard(self):
        contest_id = self.base_url.split('/')
        while not contest_id[-1]: contest_id.pop()
        contest_id = int(contest_id[-1])
        data = json.loads(self.opener.open('https://'+self.host+'/api/contest.standings?contestId=%d&from=1&count=1000000000'%contest_id).read().decode('utf-8', 'replace'))
        if data['status'] != 'OK':
            raise BruteError('Failed to load scoreboard.')
        return [
            ({'name': ', '.join(j['handle'] for j in i['party']['members'])}, [
                ({'score': j['points'], 'attempts': j['bestSubmissionTimeSeconds']} if 'bestSubmissionTimeSeconds' in j else None)
            for j in i['problemResults']])
        for i in data['result']['rows']]
    def _compile_error(self, subm_id, csrf):
        return json.loads(self.opener.open('https://'+self.host+'/data/judgeProtocol',
            urllib.parse.urlencode({
                'submissionId': subm_id,
                'csrf_token': csrf
            }).encode('ascii')).read().decode('utf-8', 'replace'))
    def compile_error(self, subm_id):
        return self._compile_error(subm_id, self._get_submissions()[1])
    def submission_source(self, subm_id):
        subm = self._get_submission(subm_id, self._get_submissions()[1])
        if 'source' in subm: return subm['source'].encode('utf-8')
    def compiler_list(self, prob_id):
        return self._get_submit()[1]
    def submission_stats(self, subm_id):
        subm = self._get_submission(subm_id, self._get_submissions()[1])
        ans = {}
        if 'testCount' in subm and subm['testCount'] and int(subm['testCount']) != 0:
            ntests = int(subm['testCount'])
            ans['tests'] = {'total': ntests}
            success = 0
            for i in range(ntests):
                if ans.get('verdict#'+str(i+1), None) == 'OK':
                    success += 1
            ans['success'] = success
            ans['fail'] = ntests - success
        return (ans, None)
    def problem_info(self, prob_id):
        task = self.tasks()[prob_id][1]
        data = self.opener.open(self.base_url+'/problem/'+task).read().decode('utf-8', 'replace')
        data = data.split('<div class="property-title">', 1)[1].split('</div><div>', 1)[1]
        data = data.split('<script type="text/javascript">', 1)[0]
        return ({}, html2md.html2md(data, None, self.base_url+'/problems/'+task))
    def download_file(self, *args):
        raise BruteError("File download doesn't exist on CodeForces")
    def clar_list(self):
        raise BruteError("Clarifications don't exits on CodeForces")
    def submit_clar(self, *args):
        raise BruteError("Clarifications don't exits on CodeForces")
    def read_clar(self, id):
        raise BruteError("Clarifications don't exits on CodeForces")
    def get_samples(self, subm_id):
        subm = self._get_submission(subm_id, self._get_submissions()[1])
        ans = []
        for i in range(int(subm.get('testCount', '0'))):
            cur = {}
            suf = '#%d'%(i+1)
            if 'input'+suf in subm:
                cur['Input'] = subm['input'+suf]
            if 'output'+suf in subm:
                cur['Output'] = subm['output'+suf]
            if 'answer'+suf in subm:
                cur['Correct'] = subm['answer'+suf]
            if 'checkerStdoutAndStderr'+suf in subm:
                cur['Checker output'] = subm['checkerStdoutAndStderr'+suf]
            ans.append(cur)
        return {i + 1: j for i, j in enumerate(ans)}
    def stop_caching(self):
        self._gs_cache = None
        self._st_cache = None
        self._subms_cache.clear()

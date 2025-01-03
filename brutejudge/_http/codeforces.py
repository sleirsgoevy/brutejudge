import urllib.request, urllib.parse, html, json, time, ssl, warnings
from brutejudge._http.base import Backend
from brutejudge.error import BruteError
from brutejudge._http.ejudge import do_http, get, post
import brutejudge._http.html2md as html2md
import brutejudge._http.types as bjtypes

with warnings.catch_warnings():
    warnings.filterwarnings("ignore")
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
    ctx.verify_mode = ssl.CERT_REQUIRED
    ctx.check_hostname = True
    ctx.load_default_certs(ssl.Purpose.SERVER_AUTH)
    ctx.set_alpn_protocols(['http/1.1'])

class CodeForces(Backend):
    @staticmethod
    def detect(url):
        url = url.split('/')
        return len(url) >= 4 and url[0] in ('http:', 'https:') and not url[1] and ('.'+url[2]).endswith('.codeforces.com') and (url[3] in ('contest', 'contests') or len(url) >= 6 and url[3] == 'group' and url[5] in ('contest', 'contests'))
    @staticmethod
    def _get_csrf(data):
        return data.split('<meta name="X-Csrf-Token" content="', 1)[1].split('"', 1)[0]
    def __init__(self, url, login, password):
        Backend.__init__(self)
        self.locale = 'en'
        cf_clearance = None
        user_agent = 'brutejudge/1.0'
        if '#' in url:
            url, params = url.rsplit('#', 1)
            params = urllib.parse.parse_qs(params)
            if 'locale' in params:
                self.locale = params['locale'][0]
            if 'cf_clearance' in params:
                cf_clearance = params['cf_clearance'][0]
            if 'user_agent' in params:
                user_agent = params['user_agent'][0]
        if url.startswith('http:'):
            url = 'https:' + url[5:]
        if url.find('/contest') == url.find('/contests'):
            url = '/contest'.join(url.split('/contests', 1))
        self.base_url = url
        self.contest_list_url = url.split('/contest/', 1)[0]+'/contests'
        self.handle = login
        self.host = url.split('/')[2]
        cookies = {'cf_clearance': cf_clearance} if cf_clearance != None else {}
        if login != None or password != None:
            req_headers = {}
            while True:
                if cookies:
                    req_headers['Cookie'] = '; '.join(map('='.join, cookies.items()))
                if user_agent != None:
                    req_headers['User-Agent'] = user_agent
                code, headers, data = get('https://%s/enter?back=%%2F'%self.host, req_headers, ssl_context=ctx)
                cookie = headers.get('Set-Cookie', [])
                if isinstance(cookie, str): cookie = [cookie]
                for i in cookie:
                    k, v = i.split(';', 1)[0].split('=', 1)
                    k = k.strip()
                    v = v.strip()
                    cookies[k] = v
                if code == 403:
                    raise BruteError("CloudFlare is angry at you. Get a token!")
                elif code != 200:
                    raise BruteError("Error getting CSRF token for login.")
                elif b'<p>Please wait. Your browser is being checked. It may take a few seconds...</p>' in data:
                    #we were given a PoW. try to solve it
                    pow_suffix = cookies['pow']
                    #print('PoW requested:', pow_suffix)
                    import hashlib
                    idx = 0
                    while True:
                        attempt = '%d_%s'%(idx, pow_suffix)
                        hsh = hashlib.sha1(attempt.encode('ascii')).hexdigest()
                        if hsh.startswith('0000'): break
                        idx += 1
                    #print('PoW solved:', attempt)
                    cookies['pow'] = attempt
                else:
                    break
            if 'Set-Cookie' in headers:
                new_cookies = headers['Set-Cookie']
                if isinstance(new_cookies, str): new_cookies = [new_cookies]
                for i in new_cookies:
                    k, v = i.split(';', 1)[0].strip().split('=', 1)
                    cookies[k] = v
            else:
                raise BruteError("No cookies received from server.")
            self.cookie = '; '.join(map('='.join, cookies.items()))
            self.user_agent = user_agent
            req_headers['Cookie'] = self.cookie
            csrf = self._get_csrf(data.decode('utf-8', 'replace'))
            code, headers, data = post('https://%s/enter?back=%%2F'%self.host, {
                'csrf_token': csrf,
                'action': 'enter',
                'ftaa': '',
                'bfaa': '',
                'handleOrEmail': login,
                'password': password
            }, req_headers, ssl_context=ctx)
            if code != 302 or headers['Location'] != 'https://%s/'%self.host:
                raise BruteError("Login failed.")
            if 'Set-Cookie' in headers:
                new_cookies = headers['Set-Cookie']
                if isinstance(new_cookies, str): new_cookies = [new_cookies]
                for i in new_cookies:
                    k, v = i.split(';', 1)[0].strip().split('=', 1)
                    cookies[k] = v
                self.cookie = '; '.join(map('='.join, cookies.items()))
        self._gs_cache = None
        self._st_cache = None
        self._subms_cache = {}
    def _get(self, path, codes=set(), headers_callback=None):
        if path.startswith('/'):
            path = self.base_url + path
        headers = {'Cookie': self.cookie}
        if self.user_agent != None:
            headers['User-Agent'] = self.user_agent
        code, headers, data = do_http(path, 'GET', headers, headers_callback=headers_callback, ssl_context=ctx)
        if code == 200 and not codes:
            return data
        elif code in codes:
            return code, headers, data
        elif code in (301, 302):
            if headers['Location'] == 'https://%s/enter?back=%%2F'%self.host:
                raise BruteError("Login required (contest not started?)")
            elif headers['Location'] == self.base_url + '/countdown':
                raise BruteError("Contest not started yet (countdown)")
            raise BruteError("Got unexpected redirect %d (%s -> %s)" %(code, path, headers['Location']))
        raise BruteError("HTTP error %d on URL %s"%(code, path))
    def _get_submit(self):
        code, headers, data = self._get('/submit?locale=en', {200, 301, 302})
        if code in (301, 302):
            return None, None, None
        data = data.decode('utf-8', 'replace')
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
        data = self._get('/my?locale=en').decode('utf-8', 'replace')
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
        headers = {
            'Cookie': self.cookie,
            'Referer': self.base_url+'/my',
        }
        if self.user_agent != None:
            headers['User-Agent'] = self.user_agent
        code, headers, req = post(self.base_url.rsplit('/contest/', 1)[0]+'/data/submitSource', {
            'submissionId': idx,
            'csrf_token': csrf
        }, headers, ssl_context=ctx)
        if code != 200:
            raise BruteError("Failed to fetch submission.")
        ans = json.loads(req.decode('utf-8', 'replace'))
        if self.caching: self._subms_cache[idx] = ans
        return ans
    def tasks(self):
        data = self._get(self.base_url).decode('utf-8')
        ans = []
        ans1 = []
        sp = data.replace('\r\n', '\n').split('<td class="id">\n                        <a href="'+self.base_url.rsplit('codeforces.com', 1)[1]+'/problem/')
        if sp[0].rfind('<') > sp[0].rfind('>'):
            return ans
        for i in sp[1:]:
            ans.append(i.split('"', 1)[0])
            ans1.append(i.split('-->', 1)[1].split('<', 1)[0])
        return [bjtypes.task_t(i, j, k) for (i, j), k in zip(enumerate(ans), ans1)]
    def submissions(self, all=False):
        if all:
            contest_id = self.base_url.split('/')
            while not contest_id[-1]: contest_id.pop()
            contest_id = int(contest_id[-1])
            data = json.loads(self._get('https://'+self.host+'/api/contest.status?contestId=%d'%contest_id).decode('utf-8', 'replace'))
            if data['status'] != 'OK':
                raise BruteError('Failed to load submissions.')
            return [bjtypes.submission_t(
                i['id'],
                i['problem']['index'],
                self._format_status(i['verdict']),
                None,
                i['passedTestCount']
            ) for i in data['result']]
        else:
            #TODO: use API here too
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
        headers = {'Content-Type': 'multipart/form-data; boundary='+x.decode('ascii'), 'Cookie': self.cookie}
        if self.user_agent != None:
            headers['User-Agent'] = self.user_agent
        post(self.base_url+'/submit?csrf_token='+csrf, data, headers, ssl_context=ctx)
        # TODO: handle error here?
    def submit_solution(self, task, lang, text):
        tasks, langs, csrf = self._get_submit()
        if tasks is None:
            raise BruteError("Submissions are closed.")
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
            data = self._get('/standings?locale=en').decode('utf-8', 'replace').replace('\r\n', '\n')
            with self.cache_lock:
                if self.caching: self._st_cache = data
        tasks = (i.split('href="/contest/', 1)[1].split('"', 1)[0].rsplit('/', 1)[1] for i in data.split('<th ')[5:])
        for i in data.split('<tr participantId="')[1:]:
            i = i.split('</tr>', 1)[0]
            handle = i.split('<a href="/profile/', 1)[1].split('"', 1)[0]
            if handle != self.handle: continue
            ans = {}
            for j in i.replace('<td\n'+' '*16+'problemId="', '<td\n'+' '*16+'>').split('<td\n'+' '*16+'>')[1:]:
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
        data = json.loads(self._get('https://'+self.host+'/api/contest.standings?contestId=%d&from=1&count=1000000000'%contest_id).decode('utf-8', 'replace'))
        if data['status'] != 'OK':
            raise BruteError('Failed to load scoreboard.')
        return [
            ({'name': ', '.join(j['handle'] for j in i['party']['members'])}, [
                ({'score': j['points'], 'attempts': j['bestSubmissionTimeSeconds']} if 'bestSubmissionTimeSeconds' in j else None)
            for j in i['problemResults']])
        for i in data['result']['rows']]
    def _compile_error(self, subm_id, csrf):
        headers = {'Cookie': self.cookie, 'Content-Type': 'application/x-www-form-urlencoded'}
        if self.user_agent != None:
            headers['User-Agent'] = self.user_agent
        code, headers, data = post(self.base_url.rsplit('/contest/', 1)[0]+'/data/judgeProtocol', {
            'submissionId': subm_id,
            'csrf_token': csrf
        }, headers, ssl_context=ctx)
        if code != 200:
            raise BruteError("Failed to fetch compilation error.")
        return json.loads(data.decode('utf-8', 'replace'))
    def compile_error(self, subm_id):
        return self._compile_error(subm_id, self._get_submissions()[1])
    def submission_source(self, subm_id):
        subm = self._get_submission(subm_id, self._get_submissions()[1])
        if 'source' in subm: return subm['source'].encode('utf-8')
    def action_list(self):
        return ['register']
    def do_action(self, action, *args):
        if action == 'register':
            url = self.base_url.replace('/contest/', '/contestRegistration/')
            headers = {
                'Cookie': self.cookie,
                'Content-Type': 'application/x-www-form-urlencoded',
                'Referer': url,
            }
            if self.user_agent != None:
                headers['User-Agent'] = self.user_agent
            code, headers, data = self._get(url, {200, 302})
            if code != 200:
                return False
            csrf_token = self._get_csrf(data.decode('utf-8', 'replace'))
            code, headers, data = post(url, {
                'csrf_token': csrf_token,
                'action': 'formSubmitted',
                'takePartAs': 'personal',
                'teamId': '-1',
            }, headers, ssl_context=ctx)
            return code == 302
        else:
            raise BruteError("Not implemented.")
    def compiler_list(self, prob_id):
        ans = self._get_submit()[1]
        if ans is None: ans = []
        return ans
    def submission_stats(self, subm_id):
        subm = self._get_submission(subm_id, self._get_submissions()[1])
        ans = {}
        if 'testCount' in subm and subm['testCount'] and int(subm['testCount']) != 0:
            ntests = int(subm['testCount'])
            ans['tests'] = {'total': ntests}
            success = 0
            for i in range(ntests):
                if subm.get('verdict#'+str(i+1), None) == 'OK':
                    success += 1
            ans['success'] = success
            ans['fail'] = ntests - success
        return (ans, None)
    def contest_info(self):
        ans = {}
        data = self._get(self.base_url.replace('/contest/', '/contests/')+'?locale=en').decode('utf-8', 'replace').replace('\r\n', '\n')
        data = data.split('<span class="format-time"', 1)[1].split('>', 1)[1].strip()
        date = data.split('<', 1)[0] # dd.mm.yyyy hh:mm, Mmm/dd/yyyy hh:mm for English locale!!!
        duration = data.split('</span>\n                </a>\n    </td>\n    <td>', 1)[1].split('<', 1)[0].strip() # hh:mm
        q1 = {'Start': date, 'Length': duration}
        if ' class="countdown">' in data:
            countdown = data.split(' class="countdown">', 1)[1].split('<', 1)[0].strip() # hh:mm:ss
            q1['Time left'] = countdown
        else:
            countdown = None
        q2 = {}
        dur = 0
        assert duration.count(':') == 1
        for i in map(int, duration.split(':')):
            dur = 60 * dur + i
        dur *= 60
        if countdown is None:
            left = None
        else:
            left = 0
            assert countdown.count(':') == 2
            for i in map(int, countdown.split(':')):
                left = 60 * left + i
        date, tm = date.split()
        h, m = map(int, tm.split(':'))
        if '/' in date:
            mt, d, y = date.split('/')
            d = int(d)
            y = int(y)
            mt = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'].index(mt) + 1
        else:
            d, mt, y = map(int, date.split('.'))
        start = int(time.mktime((y, mt, d, h, m, 0, -1, -1, -1)))
        q2['contest_start'] = start
        q2['contest_duration'] = dur
        q2['contest_end'] = start + dur
        if left is not None:
            q2['contest_time'] = dur - left
            q2['server_time'] = start + (dur - left)
        return '', q1, q2
    def problem_info(self, prob_id):
        task = self.tasks()[prob_id][1]
        data = self._get('/problem/'+task+'?locale='+self.locale, headers_callback=lambda code, headers: True if headers['Content-Type'] != 'text/html;charset=UTF-8' else None)
        if data is True:
            return {}, '['+self.base_url+'/problem/'+task+'?locale='+self.locale+'](Problem statements)'
        data = data.decode('utf-8', 'replace')
        data = data.split('<div class="property-title">', 1)[1].split('</div><div>', 1)[1]
        data = data.split('<script>')[0]
        data = data.split('<script type="text/javascript">', 1)[0]
        return ({}, html2md.html2md(data, None, self.base_url+'/problem/'+task+'?locale='+self.locale))
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
    def contest_list(self):
        if isinstance(self, str):
            headers = {'User-Agent': 'brutejudge/0.1'}
        else:
            headers = {'Cookie': self.cookie}
            if self.user_agent != None:
                headers['User-Agent'] = self.user_agent
            self = self.contest_list_url
        if self.startswith('http:'): self = 'https:' + self[5:]
        code, resp_headers, data = get(self, headers, ssl_context=ctx)
        while code in (301, 302):
            self = urllib.parse.urljoin(self, resp_headers['Location'])
            code, headers, data = get(self, headers, ssl_context=ctx)
        if code != 200:
            raise BruteError("Failed to fetch contest list.")
        data = data.decode('utf-8').replace('\r\n', '\n').replace('<tr\n     class="highlighted-row"\n    data-contestId="', '<tr\n    \n    data-contestId="').split('<tr\n    \n    data-contestId="')
        ans = []
        for i in data[1:]:
            cid, name = i.split('"', 1)
            cid = int(cid)
            url = 'https://codeforces.com/contest/'+str(cid)
            name = name.lstrip()
            if name.startswith('data-groupContestId="'):
                assert '/group/' in self and self.endswith('/contests')
                #cid = int(name.split('"', 2)[1])
                url = self[:-1]+'/'+str(cid)
            name = html.unescape(name.split('<td>', 1)[1].split('<br/>', 1)[0].split('</td>', 1)[0].strip())
            ans.append((name, url, {}))
        return ans
    def locales(self):
        return [('en', 'English'), ('ru', 'Russian')]
    def set_locale(self, which):
        self.locale = which

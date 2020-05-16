import ssl, socket, html, collections, urllib.parse, time, math
import brutejudge._http.ejudge.ej371, brutejudge._http.ejudge.ej373, brutejudge._http.html2md as html2md
from brutejudge._http.base import Backend
from brutejudge.error import BruteError

def _http_header_capitalize(h):
    return '-'.join(i[:1].upper()+i[1:].lower() for i in h.split('-'))

def do_http(url, method, headers={}, data=b''):
    if '://' not in url:
        raise BruteError("Invalid URL")
    proto, path = url.split('://', 1)
    if proto not in ('http', 'https'):
        raise BruteError("Not an HTTP url: " + url)
    if '/' not in path: path += '/'
    s_host, path = path.split('/', 1)
    path = '/' + path
    host = s_host
    if ':' in host:
        host, port = host.rsplit(':', 1)
        port = int(port)
    else: port = 80 if proto == 'http' else 443
    if host.startswith('[') and host.endswith(']'): host = host[1:-1]
    sock = socket.create_connection((host, port))
    if proto == 'https':
        sock = ssl.create_default_context().wrap_socket(sock, server_hostname=host)
    headers['Host'] = s_host
    if data:
        headers['Content-Length'] = len(data)
    request = ['%s %s HTTP/1.1' % (method, path)]
    for k, v in headers.items():
        request.append(str(k) + ': ' + str(v))
    request.append('')
    request.append('')
    sock.sendall('\r\n'.join(request).encode('utf-8'))
    if data:
        sock.sendall(data)
    def readline():
        ans = b''
        while not ans.endswith(b'\n'): ans += sock.recv(1)
        return ans
    v, c, *exp = readline().decode('utf-8').split()
    resp_headers = []
    while True:
        l = readline().decode('utf-8').strip()
        if l == '': break
        k, v = l.split(': ', 1)
        resp_headers.append((_http_header_capitalize(k), v))
    rhd = dict(resp_headers)
    if 'Content-Length' in rhd:
        data = b''
        while len(data) < int(rhd['Content-Length']):
            data += sock.recv(int(rhd['Content-Length']) - len(data))
    elif rhd.get('Transfer-Encoding', None) == 'chunked':
        data = b''
        while True:
            l = int(readline().decode('ascii'), 16)
            data2 = b''
            while len(data2) < l:
                data2 += sock.recv(l - len(data2))
            data += data2
            readline()
            if l == 0: break
    else:
        data = b''
        nfails = 0
        while nfails < 100:
            try: chunk = sock.recv(1 << 20)
            except socket.error: break
            data += chunk
            if len(chunk) == 0: break
    sock.close()
    return (int(c), rhd, data)

#try: import requests
#except ImportError: pass
#else:
#   def do_http(url, method, headers, data=b''):
#       if method == 'GET': data = None
#       it = requests.request(method, url, data=data, headers=headers, allow_redirects=False)
#       return (it.status_code, it.headers, it.content)

def get(url, headers={}):
    return do_http(url, 'GET', headers)

def post(url, data, headers={}):
    if isinstance(data, dict):
        l = []
        for k, v in data.items():
            k += '='
            for c in str(v):
                if c.lower() in 'abcdefghijklmnopqrstuvwxyz0123456789':
                    k += c
                else:
                    k += ''.join(map('%%%02x'.__mod__, c.encode('utf-8')))
            l.append(k)
        data = '&'.join(l)
    if isinstance(data, str):
        data = data.encode('utf-8')
    return do_http(url, 'POST', headers, data)

def contest_name(url):
    code, headers, data = get(url)
    if code != 200:
        raise BruteError("Page retrieval failed.")
    try: return html.unescape(data.decode('utf-8', 'replace').split('<title>', 1)[1].split(' [', 1)[1].split(']</title>', 1)[-2])
    except IndexError: return None

class Ejudge(Backend):
    @staticmethod
    def detect(url):
        return url.startswith('http://') or url.startswith('https://')
    def __init__(self, url, login, password):
        Backend.__init__(self)
        url = url.replace('/new-register?', '/new-client?')
        contest_id = url.split("contest_id=")[1].split("&")[0]
        self.contest_id = int(contest_id)
        base_url = url.split("?")[0]
        code, headers, data = post(base_url, {'contest_id': contest_id, 'locale_id': 0, 'login': login, 'password': password, 'action_213': ''})
        if code != 302:
            raise BruteError("Login failed.")
        rhd = dict(headers)
        base_url = rhd['Location'].split('&')[0]
        if 'new-client?SID=' in base_url:
            urls = ej371.get_urls(base_url)
        elif any(i in base_url for i in ('/user/', '/client/', '/register/', '/register?SID=')):
            urls = ej373.get_urls(base_url)
        else:
            raise BruteError("Unknown ejudge version.")
        self.urls = urls
        self.cookie = rhd["Set-Cookie"].split(";")[0]
        self._get_cache = {}
    def _cache_get(self, url, cookie=True):
        with self.cache_lock:
            if url in self._get_cache:
                return self._get_cache[url]
        ans = get(url, {'Cookie': self.cookie} if cookie else {})
        with self.cache_lock:
            if self.caching: self._get_cache[url] = ans
        return ans
    def task_list(self):
        code, headers, data = self._cache_get(self.urls['summary'])
        if code != 200:
            raise BruteError("Failed to fetch task list.")
        column_count = data.count(b'<th ')
        if column_count == 0: return []
        splitted = data.decode('utf-8').split('<td class="b1">')[1:]
        data = []
        for x in splitted[::column_count]:
            x = x.split("</td>")[0]
            if x.startswith('<a href="') and x.endswith('</a>'):
                x = x.split('"', 2)[2].split('>', 1)[1][:-4]
            data.append(html.unescape(x))
        return data
    def submission_list(self):
        code, headers, data = self._cache_get(self.urls['submissions'])
        if code != 200:
            raise BruteError("Failed to fetch submission list.")
        ths = [i.split('</th>', 1)[0] for i in data.decode('utf-8').split('<th class="b1">')[1:]]
        w = len(ths)
        if w == 0: return [], []
        splitted = data.decode('utf-8').split('<td class="b1">')[1:]
        data = [x.split("</td>")[0] for x in splitted]
        return list(map(lambda x:(int(x[:-1]) if x[-1:] == '#' else int(x)), data[ths.index('Run ID')::w])), data[ths.index('Problem')::w]
    def submission_results(self, id):
        code, headers, data = self._cache_get(self.urls['protocol'].format(run_id=id))
        if code != 200:
            raise BruteError("Failed to fetch testing protocol.")
        w = data.count(b'<th ')
        if w == 0: return [], []
        splitted = data.decode('utf-8').split('<td class="b1">')[1:]
        data = [x.split("</td>")[0] for x in splitted]
        return [i[:-7].split('>')[-1] for i in data[1::w]], list(map(html.unescape, data[2::w]))
    def task_ids(self):
        code, headers, data = self._cache_get(self.urls['summary'])
        if code != 200:
            raise BruteError("Failed to fetch task list.")
        try:
            data = data.decode('utf-8').split('<tr id="probNavTopList"><td width="100%" class="nTopNavList"><ul class="nTopNavList"><li class="first-rad">', 1)[1].split('\n', 1)[0]
        except IndexError: return []
        splitted = data.split('<a class="tab" href="')[1:]
        data = [x.split('"')[0] for x in splitted]
        ans = []
        for i in data:
            ans.append(int(i.split('prob_id=', 1)[1]))
        return ans
    def submit(self, task, lang, text):
        if isinstance(text, str): text = text.encode('utf-8')
        try: task = self.task_ids()[task]#task += 1
        except IndexError: return
        sid = self.urls['sid']
        url = self.urls['submit']
        data = []
        data.append(b'"SID"\r\n\r\n'+sid.encode('ascii'))
        data.append(b'"prob_id"\r\n\r\n'+str(task).encode('ascii'))
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
        ans = post(url, data, {'Content-Type': 'multipart/form-data; boundary='+x.decode('ascii'), 'Cookie': self.cookie})
        with self.cache_lock: self.stop_caching()
        return ans
    def status(self):
        code, headers, data = self._cache_get(self.urls['summary'])
        if code != 200:
            raise BruteError("Failed to fetch task list")
        ths = [i.split('</th>', 1)[0] for i in data.decode('utf-8').split('<th class="b1">')[1:]]
        w = len(ths)
        if w == 0: return {}
        splitted = data.decode('utf-8').split('<td class="b1">')[1:]
        data = [x.split("</td>")[0] for x in splitted]
        idx = ths.index('Status')
        return collections.OrderedDict((a, b if b != '&nbsp;' else None) for a, b in zip(data[ths.index('Short name')::w], data[idx::w]))
    def scores(self):
        code, headers, data = self._cache_get(self.urls['summary'])
        if code != 200:
            raise BruteError("Failed to fetch task list")
        ths = [i.split('</th>', 1)[0] for i in data.decode('utf-8').split('<th class="b1">')[1:]]
        w = len(ths)
        splitted = data.decode('utf-8').split('<td class="b1">')[1:]
        data = [x.split("</td>")[0] for x in splitted]
        if 'Score' not in ths: return {}
        return collections.OrderedDict(zip(data[ths.index('Short name')::w], [None if x == '&nbsp;' else int(x) for x in data[ths.index('Score')::w]]))
    def compile_error(self, id):
        code, headers, data = self._cache_get(self.urls['protocol'].format(run_id=id))
        if code != 200:
            raise BruteError("Failed to fetch testing protocol.")
        splitted = data.decode('utf-8').split('<pre>')[1:]
        ans = []
        for i in splitted:
            i = i.split('</pre>')[0]
            i = i.split('<')
            i = i[0] + ''.join(j.split('>', 1)[1] for j in i[1:])
            import html
            ans.append(html.unescape(i))
        return '\n'.join(ans)
    def _submission_field(self, id, field):
        code, headers, data = self._cache_get(self.urls['submissions'])
        if code != 200:
            raise BruteError("Failed to fetch submission list.")
        ths = [i.split('</th>', 1)[0] for i in data.decode('utf-8').split('<th class="b1">')[1:]]
        w = len(ths)
        if w == 0: return [], []
        splitted = data.decode('utf-8').split('<td class="b1">')[1:]
        data = [x.split("</td>")[0] for x in splitted]
        if field not in ths: return None
        for i, j in zip(map(lambda x:(int(x[:-1]) if x[-1:] == '#' else int(x)), data[ths.index('Run ID')::w]), data[ths.index(field)::w]):
            if i == id: return j
    def submission_status(self, id):
        return self._submission_field(id, 'Result')
    def submission_source(self, id):
        code, headers, data = self._cache_get(self.urls['source'].format(run_id=id))
        rhd = dict(headers)
        if code != 200 or 'html' in rhd['Content-Type']:
            return None
        return data
    def do_action(self, name, need_code, fail_pattern=None):
        code, headers, data = get(self.urls[name], {'Cookie': self.cookie})
        return code == need_code and (fail_pattern == None or fail_pattern not in data)
    def compiler_list(self, prob_id):
        code, headers, data = self._cache_get(self.urls['submission'].format(prob_id=prob_id))
        data = data.decode('utf-8')
        if '<input type="hidden" name="lang_id" value="' in data:
            data = data.split('<input type="hidden" name="lang_id" value="', 1)[1]
            num_id = int(data.split('"', 1)[0])
            lit_id = html.unescape(data.split('</td><td class="b0">', 1)[1].split('</td>', 1)[0])
            short, long = lit_id.strip().split(' - ')
            return [(num_id, short, long)]
        try: data = data.split('<select name="lang_id">', 1)[1].split('</select>', 1)[0]
        except IndexError: raise BruteError("Failed to fetch language list")
        data = data.split('<option ')[1:]
        ans = [] 
        for i in data:
            a, b = (' '+i).split(' value="', 1)[1].split('"', 1)
            b = b.split('>', 1)[1].split('</option>', 1)[0]
            if not a.isnumeric(): continue
            b, c = html.unescape(b).split(' - ')
            ans.append((int(a), b.strip(), c.strip()))
        return ans
    def _submission_stats(self, id):
        code, headers, data = self._cache_get(self.urls['protocol'].format(run_id=id))
        data = data.decode('utf-8')
        if '<big>' in data:
            data = '\n\n'.join(i.split('</big>', 1)[0] for i in data.split('<big>')[1:]).split('<')
            data = data[0]+''.join(i.split('>', 1)[1] for i in data[1:])
            ans = {}
            for l in data.split('\n'):
                l = l.split(' ')
                if l[1:4] == ['total', 'tests', 'runs,'] and l[5] == 'passed,' and l[7:] == ['failed.']:
                    ans['tests'] = {}
                    ans['tests']['total'] = int(l[0])
                    ans['tests']['success'] = int(l[4]) 
                    ans['tests']['fail'] = int(l[6])
                elif l[:2] == ['Score', 'gained:']:
                    ans['score'] = int(l[2])
            return (ans, data)
        else:
            return ({}, None)
    def submission_stats(self, id):
        ans1, ans2 = self._submission_stats(id)
        tp = self._submission_field(id, 'Tests passed')
        if tp != None and not (tp+' ').isspace() and tp.strip() != '&nbsp;': tp = int(tp)
        else: tp = None
        if tp != None:
            if 'tests' not in ans1: ans1['tests'] = {}
            ans1['tests']['success'] = tp
        return (ans1, ans2)
    def contest_info(self):
        code, headers, data = self._cache_get(self.urls['contest_info'])
        data = data.decode('utf-8')
        try: pbs = '\n'.join(html.unescape(i.split('</b></p>', 1)[0]) for i in data.split('<p><b>')[1:])
        except IndexError: pbs = ''
        datas = {}
        for i in data.split('<tr><td class="b0">')[1:]:
            i = i.split('</td></tr>', 1)[0] 
            try: key, value = i.split('<td class="b0">')
            except IndexError: pass
            else: datas[html.unescape(key.split('</td>', 1)[0])] = html.unescape(value)
        data1 = {}
        for k1, k2 in (('server_time', 'Server time:'), ('contest_start', 'Contest start time'), ('contest_duration', 'Duration:')):
            if k2 not in datas: continue
            if datas[k2] == 'Unlimited':
                data1[k1] = math.inf
                continue
            date, s_time = datas[k2].split(' ')
            year, month, day = map(int, date.split('/'))
            hour, minute, second = map(int, s_time.split(':'))
            data1[k1] = time.mktime((year, month, day, hour, minute, second, -1, -1, -1))
        if 'contest_start' in data1 and 'contest_duration' in data1:
            data1['contest_end'] = data1['contest_start'] + data1['contest_duration']
        if 'contest_start' in data1 and 'server_time' in data1:
            data1['contest_time'] = data1['server_time'] - data1['contest_start']
        return (pbs, datas, data1)
    def problem_info(self, id):
        code, headers, data = self._cache_get(self.urls['submission'].format(prob_id=id))
        data = data.decode('utf-8')
        if '<table class="line-table-wb">' not in data: return ({}, None)
        data = data.split('<table class="line-table-wb">', 1)[1]
        stats = {}
        data, data2 = data.split('</table>', 1)
        while '<tr><td><b>' in data:
            k, data = data.split('<tr><td><b>', 1)[1].split('</b></td><td>', 1)
            v, data = data.split('</td></tr>', 1)
            v = v.split('<')
            v = v[0]+''.join(i.split('>', 1)[1] for i in v[1:])
            stats[k.rsplit(':', 1)[0].strip()] = html.unescape(v.strip())
        data = data2.split('<form method="post" enctype="multipart/form-data" action="', 1)[0].rsplit('<h3>', 1)[0]
        return (stats, html2md.html2md(data, self.urls['download_file'].format(prob_id=id, filename=''), self.urls['submission'].format(prob_id=id)))
    def download_file(self, prob_id, filename):
        code, headers, data = self._cache_get(self.urls['download_file'].format(prob_id=prob_id, filename=filename))
        if code == 404:
            raise BruteError("File not found.")
        elif code != 200:
            raise BruteError("Error downloading.")
        return data
    def submission_score(self, id):
        j = self._submission_field(id, 'Score')
        if j == None: return None
        if j.startswith('<b>') and j.endswith('</b>'): j = j[3:-4]
        if (j+' ').isspace() or j == 'N/A': return None
        return int(j)
    def clars(self):
        code, headers, data = self._cache_get(self.urls['clars'])
        ths = [i.split('</th>', 1)[0] for i in data.decode('utf-8').split('<th class="b1">')[1:]]
        w = len(ths)
        splitted = data.decode('utf-8').split('<td class="b1">')[1:]
        data = [x.split("</td>")[0] for x in splitted]
        return list(map(int, data[ths.index('Clar ID')::w])), list(map(html.unescape, data[ths.index('Subject')::w]))
    def submit_clar(self, task, subject, text): 
        if post(self.urls['submit'], {'SID': self.urls['sid'], 'prob_id': task, 'subject': subject, 'text': text, 'action_41': 'Send!'}, {'Cookie': self.cookie})[0] != 302:
            raise BruteError("Failed to submit clar")
        with self.cache_lock: self.stop_caching()
    def read_clar(self, id):
        code, headers, data = self._cache_get(self.urls['read_clar'].format(clar_id=id))
        data = html.unescape(data.decode('utf-8').split('<pre class="message">', 1)[1].split('</pre>', 1)[0])
        return data.split('\n', 2)[2]
    def _get_samples(self, err):
        if err == None: err = ''
        err = err.strip()
        if "====== Test #" not in err:
            raise BruteError("No test cases available")
        err = err[err.find("====== Test #"):]
        lines = iter(err.split('\n'))
        tests = {}
        curr = None
        for line in lines:
            if line.startswith("====== Test #"):
                num = int(line[13:-7])
                curr = tests[num] = {}
            elif line.startswith('--- '):
                line = line[4:-4]
                if ': size ' not in line: continue
                what, size = line.split(': size ')
                size = int(size) + 1
                data = ''
                while len(data) < size:
                    try: data += '\n' + next(lines)
                    except StopIteration: break
                data = data[1:]
                curr[what] = data
        return tests
    def get_samples(self, subm_id):
        return self._get_samples(self.compile_error(subm_id))
    def scoreboard(self):
        code, headers, data = self._cache_get(self.urls['standings'])
        if code != 200:
            raise BruteError("Failed to fetch scoreboard.")
        teams = data.decode('utf-8').split('<td  class="st_team">')[1:]
        teams = [html.unescape(x.split("</td>")[0]) for x in teams]
        probs = data.decode('utf-8').split('<td  class="st_prob')[1:]
        probs = [x.split("</td>")[0] for x in probs]
        try: ntasks = len(probs) // len(teams)
        except ZeroDivisionError: return []
        del teams[-3:]
        del probs[-3*ntasks:]
        probs = iter(probs)
        ans = []
        for i in teams:
            ans.append(({'name': i}, []))
            for j in range(ntasks):
                j = next(probs).split('>', 1)[1]
                if j == '&nbsp;': ans[-1][1].append(None)
                elif j[:1] in ('+', '-'):
                    attempts = int(j[0]+'0'+j[1:])
                    ans[-1][1].append({'attempts': attempts})
                elif j.startswith('<b>') and j.endswith('</b>') and j[3:-4].isnumeric():
                    score = int(j[3:-4])
                    attempts = float('inf')
                    ans[-1][1].append({'score': score, 'attempts': attempts})
                elif j.isnumeric():
                    score = int(j)
                    attempts = float('-inf')
                    ans[-1][1].append({'score': score, 'attempts': attempts})
                else:
                    assert False, j
        return ans
    def stop_caching(self):
        self._get_cache.clear()
    def contest_list(self):
        if isinstance(self, str): url = self
        else: url = self.urls['contest_list']
        code, headers, data = get(url)
        if code != 200:
            return []
        ans = []
        for i in data.decode('utf-8').split('<td><a href="')[1:]:
            url = html.unescape(i.split('"', 1)[0])
            name = html.unescape(i.split('>', 1)[1].split('<', 1)[0])
            ans.append((name, url, {}))
        return ans

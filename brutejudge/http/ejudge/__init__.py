import ssl, socket, html, collections
import brutejudge.http.ejudge.ej371, brutejudge.http.ejudge.ej373
from brutejudge.error import BruteError

def do_http(url, method, headers, data=b''):
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
        host, port = host.split(':')
        port = int(port)
    else: port = 80 if proto == 'http' else 443
    sock = socket.create_connection((host, port))
    if proto == 'https':
        sock = ssl.wrap_socket(sock)
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
        resp_headers.append((k, v))
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

class Ejudge:
    def __init__(self, url, login, password):
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
        elif '/user/' in base_url or '/client/' in base_url or '/register?SID=' in base_url:
            urls = ej373.get_urls(base_url)
        else:
            raise BruteError("Unknown ejudge version.")
        self.urls = urls
        self.cookie = rhd["Set-Cookie"].split(";")[0]
    def task_list(self):
        code, headers, data = get(self.urls['summary'], {'Cookie': self.cookie})
        if code != 200:
            raise BruteError("Failed to fetch task list.")
        column_count = data.count(b'<th ')
        if column_count == 0: return []
        splitted = data.decode('utf-8').split('<td class="b1">')[1:]
        data = [x.split("</td>")[0] for x in splitted]
        return data[::column_count]
    def submission_list(self):
        code, headers, data = get(self.urls['submissions'], {'Cookie': self.cookie})
        if code != 200:
            raise BruteError("Failed to fetch submission list.")
        w = data.count(b'<th ')
        if w == 0: return [], []
        splitted = data.decode('utf-8').split('<td class="b1">')[1:]
        data = [x.split("</td>")[0] for x in splitted]
        return list(map(lambda x:(int(x[:-1]) if x[-1:] == '#' else int(x)), data[::w])), data[3::w]
    def submission_results(self, id):
        code, headers, data = get(self.urls['protocol'].format(run_id=id), {'Cookie': self.cookie})
        if code != 200:
            raise BruteError("Failed to fetch testing protocol.")
        w = data.count(b'<th ')
        if w == 0: return [], []
        splitted = data.decode('utf-8').split('<td class="b1">')[1:]
        data = [x.split("</td>")[0] for x in splitted]
        return [i[:-7].split('>')[-1] for i in data[1::w]], list(map(html.unescape, data[2::w]))
    def task_ids(self):
        code, headers, data = get(self.urls['summary'], {'Cookie': self.cookie})
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
        task = self.task_ids()[task]#task += 1
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
        return post(url, data, {'Content-Type': 'multipart/form-data; boundary='+x.decode('ascii'), 'Cookie': self.cookie})
    def status(self):
        code, headers, data = get(self.urls['summary'], {'Cookie': self.cookie})
        if code != 200:
            raise BruteError("Failed to fetch task list")
        w = data.count(b'<th ')
        if w == 0: return {}
        splitted = data.decode('utf-8').split('<td class="b1">')[1:]
        data = [x.split("</td>")[0] for x in splitted]
        idx = 2 if data[1].startswith('<a ') else 1
        return collections.OrderedDict((a, b if b != '&nbsp;' else None) for a, b in zip(data[::w], data[idx::w]))
    def scores(self):
        code, headers, data = get(self.urls['summary'], {'Cookie': self.cookie})
        if code != 200:
            raise BruteError("Failed to fetch task list")
        w = data.count(b'<th ')
        splitted = data.decode('utf-8').split('<td class="b1">')[1:]
        data = [x.split("</td>")[0] for x in splitted]
        w1 = w
        if not data[1].startswith('<a '): w1 += 1
        if w1 != 6: return {}
        return dict(zip(data[::w], [None if x == '&nbsp;' else int(x) for x in data[w-2::w]]))
    def compile_error(self, id):
        code, headers, data = get(self.urls['protocol'].format(run_id=id), {'Cookie': self.cookie})
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
    def submission_status(self, id):
        code, headers, data = get(self.urls['submissions'], {'Cookie': self.cookie})
        if code != 200:
            raise BruteError("Failed to fetch submission list.")
        w = data.count(b'<th ')
        if w == 0: return [], []
        splitted = data.decode('utf-8').split('<td class="b1">')[1:]
        data = [x.split("</td>")[0] for x in splitted]
        for i, j in zip(map(lambda x:(int(x[:-1]) if x[-1:] == '#' else int(x)), data[::w]), data[5::w]):
            if i == id: return j
    def submission_source(self, id):
        code, headers, data = get(self.urls['source'].format(run_id=id), {'Cookie': self.cookie})
        rhd = dict(headers)
        if code != 200 or 'html' in rhd['Content-Type']:
            return None
        return data
    def do_action(self, name, need_code, fail_pattern=None):
        code, headers, data = get(self.urls[name], {'Cookie': self.cookie})
        return code == need_code and (fail_pattern == None or fail_pattern not in data)
    def compiler_list(self, prob_id):
        code, headers, data = get(self.urls['submission'].format(prob_id=prob_id), {'Cookie': self.cookie})
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

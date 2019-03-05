import ssl, socket
from .error import BruteError

def do_http(url, method, headers, data=b''):
    if '://' not in url:
        raise BruteError("Invalid URL")
    proto, path = url.split('://')
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
        sock = ssl.SSLSocket(sock)
    headers['Host'] = s_host
    if data:
        headers['Content-Length'] = len(data)
    request = ['%s %s HTTP/1.0' % (method, path)]
    for k, v in headers.items():
        request.append(str(k) + ': ' + str(v))
    request.append('')
    request.append('')
    file = sock.makefile('rwb', 0)
    file.write('\r\n'.join(request).encode('utf-8'))
    if data:
        file.write(data)
    v, c, *exp = file.readline().decode('utf-8').split()
    resp_headers = {}
    while True:
        l = file.readline().decode('utf-8').strip()
        if l == '': break
        k, v = l.split(': ', 1)
        resp_headers[k] = v
    data = file.read(int(resp_headers.get('Content-Length', -1)))
    return (int(c), resp_headers, data)

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

def login(url, login, password):
    contest_id = url.split("contest_id=")[1].split("&")[0]
    base_url = url.split("?")[0]
    code, headers, data = post(base_url, {'contest_id': contest_id, 'locale_id': 0, 'login': login, 'password': password, 'action_213': ''})
    if code != 302:
        raise BruteError("Login failed.")
    base_url = headers['Location'].split('&')[0]
    return (base_url, headers["Set-Cookie"].split(";")[0])

def task_list(url, cookie):
    code, headers, data = get(url + '&action=137', {'Cookie': cookie})
    if code != 200:
        raise BruteError("Failed to fetch task list.")
    column_count = data.count(b'<th ')
    if column_count == 0: return []
    splitted = data.decode('utf-8').split('<td class="b1">')[1:]
    data = [x.split("</td>")[0] for x in splitted]
    return data[::column_count]

def submission_list(url, cookie):
    code, headers, data = get(url + '&action=140&all_runs=1', {'Cookie': cookie})
    if code != 200:
        raise BruteError("Failed to fetch submission list.")
    w = data.count(b'<th ')
    if w == 0: return [], []
    splitted = data.decode('utf-8').split('<td class="b1">')[1:]
    data = [x.split("</td>")[0] for x in splitted]
    return list(map(int, data[::w])), data[3::w]

def submission_results(url, cookie, id):
    code, headers, data = get(url + '&action=37&run_id=%d'%id, {'Cookie': cookie})
    if code != 200:
        raise BruteError("Failed to fetch testing protocol.")
    w = data.count(b'<th ')
    if w == 0: return [], []
    splitted = data.decode('utf-8').split('<td class="b1">')[1:]
    data = [x.split("</td>")[0] for x in splitted]
    return [i[:-7].split('>')[-1] for i in data[1::w]], data[2::w]

def task_ids(url, cookie):
    code, headers, data = get(url + '&action=137', {'Cookie': cookie})
    if code != 200:
        raise BruteError("Failed to fetch task list.")
    w = data.count(b'<th ')
    if w == 0: return []
    splitted = data.decode('utf-8').split('<td class="b1">')[1:]
    data = [x.split("</td>")[0] for x in splitted]
    ans = []
    for i in data[1::w]:
        ans.append(int(i.split('prob_id=', 1)[1].split('"', 1)[0]))
    return ans

def submit(url, cookie, task, lang, text):
    task = task_ids(url, cookie)[task]#task += 1
    sid = url.split("SID=")[-1].split("&")[0]
    url = url.split("?")[0]
    data = []
    data.append('"SID"\r\n\r\n'+sid)
    data.append('"prob_id"\r\n\r\n'+str(task))
    data.append('"lang_id"\r\n\r\n'+str(lang))
    data.append('"file"; filename="brute.txt"\r\nContent-Type'
                ': text/plain\r\n\r\n'+text)
    data.append('"action_40"\r\n\r\nSend!')
    import random
    while True:
        x = '----------'+str(random.randrange(1, 1000000000))
        for i in data:
            if x in i: break
        else: break
#   x = '-----------------------------850577185583170701784494929'
    data = '\r\n'.join('--'+x+'\r\n'+'Content-Disposition: form-data; name='+i for i in data)+'\r\n--'+x+'--\r\n'
    return post(url, data, {'Content-Type': 'multipart/form-data; boundary='+x, 'Cookie': cookie})

def status(url, cookie):
    code, headers, data = get(url + '&action=137', {'Cookie': cookie})
    if code != 200:
        raise BruteError("Failed to fetch task list")
    w = data.count(b'<th ')
    if w == 0: return {}
    splitted = data.decode('utf-8').split('<td class="b1">')[1:]
    data = [x.split("</td>")[0] for x in splitted]
    return dict(zip(data[::w], data[2::w]))

def scores(url, cookie):
    code, headers, data = get(url + '&action=137', {'Cookie': cookie})
    if code != 200:
        raise BruteError("Failed to fetch task list")
    w = data.count(b'<th ')
    if w != 6: return {}
    splitted = data.decode('utf-8').split('<td class="b1">')[1:]
    data = [x.split("</td>")[0] for x in splitted]
    return dict(zip(data[::w], [None if x == '&nbsp;' else int(x) for x in data[4::w]]))

def compile_error(url, cookie, id):
    code, headers, data = get(url + '&action=37&run_id=%d'%id, {'Cookie': cookie})
    if code != 200:
        raise BruteError("Failed to fetch testing protocol.")
    splitted = data.decode('utf-8').split('<pre>', 2)[1].split('</pre>')[0]
    splitted = splitted.split('<')
    splitted = splitted[0] + ''.join(i.split('>', 1)[1] for i in splitted[1:])
    import html
    return html.unescape(splitted)

def submission_status(url, cookie, id):
    code, headers, data = get(url + '&action=37&run_id=%d'%id, {'Cookie': cookie})
    if code != 200:
        raise BruteError("Failed to fetch testing protocol.")
    try: return data.decode('utf-8').split('<h2 ', 1)[1].split('>', 1)[1].split('<', 1)[0]
    except IndexError: return ''

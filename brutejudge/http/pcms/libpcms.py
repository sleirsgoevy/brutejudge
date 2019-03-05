import urllib.request, urllib.parse, html, json

class PCMS:
    def __init__(self, url, auth=None):
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor)
        req = self.opener.open(url)
        if req.geturl().endswith('/login.xhtml'):
            login, password = auth
            req2 = self.opener.open(req.geturl(), urllib.parse.urlencode({'login': 'login', 'login:name': login, 'login:password': password, 'login:submit': 'Login', 'javax.faces.ViewState': self.get_view_state(req.read().decode('utf-8'))}).encode('ascii'))
#           except Exception as e: req2 = e
#           print(req2.read().decode('utf-8'))
        else: req2 = req
        assert not req2.geturl().endswith('/login.xhtml'), "Login failed"
        self.base_url = req2.geturl().rsplit('/', 1)[0]
    @classmethod
    def _from_pickled(self, cookies, baseurl):
        import http.cookiejar
        x = http.cookiejar.CookieJar()
        for i in cookies: x.set_cookie(i)
        self = object.__new__(self)
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(x))
        self.base_url = baseurl
        return self
    def __reduce__(self):
        return (self._from_pickled, (list([i for i in self.opener.handlers if isinstance(i, urllib.request.HTTPCookieProcessor)][0].cookiejar), self.base_url))
    @staticmethod
    def get_view_state(data):
        return data.split('<input type="hidden" name="javax.faces.ViewState" id="', 1)[1].split('"', 3)[2]
    def contest_list(self):
        data = self.opener.open(self.base_url + '/contests.xhtml').read().decode('utf-8')
        names = list(map(html.unescape, (i.split('"', 1)[0] for i in data.split('<a href="#" title="')[1:])))
        return names, self.get_view_state(data)
    def select_contest(self, index, viewstate):
        self.opener.open(self.base_url + '/contests.xhtml', urllib.parse.urlencode({'j_idt25': 'j_idt25', 'j_idt25:j_idt26:%d:j_idt28'%index: 'j_idt25:j_idt26:%d:j_idt28'%index, 'javax.faces.ViewState': viewstate}).encode('ascii'))
    def get_info(self):
        data = self.opener.open(self.base_url + '/information.xhtml').read().decode('utf-8')
        props_s = data.split('<table class="properties">', 1)[1].split('</table>', 1)[0]
        keys = [] 
        values = []
        for i in props_s.split('<td class="key">')[1:]:
            keys.append(html.unescape(i.split('</td>', 1)[0]))
        for i in props_s.split('<td class="value">')[1:]:
            values.append(html.unescape(i.split('</td>', 1)[0]))
        props = dict(zip(keys, values))
        return props
    def get_messages(self):
        data = self.opener.open(self.base_url + '/information.xhtml').read().decode('utf-8')
        messages = []
        messages_s = data.split('<table class="messages list">', 1)[1].split('</table>', 1)[0]
        for i in messages_s.split('</td><td class="')[1:]:
            i = i.split('</td>', 1)[0]
            t, s = i.split('">', 1)
            messages.append((t, html.unescape(s)))
        return messages
    @staticmethod
    def get_list_content(prob):
        data = []
        for subm in prob.split('<tr class="')[1:]:
            subm = subm.split('</tr>', 1)[0]
            subm_d = {}
            data.append((subm.split('"', 1)[0], subm_d))
            for i in subm.split('<td ')[1:]:
                cls, dat = i.split('">', 1)
                try: cls = cls.split('class="', 1)[1].split('"', 1)[0]
                except IndexError: cls = None
                dat = html.unescape(dat.split('</td>', 1)[0])
                subm_d[cls] = dat
                try: del subm_d['pad']
                except KeyError: pass
        return data
    def get_submissions(self, filter=True):
        data = self.opener.open(self.base_url + '/runs.xhtml').read().decode('utf-8')
        try: runs_s = data.split('<table class="runs list">', 1)[1].split('</table>', 1)[0]
        except IndexError: runs_s = ''
        ans = {}
        for prob in runs_s.split('<tbody id="problem-')[1:]:
            prob = prob.split('</tbody>', 1)[0]
            ans[prob.split('"', 1)[0]] = data = [(i[4 if filter else 0:], j) for i, j in self.get_list_content(prob) if i.startswith('run ') or not filter]
            for i in data:
                subm_d = i[1]
                try: subm_d['source'] = urllib.parse.urljoin(self.base_url, subm_d['source'].split('"')[1])
                except KeyError: pass
        return ans
    def get_submit(self):
        data = self.opener.open(self.base_url + '/submit.xhtml').read().decode('utf-8')
        langs_s = data.split('<select id="submit:language" name="submit:language" class="w100" size="1">', 1)[1].split('</select>', 1)[0]
        langs = {}
        for i in langs_s.split('<option value="')[1:]:
            val, name = i.split('</option>', 1)[0].split('">', 1)
            val = val.split('"', 1)[0]
            name = html.unescape(name)
            if name.endswith('\u200e'):
                name = name[:-1]
            langs[val] = name
        probs = []
        for i in data.split('<div id="problem-')[1:]:
            prob, rest = i.split('"', 1)
            rest = rest.split('">', 1)[0]
#           if rest.endswith(' class="allowed'):
            probs.append(prob)
        jsonp = json.loads(data.split('<script type="text/javascript">submits.init(', 1)[1].split(');</script>', 1)[0])
        return (probs, langs, jsonp, self.get_view_state(data))
    def submit(self, task, lang, text, vs, ext='.txt'):
        data = []
        data.append(b'"submit"\r\n\r\nsubmit')
        data.append(b'"submit:problem"\r\n\r\n'+task.encode('utf-8'))
        data.append(b'"submit:language"\r\n\r\n'+str(lang).encode('utf-8'))
        data.append(b'"submit:file"; filename="brute'+ext.encode('utf-8')+b'"\r\nContent-Type'+
                    b': text/plain\r\n\r\n'+text)
        data.append(b'"submit:submitSolution"\r\n\r\nSubmit solution')
        data.append(b'"javax.faces.ViewState"\r\n\r\n'+vs.encode('utf-8'))
        import random
        while True:
            x = b'----------'+str(random.randrange(1, 1000000000)).encode('ascii')
            for i in data:
                if x in i: break
            else: break
        data = b'\r\n'.join(b'--'+x+b'\r\n'+b'Content-Disposition: form-data; name='+i for i in data)+b'\r\n--'+x+b'--\r\n'
#       print(data)
        assert self.opener.open(urllib.request.Request(self.base_url + '/submit.xhtml',
                                data=data,
                                headers={'Content-Type': 'multipart/form-data; boundary='+x.decode('ascii')},
                                method='POST')).geturl() == self.base_url + '/submitDone.xhtml'
    def get_protocol(self, task, attempt):
        req = self.opener.open(self.base_url+'/feedback.xhtml?'+urllib.parse.urlencode({'problem': task, 'attempt': attempt}))
        if req.geturl().endswith('/runs.xhtml'):
            return None
        data = req.read().decode('utf-8')
#       print(data)
        return self.get_list_content(data)
    def get_compile_error(self, task, attempt):
        data = self.opener.open(self.base_url+'/runs.xhtml').read().decode('utf-8')
        try: data = data.split('<tr id="ce-%s_%d" style="display: none"><td class="pad"></td><td colspan="7"><pre>'%(task, attempt), 1)[1].split('</pre>', 1)[0]
        except IndexError: return None
        return html.unescape(data)
    def get_source(self, task, attempt):
        req = self.opener.open(self.base_url+'/sources.xhtml?problem=%s&attempt=%d'%(task, attempt))
        if req.geturl().endswith('/runs.xhtml'):
            return None
        try: return html.unescape(req.read().split(b'<pre dir="ltr" ', 1)[1].split(b'>', 1)[1].split(b'</pre>', 1)[0].decode('latin-1')).encode('latin-1')
        except IndexError: return None

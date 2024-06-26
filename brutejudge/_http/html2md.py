import html, urllib.parse

def do_unescape(s, code=None):
    if code is not None: return html.unescape(s)
    return html.unescape(' '.join(('_'+s+'_').split()))[1:-1]

def validate_tag(data):
    data = data.strip()
    if data.startswith('/'): data = data[1:]
    if data.endswith('/'): data = data[:-1]
    i = 0
    while i < len(data):
        j = min(data.find("'", i) % (len(data) + 1), data.find('"', i) % (len(data) + 1))
        if not set(data[i:j]).issubset(set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789- =\n')):
            return False
        if j == len(data): return True
        i = j + 1
        j = data.find(data[j], j + 1) % (len(data) + 1)
        if j == len(data):
            return False
        i = j + 1
    return i == len(data)

def html2md(data, dload_prefix=None, base=None):
    data = ''.join(i.split('-->', 1)[1] for i in ('-->'+data).split('<!--')).split('<')
    ans = do_unescape(data[0])
    is_code = None
    hrefs = []
    prev = None
    for i in data[1:]:
        if i.startswith('a href="'):
            href, i = i[8:].split('">', 1)
            href = do_unescape(href.split('"', 1)[0], is_code)
            if base != None: href = urllib.parse.urljoin(base, href)
            if dload_prefix != None and href.startswith(dload_prefix):
                href = 'file '+href[len(dload_prefix):]
            hrefs.append(href)
            ans += '['+do_unescape(i, is_code)
        elif i.startswith('img '):
            x, i = i.split('>', 1)
            src = x.split('src="', 1)[1].split('"', 1)[0]
            src = do_unescape(src.split('"', 1)[0], is_code)
            if base != None: src = urllib.parse.urljoin(base, src)
            if dload_prefix != None and src.startswith(dload_prefix):
                src = 'file '+src[len(dload_prefix):]
            ans += '![]('+src+')'
        elif any(i.startswith('h%d>'%x) or i.startswith('h%d '%x) for x in range(1, 7)):
            d, i = i.split('>', 1)
            ans += '\n\n'+'#'*int(d[1])+' '+do_unescape(i, is_code)
        elif i.startswith('li>'):
            ans += '* ' + do_unescape(i[3:], is_code)
        elif i.startswith('div class="test-example-line ') and prev == '/div>': # codeforces
            assert ans.endswith('\n\n')
            ans = ans[:-1] + do_unescape(i.split('>', 1)[1], is_code)
        elif any(i.startswith(x) for x in ('br>', 'br/>', 'br />', '/h1>', '/h2>', '/h3>', '/h4>', '/h5>', '/h6>', '/p>', '/li>', '/div>')):
            ans += '\n\n' + do_unescape(i.split('>', 1)[1], is_code)
        elif i.startswith('/a>'):
            ans += ']('+hrefs.pop()+')'+do_unescape(i[3:], is_code)
        elif i.startswith('sub>') or i.startswith('sub '):
            ans += '[' + do_unescape(i.split('>', 1)[-1], is_code)
        elif i.startswith('/sub>'):
            ans += ']' + do_unescape(i.split('>', 1)[1], is_code)
        elif i.startswith('sup>') or i.startswith('sup '):
            ans += '**(' + do_unescape(i.split('>', 1)[-1], is_code)
        elif i.startswith('/sup>'):
            ans += ')' + do_unescape(i[5:], is_code)
        elif i.startswith('var>') or i.startswith('/var>'):
            ans += '$' + do_unescape(i.split('>', 1)[1], is_code)
        else:
            if i.startswith('/pre>'):
                if is_code == 'pre':
                    ans += '\n```'
                    is_code = None
            elif i.startswith('/code>'):
                if is_code == 'code':
                    ans += '`'
                    is_code = None
            elif i.startswith('pre>') or i.startswith('pre '):
                if is_code is None:
                    ans += '```\n'
                    is_code = 'pre'
            elif i.startswith('code>') or i.startswith('code '):
                if is_code is None:
                    ans += '`'
                    is_code = 'code'
            if (i.startswith('p>') or i.startswith('p ')) and ans and not ans.endswith('\n'):
                ans += '\n'
            if '>' not in i or not validate_tag(i.split('>', 1)[0]):
                ans += '<' + do_unescape(i, is_code)
            else:
                ans += do_unescape(i.split('>', 1)[-1], is_code)
        prev = i
    return '\n\n'.join(i for i in ans.split('\n\n') if i).replace('\n\n\n', '\n\n').strip()

def md2html(data):
    ans = []
    uldepth = 0
    for l in data.split('\n\n'):
        cur_uldepth = 0
        if set(l.split(' ', 1)[0]) == {'*'}:
            hdeep, l = l.split(' ', 1)
            cur_uldepth = len(hdeep)
        while uldepth < cur_uldepth:
            ans.append('<ul>')
            uldepth += 1
        while cur_uldepth < uldepth:
            ans.append('</ul>')
            uldepth -= 1
        l = l.replace('\n', ' ')
        fmt = '<p>%s</p>' if uldepth == 0 else '<li>%s</li>'
        if set(l.split(' ', 1)[0]) == {'#'}:
            hdeep, l = l.split(' ', 1)
            fmt = '<h%d>%%s</h%d>'%(len(hdeep), len(hdeep))
        l = l.split('[')
        ll = html.escape(l[0])
        for i in l[1:]:
            if ']' not in i:
                ll += html.escape(i)
                continue
            href, i = i.split(']', 1)
            text = href
            if i.startswith('(') and ')' in i:
                text, i = i[1:].split(')')
            ll += '<a href="'+html.escape(href)+'">'+html.escape(text)+'</a>'+html.escape(i)
        ans.append(fmt % ll)
    return '\n'.join(ans)

#function for collecting raw html data for debugging html2md
def monkeypatch():
    import hashlib, json
    global html2md
    old_html2md = html2md
    def html2md(data, *args, **kwds):
        h = hashlib.sha256(data.encode('utf-8')).hexdigest()
        with open('html2md-%s.in'%h, 'w') as file:
            file.write(data)
        with open('html2md-%s.args'%h, 'w') as file:
            file.write(json.dumps({'args': args, 'kwargs': kwds}))
        data = old_html2md(data, *args, **kwds)
        with open('html2md-%s.out'%h, 'w') as file:
            file.write(data)
        return data

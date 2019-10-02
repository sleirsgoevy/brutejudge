import urllib.request, urllib.parse, html, json, ssl
from ...error import BruteError

def parse_hidden_inputs(data):
    ans = {}
    for i in data.split('\n  <input ')[1:]:
        i = ' '+i.split('\n', 1)[0]
        if ' type="hidden" ' in i:
            name = i.split(' name="', 1)[1].split('"', 1)[0]
            value = i.split(' value="', 1)[1].split('"', 1)[0]
            ans[html.unescape(name)] = html.unescape(value)
    if 'bgresponse' in ans:
        ans['bgresponse'] = 'js_enabled'
    return ans

def do_oauth(email, password):
    ctx = ssl.create_default_context()
    x = urllib.request.build_opener(urllib.request.HTTPCookieProcessor, urllib.request.HTTPRedirectHandler, urllib.request.HTTPSHandler(context=ctx))
    data1 = x.open('https://accounts.google.com/o/oauth2/auth?redirect_uri=storagerelay%3A%2F%2Fhttps%2Fcodingcompetitions.withgoogle.com%3Fid%3Dauth459599&response_type=permission%20id_token&scope=email%20profile%20openid%20https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fcodejam&openid.realm=&client_id=786918852754-bprfsksl61u8t4iua13hkq56jpja9g2u.apps.googleusercontent.com&ss_domain=https%3A%2F%2Fcodingcompetitions.withgoogle.com&prompt=select_account&fetch_basic_profile=true&gsiwebsdk=2')
    data1 = data1.read().decode('utf-8', 'replace')
    data1 = parse_hidden_inputs(data1)
    data1['Email'] = email
    data2 = x.open('https://accounts.google.com/signin/v1/lookup', urllib.parse.urlencode(data1).encode('ascii'))
    data2 = data2.read().decode('utf-8', 'replace')
    data2 = parse_hidden_inputs(data2)
    data2['Email'] = email
    data2['Passwd'] = password
    data3 = x.open('https://accounts.google.com/multilogin/challenge/sl/password', urllib.parse.urlencode(data2).encode('ascii'))
    data3 = data3.read().decode('utf-8', 'replace')
    if '<span role="alert" class="error-msg" id="errormsg_0_Passwd">' in data3:
        raise BruteError("Login failed.")
    if '<img src="https://accounts.google.com/Captcha?' in data3:
        raise BruteError("Login failed: CAPTCHA received. Log in to GCJ using your web browser, then try again.")
    if '<button id="submit_approve_access" ' in data3:
        raise BruteError("Login failed: rights haven't been granted. Log in to GCJ using your web browser, then try again.")
    data4 = json.loads('{'+data3.split('lso.relayAuthResponse( ', 1)[1].split('{', 1)[1].rsplit(');</script>', 1)[0].rsplit('}', 1)[0]+'}')
#curl 'https://accounts.google.com/o/oauth2/iframerpc?action=issueToken&response_type=token%20id_token&login_hint=AJDLj6LJaXjplD11OecOt22tY_Tlr9x5xx7KVtECyntMGiQ1ovSeFwZ3tlhiSnD5UDm49mvfRC9tVxiuNRWi97jQrqnuOZ8Aa1p6U9HGJ9iBRG6VJvGwClU&client_id=786918852754-bprfsksl61u8t4iua13hkq56jpja9g2u.apps.googleusercontent.com&origin=https%3A%2F%2Fcodingcompetitions.withgoogle.com&scope=openid%20profile%20email%20https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fcodejam&ss_domain=https%3A%2F%2Fcodingcompetitions.withgoogle.com' -H 'X-Requested-With: XmlHttpRequest' -H 'Cookie: SID=lAfXdY0HfsLBLe-YXBoSWvZvoXXeqslGBFVfq9eD-E4RDVq100B3BYx_fV0HSldSeVaVlg.; LSID=ah|blogger|doritos|lso|mail|o.calendar.google.com|o.console.cloud.google.com|o.mail.google.com|o.myaccount.google.com|o.notifications.google.com|o.smartlock.google.com|o.takeout.google.com|s.RU|s.blogger|s.youtube|sitemaps|ss|urlshortener|wise|youtube:lAfXdezUGT-6s-fj7Y-y3EGoBlr9LaaBgVDIBB9x2g4CW21XHyrjvS4Ew-GZNYrF9F5SAQ.; HSID=AVYr8nELzElaznxtX; SSID=AvS_FHt-pndJPrbUt' -H 'Connection: keep-alive' -v; echo
    data5 = x.open(urllib.request.Request('https://accounts.google.com/o/oauth2/iframerpc?action=issueToken&response_type=token%20id_token&login_hint='+data4['login_hint']+'&client_id=786918852754-bprfsksl61u8t4iua13hkq56jpja9g2u.apps.googleusercontent.com&origin=https%3A%2F%2Fcodingcompetitions.withgoogle.com&scope=openid%20profile%20email%20https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fcodejam&ss_domain=https%3A%2F%2Fcodingcompetitions.withgoogle.com', headers={'X-Requested-With': 'XmlHttpRequest'}))
    data5 = json.loads(data5.read().decode('utf-8', 'replace'))
    return data5['access_token']

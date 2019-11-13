import subprocess, json, urllib.request
from ...error import BruteError

PHJS = r'''
var page = require('webpage').create();
page.open('https://accounts.google.com/o/oauth2/auth?redirect_uri=storagerelay%3A%2F%2Fhttps%2Fcodingcompetitions.withgoogle.com%3Fid%3Dauth459599&response_type=permission%20id_token&scope=email%20profile%20openid%20https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fcodejam&openid.realm=&client_id=786918852754-bprfsksl61u8t4iua13hkq56jpja9g2u.apps.googleusercontent.com&ss_domain=https%3A%2F%2Fcodingcompetitions.withgoogle.com&prompt=select_account&fetch_basic_profile=true&gsiwebsdk=2', function()
{
    page.evaluate(function()
    {
        document.getElementById('Email').value = EMAIL;
        document.getElementById('next').click();
    });
    var tout = setInterval(function()
    {
        var q = page.evaluate(function()
        {
            var elem = document.getElementById('errormsg_0_Email');
            if(elem && elem.innerHTML !== '')
                return "invalidEmail";
            var elem = document.getElementById('Passwd');
            if(elem)
            {
                elem.value = PASSWORD;
                document.getElementById('signIn').click();
                return true;
            }
            return false;
        });
        if(q === "invalidEmail")
        {
            console.log('"invalidEmail"');
            phantom.exit();
        }
        if(q)
        {
            clearInterval(tout);
            tout = setInterval(function()
            {
                var q = page.evaluate(function()
                {try{
                    if(document.location.href.substr(0, 42) === "https://accounts.google.com/o/oauth2/auth?" && document.documentElement.outerHTML.indexOf('var done = function() {window.close();}; lso.relayAuthResponse( ') >= 0)
                    {
                        var sp = document.documentElement.outerHTML.split('var done = function() {window.close();}; lso.relayAuthResponse( ');
                        sp.shift();
                        sp = sp.join('var done = function() {window.close();}; lso.relayAuthResponse( ').split(');</script>');
                        sp.pop();
                        sp = sp.join(');</script>').split('{');
                        sp[0] = '';
                        sp = sp.join('{').split('}');
                        sp[sp.length-1] = '';
                        sp = JSON.parse(sp.join('}'));
                        history.pushState({}, '', 'https://accounts.google.com/o/oauth2/iframe');
                        var xhr = new XMLHttpRequest();
                        xhr.open('GET', 'https://accounts.google.com/o/oauth2/iframerpc?action=issueToken&response_type=token%20id_token&login_hint='+sp['login_hint']+'&client_id=786918852754-bprfsksl61u8t4iua13hkq56jpja9g2u.apps.googleusercontent.com&origin=https%3A%2F%2Fcodingcompetitions.withgoogle.com&scope=openid%20profile%20email%20https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fcodejam&ss_domain=https%3A%2F%2Fcodingcompetitions.withgoogle.com', false);
                        xhr.setRequestHeader('X-Requested-With', 'XmlHttpRequest');
                        xhr.send('');
                        return xhr.responseText.split("\n").join(" ");
                    }
                    var elem = document.getElementById('errormsg_0_Passwd');
                    if(elem && elem.innerHTML !== '')
                        return '"invalidPassword"';
                    var elem = document.getElementById('submit_approve_access');
                    if(elem)
                        return '"noAccess"';
                    return "null";
                }catch(e){return ""+e;}});
                if(q !== "null")
                {
                    console.log(q);
                    clearInterval(tout);
                    phantom.exit();
                }
            }, 100);
        }
    }, 100);
});
'''

def do_oauth(email, password):
    phjs = PHJS.replace('EMAIL', json.dumps(email)).replace('PASSWORD', json.dumps(password))
    p = subprocess.Popen(('phantomjs', '/dev/stdin'), stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    res = json.loads(p.communicate(phjs.encode('utf-8'))[0].decode('utf-8', 'replace').split('\n', 1)[0])
    p.wait()
    if res == 'invalidEmail':
        raise BruteError("Login failed: invalid e-mail.")
    elif res == 'invalidPassword':
        raise BruteError("Login failed: invalid password.")
    elif res == 'noAccess':
        raise BruteError("Login failed: rights haven't been granted. Log in to GCJ using your web browser, then try again.")
    return res['access_token']

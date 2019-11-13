from .oauth_old import do_oauth as do_oauth_old
from .oauth_phjs import do_oauth as do_oauth_phjs

def do_oauth(url, email, password):
    if url.endswith('#oauth-old'):
        return do_oauth_old(email, password)
    return do_oauth_phjs(email, password)

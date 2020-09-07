import brutejudge.http, getpass, brutejudge.error

def do_passwd(self, cmd):
    """
    usage: passwd

    Change contest login password.
    """
    if cmd.strip():
        return self.do_help('passwd')
    oldpass = getpass.getpass('Old password: ')
    newpass = getpass.getpass('New password: ')
    newpass2 = getpass.getpass('Retype new password: ')
    if newpass != newpass2:
        raise brutejudge.error.BruteError('Passwords do not match!')
    brutejudge.http.change_password(self.url, self.cookie, oldpass, newpass)
    print('Password changed successfully, now relogin.')
    self.url = self.cookie = None

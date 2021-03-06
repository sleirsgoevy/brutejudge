import socket, threading, os, pty, tty, select, sys, shlex, subprocess, io, signal

mustexit = None

class UnbufferedStream(io.FileIO):
    def read1(self, x=-1): return self.read(x)

def readline(sock):
    ans = b''
    while not ans.endswith(b'\n'):
        try: chunk = sock.recv(1)
        except socket.error: return ''
        ans += chunk
        if chunk == b'': return ''
    return ans.decode('utf-8')[:-1]

def io_server_thread(sock, stdin, stdout, stderr, efd):
    try:
        fd_set = {sock.fileno(), stdout, stderr, efd}
        while True:
            l = select.select(list(fd_set), [], [])[0]
            if l == [efd]:
                sock.sendall(('exit %d\n'%os.read(efd, 1)[0]).encode('utf-8'))
                sock.close()
                break
            for i in l:
                if i == sock.fileno():
                    data = sock.recv(1048576, socket.MSG_PEEK)
                    if not data: fd_set.remove(i)
                    l = os.write(stdin, data)
                    sock.recv(l)
                    if os.isatty(stdin) and b'\3' in data[:l]: os.kill(os.getpid(), signal.SIGINT)
                elif i == stdout:
                    try: data = os.read(stdout, 1024)
                    except OSError: data = b''
                    if not data: fd_set.remove(i)
                    sock.sendall(('stdout %d\n'%len(data)).encode('utf-8')+data)
                elif i == stderr:
                    try: data = os.read(stderr, 1024)
                    except OSError: data = b''
                    if not data: fd_set.remove(i)
                    sock.sendall(('stderr %d\n'%len(data)).encode('utf-8')+data)
    except socket.error: pass
    finally:
        for i in {stdin, stdout, stderr, efd}: os.close(i)

tld_devtty = threading.local()

def io_server(brute, sock, auth_token, tty_conf):
    auth = readline(sock)
    if auth != auth_token:
        sock.close()
        return
    mode, command = readline(sock).split(' ', 1)
    if mode == 'pty':
        stdin, cstdin = pty.openpty()
        tty.tcsetattr(cstdin, tty.TCSAFLUSH, tty_conf)
        stdout = stderr = stdin
        cstdout = cstderr = cstdin
        tld_devtty.value = '/proc/self/fd/%d'%cstdin
    else:
        cstdin, stdin = os.pipe()
        stdout, cstdout = os.pipe()
        stderr, cstderr = os.pipe()
    command = eval(command)
    efd, efd_w = os.pipe()
    threading.Thread(target=io_server_thread, args=(sock, stdin, stdout, stderr, efd), daemon=True).start()
    if mode == 'pty':
        do_open = UnbufferedStream
    else:
        do_open = open
    cstdin_f = do_open(cstdin, 'rb', closefd=False)
    cstdout_f = do_open(cstdout, 'wb', closefd=False)
    cstderr_f = do_open(cstderr, 'wb', closefd=False)
    from brutejudge.hook_stdio import RedirectSTDIO
#   sys.stdin.buffer._tld.value = cstdin_f
#   sys.stdout.buffer._tld.value = cstdout_f
#   sys.stderr.buffer._tld.value = cstderr_f
    exitstatus = 0
    try:
        with RedirectSTDIO(cstdin_f, cstdout_f, cstderr_f):
            brute.onecmd(command)
    except SystemExit as e:
        if len(e.args) == 1 and isinstance(e.args[0], int):
            exitstatus = e.args[0]
        elif len(e.args) == 1:
            print(e.args[0], file=sys.stderr)
        else:
            print(e.args, file=sys.stderr)
    except:
        if mustexit != None: exit(mustexit)
        sys.excepthook(*sys.exc_info())
        exitstatus = 1
    finally:
#       sys.stdin.flush()
#       sys.stdout.flush()
#       sys.stderr.flush()
#       del sys.stdin.buffer._tld.value
#       del sys.stdout.buffer._tld.value
#       del sys.stderr.buffer._tld.value
        try: del tld_devtty.value
        except AttributeError: pass
        for i in {cstdin, cstdout, cstderr}: os.close(i)
    try:
        os.write(efd_w, bytes((exitstatus,)))
        os.close(efd_w)
    except OSError: pass

def io_server_main(brute, sock, auth_token):
    tty_conf = tty.tcgetattr(0)
    while True: io_server(brute, sock.accept()[0], auth_token, tty_conf)

def hook_stdio():
    import brutejudge.hook_stdio
    import os
    os_open = os.open
    def gp_open(file, *args, **kwds):
        if file == '/dev/tty' and hasattr(tld_devtty, 'value'):
            file = tld_devtty.value
        return os_open(file, *args, **kwds)
    os.open = gp_open

def start_io_server(brute, auth_token, zsh=False):
    import socket
    sock = socket.socket()
    sock.bind(('127.0.0.1', 0))
    sock.listen(1)
    threading.Thread(target=run_bash, args=(sock.getsockname(), auth_token, zsh), daemon=True).start()
    try: io_server_main(brute, sock, auth_token)
    except:
        if mustexit != None: exit(mustexit)
        raise

def run_bash(arg, auth_token, zsh=False):
    global mustexit
    port = arg[1]
    env = dict(os.environ)
    func_code = '() { python3 -m brutejudge.bashhelper %d %s "$@"; }'%(port, auth_token)
    print('bash integration enabled. Type `bj help` for help.')
    if zsh: # this sucks
        dotdir = env.get('ZDOTDIR', env['HOME'])
        import tempfile
        with tempfile.TemporaryDirectory() as dir:
            with open(dir+'/.zshrc', 'w') as file:
                file.write('source '+shlex.quote(dotdir+'/.zshrc')+'\n')
                file.write('command_not_found_handler '+func_code+'\n\n')
                file.write('bj '+func_code+'\n')
            env['ZDOTDIR'] = dir
            mustexit = subprocess.call('zsh', env=env)
    else:
        for i in ('BASH_FUNC_%s%%%%', 'BASH_FUNC_%s()', '%s'):
            env[i%'command_not_found_handle'] = env[i%'bj'] = func_code
        ppath = os.environ.get('PYTHONPATH', None)
        ppath = os.path.split(os.path.split(__file__)[0])[0]+(':'+ppath if ppath != None else '')
        env['PYTHONPATH'] = ppath
        mustexit = subprocess.call('bash', env=env)
    os.kill(os.getpid(), signal.SIGINT)

def io_client(port, auth_token, cmd):
    sock = socket.create_connection(('127.0.0.1', port))
    sock.sendall((auth_token+'\n').encode('utf-8'))
    if sys.stdin.isatty() and sys.stdout.isatty() and sys.stderr.isatty():
        mode = 'pty'
    else:
        mode = 'pipe'
    sock.sendall(('%s %r\n'%(mode, cmd)).encode('utf-8'))
    if mode == 'pty':
        old = tty.tcgetattr(0)
        tty.setraw(0)
    try:
        while True:
            for i in select.select([sys.stdin.fileno(), sock.fileno()], [], [])[0]:
                if i == sys.stdin.fileno():
                    sock.sendall(sys.stdin.buffer.raw.read(1048576))
                elif i == sock.fileno():
                    try: where, l = readline(sock).split()
                    except ValueError: break
                    l = int(l)
                    if where == 'exit':
                        sock.close()
                        exit(l)
                    data = b''
                    while len(data) < l: data += sock.recv(l - len(data))
                    if where == 'stdout': sys.stdout.buffer.raw.write(data)
                    else: sys.stderr.buffer.raw.write(data)
            else: continue
            break
    finally:
        if mode == 'pty':
            tty.tcsetattr(0, tty.TCSAFLUSH, old)

def smart_quote(x):
    if not (set(' \\\'\"\n') & set(x)): return x
    return shlex.quote(x)

def main():
    signal.signal(signal.SIGTTIN, signal.SIG_IGN)
    signal.signal(signal.SIGTTOU, signal.SIG_IGN)
    if len(sys.argv) == 1 or sys.argv[1] in ('--bash', '--zsh'):
        hook_stdio()
        import brutejudge.cmd
        brute = brutejudge.cmd.BruteCMD()
        auth_token = '%0128x'%int.from_bytes(os.urandom(64), 'big')
        start_io_server(brute, auth_token, zsh=(len(sys.argv) > 1 and sys.argv[1] == '--zsh'))
    else:
        io_client(int(sys.argv[1]), sys.argv[2], ' '.join(map(smart_quote, sys.argv[3:])))

if __name__ == '__main__':
    main()

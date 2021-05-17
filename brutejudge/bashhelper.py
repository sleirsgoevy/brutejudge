import socket, threading, os.path, pty, tty, select, sys, shlex, subprocess, io, signal, functools

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
        sock.sendall(('pid %d\n'%os.getpid()).encode('utf-8'))
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

def torsocks_workaround():
    lp = os.getenv('LD_PRELOAD')
    if lp == None or not any('torsocks' in os.path.basename(i) for i in lp.split(':')):
        return socket.socket.connect, 'no_torsocks'
    un = os.uname()
    arch = un.machine
    is_x86 = len(arch) == 4 and arch.startswith('i') and arch.endswith('86') and arch[1] in '3456'
    is_x86_64 = arch == 'x86_64'
    if un.sysname != 'Linux' or not (is_x86 or is_x86_64) or os.path.isdir('/system'):
        print('Running brutejudge --bash under torsocks is not supported on your system.')
        exit(1)
    import ctypes, mmap
    libc = ctypes.CDLL('libc.so.6')
    libc.mmap.restype = ctypes.POINTER(ctypes.c_char)
    libc.mmap.argtypes = (ctypes.c_void_p, ctypes.c_size_t, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_longlong)
    errno = ctypes.c_int.in_dll(libc, 'errno')
    ram = libc.mmap(None, 4096, mmap.PROT_READ|mmap.PROT_WRITE|4, mmap.MAP_PRIVATE|mmap.MAP_ANONYMOUS, -1, 0)
    if ctypes.cast(ram, ctypes.c_void_p).value == ctypes.c_void_p(-1).value:
        ctypes.pythonapi.PyErr_SetFromErrno(ctypes.py_object(OSError))
    if is_x86:
        # push ebx
        # mov eax, __NR_socketcall
        # mov ebx, [esp+8]
        # mov ecx, [esp+12]
        # int 0x80
        # pop ebx
        # ret
        for i, x in enumerate(b'\x53\xb8\x66\x00\x00\x00\x8b\x5c\x24\x08\x8b\x4c\x24\x0c\xcd\x80\x5b\xc3'): ram[i] = x
        _socketcall = ctypes.cast(ram, ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_int, ctypes.c_char_p))
        def socketcall(call, *args):
            param = b''
            for i in args:
                sz = ctypes.sizeof(i)
                ptr = ctypes.cast(ctypes.pointer(i), ctypes.POINTER(ctypes.c_char*sz))
                data = ptr[0][:]
                data += bytes(ctypes.sizeof(ctypes.c_long) - len(data))
                param += data
            return _socketcall(call, param)
        def _connect(fd, addr, sz):
            return socketcall(3, ctypes.c_int(fd), ctypes.c_char_p(addr), ctypes.c_size_t(sz))
    elif is_x86_64:
        # mov eax, __NR_connect
        # syscall
        # ret
        for i, x in enumerate(b'\xb8\x2a\x00\x00\x00\x0f\x05\xc3'): ram[i] = x
        _connect = ctypes.cast(ram, ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_int, ctypes.c_char_p, ctypes.c_size_t))
    else: assert False
    def connect(sock, addr):
        fd = sock.fileno()
        host, port = addr
        host = socket.inet_aton(host)
        port = port.to_bytes(2, 'big')
        addr = socket.AF_INET.to_bytes(2, 'little') + port + host
        addr += bytes(16 - len(addr))
        ans = _connect(fd, addr, len(addr))
        if ans < 0:
            errno.value = -ans
            ctypes.pythonapi.PyErr_SetFromErrno(ctypes.py_object(socket.error))
    return connect, 'torsocks'

sock_connect, torsocks_type = torsocks_workaround()

def io_server(brute, sock, auth_token, tty_conf):
    auth = readline(sock)
    if auth.count(':') != 1:
        sock.close()
        return
    ts_type, auth = auth.split(':')
    if auth != auth_token:
        sock.close()
        return
    if ts_type != torsocks_type:
        msg = b'Run the whole brutejudge session under torsocks!\r\n'
        sock.sendall(('stdout %d\n'%len(msg)).encode('ascii')+msg+b'exit \0')
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
        if isinstance(brute, ForkingBrute): #we're in fork
            raise
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
    ppath = os.environ.get('PYTHONPATH', None)
    ppath = os.path.split(os.path.split(__file__)[0])[0]+(':'+ppath if ppath != None else '')
    env['PYTHONPATH'] = ppath
    func_code = '() { python3 -m brutejudge.bashhelper %d %s "$@"; }'%(port, auth_token)
    print('bash integration enabled. Type `bj help` for help.')
    import tempfile
    if zsh:
        dotdir = env.get('ZDOTDIR', env['HOME'])
        with tempfile.TemporaryDirectory() as dir:
            with open(dir+'/.zshrc', 'w') as file:
                file.write('source '+shlex.quote(dotdir+'/.zshrc')+'\n')
                file.write('command_not_found_handler '+func_code+'\n\n')
                file.write('bj '+func_code+'\n')
            env['ZDOTDIR'] = dir
            mustexit = subprocess.call('zsh', env=env)
    else:
        with tempfile.NamedTemporaryFile(mode='w') as file:
            file.write('source '+shlex.quote(env['HOME']+'/.bashrc')+'\n')
            file.write('command_not_found_handle '+func_code+'\n\n')
            file.write('bj '+func_code+'\n')
            file.flush()
            mustexit = subprocess.call(('bash', '--rcfile', file.name), env=env)
    os.kill(os.getpid(), signal.SIGINT)

def io_client(port, auth_token, cmd):
    sock = socket.socket()
    sock_connect(sock, ('127.0.0.1', port))
    sock.sendall((torsocks_type+':'+auth_token+'\n').encode('utf-8'))
    if sys.stdin.isatty() and sys.stdout.isatty() and sys.stderr.isatty():
        mode = 'pty'
    else:
        mode = 'pipe'
    sock.sendall(('%s %r\n'%(mode, cmd)).encode('utf-8'))
    if mode == 'pty':
        old = tty.tcgetattr(0)
        tty.setraw(0)
    try:
        pid = None
        have_int = [False, False]
        def handler(*args):
            if have_int[1]:
                have_int[1] = False
                raise KeyboardInterrupt
            have_int[0] = True
        signal.signal(signal.SIGINT, handler)
        while True:
            try:
                have_int[1] = True
                if have_int[0]:
                    have_int[0] = False
                    have_int[1] = False
                    raise KeyboardInterrupt
                r = select.select([sys.stdin.fileno(), sock.fileno()], [], [])[0]
                have_int[1] = False
            except KeyboardInterrupt:
                if pid == None: raise
                os.kill(pid, signal.SIGINT)
            for i in r:
                if i == sys.stdin.fileno():
                    sock.sendall(sys.stdin.buffer.raw.read(1048576))
                elif i == sock.fileno():
                    try: where, l = readline(sock).split()
                    except ValueError: break
                    l = int(l)
                    if where == 'exit':
                        sock.close()
                        exit(l)
                    elif where == 'pid':
                        pid = l
                        continue
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

class ForkingBrute:
    def __init__(self):
        import pickle
        self.brute = pickle.dumps(None)
        self.unpickle_failed = False
        self.execute(self.init)
        if self.brute == pickle.dumps(None):
            raise RuntimeError("ForkingBrute failed to initialize")
    def init(self):
        import brutejudge.cmd
        self.brute = brutejudge.cmd.BruteCMD()
        self.brute.stdin = self.brute.stdout = None
    def do_onecmd(self, cmd):
        self.brute.stdin = sys.stdin
        self.brute.stdout = sys.stdout
        self.brute.onecmd(cmd)
        self.brute.stdin = self.brute.stdout = None
    def execute(self, fn, *args):
        import pickle
        pipe = os.pipe()
        pid = os.fork()
        if not pid:
            try:
                os.close(pipe[0])
                try: self.brute = pickle.loads(self.brute)
                except:
                    self.unpickle_failed = True
                    raise
                fn(*args)
                with open(pipe[1], 'wb') as file: file.write(pickle.dumps(self.brute))
                sys.exit(0)
            except SystemExit: raise
            except BaseException:
                sys.excepthook(*sys.exc_info())
                with open(pipe[1], 'wb') as file: file.write(self.brute if self.unpickle_failed else pickle.dumps(self.brute))
                sys.exit(1)
        os.close(pipe[1])
        os.waitpid(pid, 0)
        with open(pipe[0], 'rb') as file: self.brute = file.read()
    def onecmd(self, cmd):
        self.execute(self.do_onecmd, cmd)

def main():
    signal.signal(signal.SIGTTIN, signal.SIG_IGN)
    signal.signal(signal.SIGTTOU, signal.SIG_IGN)
    if len(sys.argv) == 1 or sys.argv[1] in ('--bash', '--zsh'):
        hook_stdio()
        if 'BJ_PICKLE' in os.environ:
            brute = ForkingBrute()
        else:
            import brutejudge.cmd
            brute = brutejudge.cmd.BruteCMD()
        auth_token = '%0128x'%int.from_bytes(os.urandom(64), 'big')
        start_io_server(brute, auth_token, zsh=(len(sys.argv) > 1 and sys.argv[1] == '--zsh'))
    else:
        io_client(int(sys.argv[1]), sys.argv[2], ' '.join(map(smart_quote, sys.argv[3:])))

if __name__ == '__main__':
    main()

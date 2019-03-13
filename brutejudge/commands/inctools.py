import brutejudge.cheats, io, base64, gzip, shlex, sys, os.path, ast
from brutejudge.commands.incat import incat, base64_filter
from brutejudge.http import task_list, task_ids
from brutejudge.http.ejudge import Ejudge
from brutejudge.error import BruteError

def easy_incat(self, task, filepath, custom_include=None, binary=True):
    try: task_id = task_list(self.url, self.cookie).index(task)
    except ValueError: raise BruteError("No such task.")
    x = io.StringIO()
    incat(self, task, task_id, filepath, x, filter=(base64_filter if binary else ''), custom_include=custom_include)
    x.seek(0)
    ans = x.read()
    if binary: ans = base64.b64decode(ans.encode('ascii'))
    return ans

def easy_incat_multiple(self, task, filepaths):
    if not filepaths: return []
    separator = os.urandom(64)
    xsep = '\\"'+''.join('\\\\x%02x'%i for i in separator)+'\\"'
    custom_include = ('.ascii '+xsep+'\\n.incbin \\"%s\\"\\n')*len(filepaths)
    try: data = easy_incat(self, task, tuple(filepaths), custom_include)
    except: return None
    if data.count(separator) != len(filepaths):
        raise BruteError("You're 2**-512 unlucky!")
    assert data.startswith(separator)
    return data.split(separator)[1:]

def format_solution_id(x):
    alphabet = "0123456789ABCDEFGHIJKLMNOPQRSTUV"
    return '%s/%s/%s/%06d'%(alphabet[(x // 32768) % 32], alphabet[(x // 1024) % 32], alphabet[(x // 32) % 32], x)

def fetch_solution(self, task, i, j):
    return easy_incat(self, task, '/home/judges/%06d/var/archive/runs/%s'%(i, format_solution_id(j)))

def fetch_protocol(self, task, i, j):
    try:
        return easy_incat(self, task, '/home/judges/%06d/var/archive/xmlreports/%s'%(i, format_solution_id(j)))
    except BruteError:
        return gzip.decompress(easy_incat(self, task, '/home/judges/%06d/var/archive/xmlreports/%s.gz'%(i, format_solution_id(j))))

import html.parser

class TestsParser(html.parser.HTMLParser):
    def __init__(self):
        html.parser.HTMLParser.__init__(self)
        self.global_meta = {}
        self.test_meta = []
        self.metadata_dict = self.global_meta
        self.metadata_key = None
    def handle_starttag(self, tag, attrs):
        if tag == 'testing-report':
            self.global_meta.update(dict(attrs))
        elif tag == 'tests': pass
        elif tag == 'test':
            self.test_meta.append(dict(attrs))
            self.metadata_dict = self.test_meta[-1]
        else:
            self.metadata_key = tag
    def handle_startendtag(self, tag, attrs): pass
    def handle_data(self, data):
        if self.metadata_key is not None:
            self.metadata_dict[self.metadata_key] = self.metadata_dict.get(self.metadata_key, '')+data
    def handle_endtag(self, tag):
        self.metadata_key = None
        if tag == 'test':
            self.metadata_dict = self.global_meta

def get_tests(self, task, i, j):
    proto = fetch_protocol(self, task, i, j).decode('utf-8', 'replace')
    parser = TestsParser()
    parser.feed(proto.split('\n', 2)[-1])
    parser.close()
    tests = []
    for i in parser.test_meta:
        meta = {}
        files = {}
        for k, v in i.items():
            if k == 'checker-comment': k = 'checker'
            if k in ('input', 'output', 'stderr', 'correct', 'checker'):
                files[k] = v
            else:
                meta[k] = v
        tests.append((meta, files))
    compiler_output = parser.global_meta.get('compiler_output', '')
    try: del parser.global_meta['compiler_output']
    except KeyError: pass
    return (compiler_output, parser.global_meta, tests)

def format_meta(m):
    ans = ''
    for k, v in m.items():
        k = k.strip()
        v = v.strip()
        if '\n' in v:
            ans += k+':\n'+v+'\n\n'
        else:
            ans += k+': '+v+'\n'
    return ans

def dump_tests(self, path, task, i, j):
    cout, global_meta, tests = get_tests(self, task, i, j)
    os.makedirs(path)
    with open(os.path.join(path, 'meta.txt'), 'w') as file:
        file.write(format_meta(global_meta))
    with open(os.path.join(path, 'compiler.log'), 'w') as file:
        file.write(cout)
    for i, (meta, files) in enumerate(tests):
        with open(os.path.join(path, '%02d.meta'%(i + 1)), 'w') as file:
            file.write(format_meta(meta))
        for k, v in files.items():
            with open(os.path.join(path, '%02d%s'%(i + 1, {'input': '', 'correct': '.a'}.get(k, '.'+k))), 'w') as file:
                file.write(v)

def dump_contest(self, path, task, contest_id, options):
    os.makedirs(path)
    print('Fetching serve.cfg...')
    serve_cfg = easy_incat(self, task, '/home/judges/%06d/conf/serve.cfg'%contest_id)
    serve_cfg_lines = [i.split('#', 1)[0].strip() for i in serve_cfg.decode('utf-8', 'replace').split('\n')]
    serve_cfg_fmt = '\n'+'\n'.join(serve_cfg_lines)+'\n'
    if '\nadvanced_layout\n' in serve_cfg_fmt:
        tests_path = 'problems/%s/tests'
        checker_path = 'problems/%s/check'
        statement_path = 'problems/%s/statement.xml'
        attachment_path = 'problems/%s/attachments/%s'
    else:
        tests_path = 'tests/%s'
        checker_path = 'checkers/check_%s'
        statement_path = 'statements/%s.xml'
        attachment_path = 'attachments/%s/%s'
    problems = {}
    for i in serve_cfg_fmt.split('\n[problem]\n')[1:]:
        data = {}
        for j in i.split('\n'):
            if not j: continue
            if j == '['+j[1:-1]+']': break
            if '=' not in j: 
                data[j] = None
            else:
                j1, j2 = j.split('=', 1)
                data[j1.strip()] = j2.strip()
        try:
            short_name = ast.literal_eval(data.get('short_name', 'None'))
        except:
            short_name = None
        if short_name != None:
            problems[short_name] = data
    def get_task_param(name, key, default=None, do_eval=False):
        if name not in problems: return default
        if key in problems[name]:
            ans = problems[name][key]
            if do_eval:
                try: ans = ast.literal_eval(ans)
                except: ans = default
            return ans
        if 'super' in problems[name]:
            try:
                super_task = ast.literal_eval(problems[name]['super'])
            except: return default
            else:
                try: return get_task_param(super_task, key, default=default, do_eval=do_eval)
                except RuntimeError: return default
        return default
    def dump_file(p, d):
        p = os.path.join(path, p.replace('/', os.path.sep))
        os.makedirs(p)
        os.rmdir(p)
        with open(p, 'wb' if isinstance(d, bytes) else 'w') as file:
            file.write(d)
    dump_file('conf/serve.cfg', serve_cfg)
    if '--tests' in options:
        def do_dump_tests(k, low, high, pat):
            paths = [tests_path % k + '/' + pat % i for i in range(low, high)]
            data = easy_incat_multiple(self, task, ['/home/judges/%06d/%s'%(contest_id, i) for i in paths])
            if data == None: return False
            for k, v in zip(paths, data):
                dump_file(k, v)
            return True
        for k, v in problems.items():
            if 'abstract' not in v:
                print('Fetching tests for task %s...'%k)
                test_pat = get_task_param(k, 'test_pat', '%03d' + get_task_param(k, 'test_sfx', '', do_eval=True), do_eval=True)
                corr_pat = get_task_param(k, 'corr_pat', '%03d' + get_task_param(k, 'corr_sfx', '', do_eval=True), do_eval=True)
                low = 1
                high = 2
                while do_dump_tests(k, low, high, test_pat):
                    low = high
                    print(low - 1, 'tests dumped...')
                    high *= 2
                while high - low > 1:
                    mid = (high + low) // 2
                    if do_dump_tests(k, low, mid, test_pat):
                        low = mid
                        print(low - 1, 'tests dumped...')
                    else:
                        high = mid
                do_dump_tests(k, 1, low, corr_pat)
                if low == 1:
                    print('Warning: task', k, 'has no tests!')
                else:
                    print(low - 1, 'tests dumped.')
    if '--statements' in options or '--attachments' in options:
        for k, v in problems.items():
            if 'abstract' not in v:
                print('Fetching statements for task %s...'%k)
                try: data = easy_incat(self, task, '/home/judges/%06d/%s'%(contest_id, statement_path % k))
                except: print('Note: task ', k, 'has no statements.')
                else:
                    attachments = set()
                    for i in data.decode('latin-1').split('${getfile}=')[1:]:
                        i = i.split('"', 1)[0]
                        attachments.add(i)
                    dump_file(statement_path % k, data)
                    if '--attachments' in options:
                        for i in attachments:
                            print('Fetching attachment %s for task %s...'%(i, k))
                            try: attachment = easy_incat(self, task, '/home/judges/%06d/%s'%(contest_id, attachment_path % (k, i)))
                            except: print('Warning: failed downloading', i)
                            else: dump_file(attachment_path % (k, i), attachment)
    if '--checkers' in options or '--binary-checkers' in options:
        for k, v in problems.items():
            if 'abstract' not in v and get_task_param(k, 'standard_checker', do_eval=True) == None:
                print('Fetching checker for task %s...'%k)
                data = None
                try: data = easy_incat(self, task, '/home/judges/%06d/%s.cpp'%(contest_id, checker_path % k))
                except:
                    if '--binary-checkers' in options:
                        print('Warning: task %s: falling back to binary checker'%k)
                        try: data = easy_incat(self, task, '/home/judges/%06d/%s'%(contest_id, checker_path % k))
                        except: print('Warning: task', k, 'has no checker!')
                        else: dump_file(checker_path % k, data)
                else: dump_file(checker_path % k + '.cpp', data)

def do_inctools(self, cmd):
    """
    usage: inctools [--dump-path <path>] <task> <command> [args]

    `command` can be one of:
        submission <subm_id>
        Dump source code of a submission.

        protocol <subm_id>
        Dump full testing protocol for a submission.

        --dump-path <path> <task> dump-tests <subm_id>
        Dump tests from the protocol to the directory specified.

        --dump-path <path> <task> dump-contest [options] <contest_id>
        Dump contest to the directory specified.
        Supported options:
            --tests
            Dump tests.

            --statements
            Dump statements.

            --attachments
            Dump statement attachments (PDF statements/embedded images).
            (implies --statements)

            --checkers
            Dump checkers' source code.

            --binary-checkers
            Dump checker binaries if source code is not available.
            If the source is available, binaries won't be dumped.
            (implies --checkers)

            --all
            Dump everything of the above.
    """
    brutejudge.cheats.cheating(self)
    cmd = shlex.split(cmd)
    if not cmd:
        return self.do_help('inctools')
    if not isinstance(self.url, Ejudge):
        raise BruteError("inctools only work on ejudge.")
    dump_path = None
    if len(cmd) > 1 and cmd[0] == '--dump-path':
        dump_path = cmd[1]
        del cmd[:2]
    if len(cmd) < 3:
        return self.do_help('inctools')
    task = cmd[0]
    contest_id = self.url.contest_id
    if cmd[1] in ('submission', 'protocol'):
        if len(cmd) != 3:
            return self.do_help('inctools')
        if not cmd[2].isnumeric():
            raise BruteError("subm_id must be a number")
        subm_id = int(cmd[2])
        data = (fetch_solution if cmd[0] == 'submission' else fetch_protocol)(self, task, contest_id, subm_id)
        if dump_path == None:
            sys.stdout.buffer.raw.write(data)
        else:
            with open(dump_path, 'wb') as file: file.write(data)
    elif cmd[1] == 'dump-tests':
        if len(cmd) != 3:
            return self.do_help('inctools')
        if not cmd[2].isnumeric():
            raise BruteError("subm_id must be a number")
        subm_id = int(cmd[2])
        if dump_path == None:
            raise BruteError("dump-tests requires dump-path to work.")
        dump_tests(self, dump_path, task, contest_id, subm_id)
    elif cmd[1] == 'dump-contest':
        options = set()
        while len(cmd) >= 3 and cmd[2].startswith('--'):
            options.add(cmd[2])
            del cmd[2]
        if len(cmd) != 3 or not options.issubset({"--all", "--tests", "--statements", "--attachments", "--checkers", "--binary-checkers"}):
            return self.do_help('inctools')
        if "--all" in options:
            options = {"--tests", "--statements", "--attachments", "--checkers", "--binary-checkers"}
        if not cmd[2].isnumeric():
            raise BruteError("contest_id must be a number")
        tgt_id = int(cmd[2])
        if dump_path == None:
            raise BruteError("dump-contest requires dump-path to work.")
        dump_contest(self, dump_path, task, tgt_id, options)
    else:
        return self.do_help('inctools')

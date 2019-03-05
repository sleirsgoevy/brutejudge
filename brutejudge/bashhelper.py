import brutejudge.cmd, os, pickle, sys, shlex

try: data = pickle.loads(bytes.fromhex(os.environ.get('BJ_PICKLED')))
except: data = (None, None, False)

cmd = brutejudge.cmd.BruteCMD()
cmd._url, cmd._cookie = data[:2]
if data[2]: cmd.no_cheats = True

def my_quote(i):
    if set(i) & set('\'" \n\t'):
        return shlex.quote(i)
    return i

cmd.onecmd(' '.join(map(my_quote, sys.argv[1:])))

data2 = pickle.dumps((cmd._url, cmd._cookie, hasattr(cmd, 'no_cheats'))).hex()

try:
    with open(3, 'w') as file: file.write(data2)
except IOError: pass

import brutejudge.cmd, os, pickle, sys

try: data = pickle.loads(bytes.fromhex(os.environ.get('BJ_PICKLED')))
except: data = (None, None)

cmd = brutejudge.cmd.BruteCMD()
cmd._url, cmd._cookie = data

def my_quote(i):
    if set(i) & set('\'" \n\t'):
        return shlex.quote(i)
    return i

cmd.onecmd(' '.join(map(my_quote, sys.argv[1:])))

data2 = pickle.dumps((cmd._url, cmd._cookie)).hex()

try:
    with open(3, 'w') as file: file.write(data2)
except IOError: pass

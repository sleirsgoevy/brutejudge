from brutejudge.commands.incat import incat
from brutejudge.http import task_list
import io, shlex

def do_ingrep(self, cmd):
    cmd = shlex.split(cmd)
    if len(cmd) != 3:
        return self.do_help('ingrep')
    task, pattern, file = cmd
    tasks = task_list(self.url, self.cookie)
    try:
        task_id = tasks.index(task)
    except ValueError:
        raise BruteError("No such task.")
    out = io.StringIO()
    incat(self, task, task_id, file, out, '''\
istringstream sin(included_s);
string s2;
string l;
while (getline(sin, l))
{
    if (l.find("'''+pattern.replace('\\', '\\\\').replace('"', '\\"')+'''") != l.npos)
    {
        s2 += l;
        s2 += '\\n';
    }
}
included_s = s2;
''')
    print(out.getvalue())

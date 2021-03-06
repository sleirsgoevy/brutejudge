import sys

if '--bash' in sys.argv or '--zsh' in sys.argv:
    import brutejudge.bashhelper
    brutejudge.bashhelper.main()
    exit(0)

from brutejudge.cmd import BruteCMD
import cmd, builtins

def input(prompt = ''):
    while True:
        try: return builtins.input(prompt)
        except KeyboardInterrupt: pass

cmd.input = input

print('Type `help` for help.')
print('TIP: use `brutejudge --bash` or `brutejudge --zsh` to integrate brutejudge into your shell')
BruteCMD().cmdloop()

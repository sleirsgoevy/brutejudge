from brutejudge.cmd import BruteCMD
import cmd, builtins

def input(prompt = ''):
    while True:
        try: return builtins.input(prompt)
        except KeyboardInterrupt: pass

cmd.input = input

BruteCMD().cmdloop()

from brutejudge.commands.asubmit import do_asubmit

def do_aformat(self, cmd):
    """
    usage: aformat [-x <extension>] <file>

    Prints a style-fixed version of <file> to standard output.
    Uses a specific style fixer if -x is specified.
    """
    do_asubmit(self, cmd, afmt=True)

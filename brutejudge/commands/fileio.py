def do_fileio(self, cmd):
    """
    usage: fileio <input> <output>

    Forces the brute to use file IO.
    """
    sp = cmd.split()
    if len(sp) != 2:
        return self.do_help('fileio')
    self.input_file, self.output_file = sp

from .format_cpp import read_file, format as _format

def format(code, options=set()):
    return _format(code, options, cplusplus=False)

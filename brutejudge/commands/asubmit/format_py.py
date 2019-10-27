import sys

def read_file(path, options=set()):
    with open(path) as file: return file.read()

def format(orig, options=set()):
    data = orig.split('\n')
    i = 0
    while i < len(data):
        if (data[i].strip().startswith("def ") or data[i].strip().startswith("class ")) and data[i - 1:i] != ['']:
            data.insert(i, '')
        if (data[i].startswith("def ") or data[i].startswith("class ")) and data[i - 2:i] != ['', '']:
            data.insert(i, '')
        i += 1
    while data[:1] == ['']: del data[0]
    data = '\n'.join(data)
    return data

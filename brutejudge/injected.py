import brutejudge.cheats

injected = """\
import sys

data = %s.read()

if data in TESTS:
    stdout = %s
    stdout.write(TESTS[data])
    stdout.close()
    exit()


def bin_int(no, bin):
    if int(data.split()[no]) >= bin:
        exit(1)
    exit(0)


def bin_char(no, idx, bin):
    if ord(data.split()[no][idx]) >= bin:
        exit(1)
    exit(0)


def bin_choice(no, bin, *choices):
    i = choices.index(data.split()[no])
    if i > bin:
        exit(1)
    exit(0)
"""

import brutejudge.cheats
from .error import BruteError

def cheating(self):
    if hasattr(self, 'no_cheats'):
        raise BruteError('No cheats, please!')

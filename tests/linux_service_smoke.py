"""CI-only fake SDK. Never connects to a Royal Render server."""
from pathlib import Path
import sys

root = Path(sys.argv[1])
native = root / 'bin/lx64/lib'
native.mkdir(parents=True)
(native / f'libpyRR{sys.version_info.major}{sys.version_info.minor}.so').touch()
sdk = root / 'SDK/External/Python/rr_python_utils'
sdk.mkdir(parents=True)
(sdk / '__init__.py').touch()
(sdk / 'load_rrlib.py').write_text('''
from types import SimpleNamespace as NS
class TCP:
    def __init__(self, *args):
        self.clients = NS(count=lambda: 0)
        self.jobs = NS(getMaxJobsFiltered=lambda: 0)
    def setServer(self, *args): return True
    def connectAndAuthorize(self): return True
    def clientGetList(self): return True
    def clientGetGroups(self): return NS(count=0)
    def jobList_GetInfo(self): return True
rrLib = NS(_rrTCP=TCP)
''', encoding='utf-8')

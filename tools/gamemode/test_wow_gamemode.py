import os
from unittest.mock import patch
import tempfile
import unittest
from pathlib import Path
from wow_gamemode import Supervisor, discover


class API:
    def __init__(self, status=1):
        self.value, self.starts, self.ends = status, [], []

    def requester(self, pid):
        return os.getpid()

    def status(self, pid):
        return self.value

    def start(self, pid):
        self.starts.append(pid)
        self.value = 2
        return 0

    def end(self, pid):
        self.ends.append(pid)
        self.value = 1
        return 0


class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.p = self.root / '42'
        self.p.mkdir()
        self.born('100')
        (self.p/'comm').write_text('WoW.exe\n')
        (self.p/'environ').write_bytes(b'PROTONPATH=/r/ErgenProton-WoW-0.1.0\0UMU_ID=umu-wow\0')
        self.api = API()
        self.s = Supervisor(self.api, self.root)

    def born(self, value):
        (self.p/'stat').write_text('42 (WoW.exe) ' + ' '.join(['0']*19 + [value]))

    def test_register_once_and_release(self):
        self.s.tick(discover(self.root)); self.s.tick(discover(self.root))
        self.assertEqual(self.api.starts, [42])
        self.s.close()
        self.assertEqual(self.api.ends, [42])

    def test_preserve_external_registration(self):
        self.api.value = 2
        self.s.tick(discover(self.root)); self.s.close()
        self.assertEqual(self.api.starts + self.api.ends, [])

    def test_reused_pid_not_unregistered(self):
        self.s.tick(discover(self.root)); self.born('200'); self.s.close()
        self.assertEqual(self.api.ends, [])

    def test_foreign_runner_ignored(self):
        (self.p/'environ').write_bytes(b'PROTONPATH=/r/GE-Proton11-7\0UMU_ID=umu-wow\0')
        self.assertEqual(discover(self.root), {})

    def test_launcher_ignored(self):
        (self.p/'comm').write_text('Battle.net.exe')
        self.assertEqual(discover(self.root), {})

    def test_daemon_restart(self):
        self.s.tick(discover(self.root)); self.api.value = 0
        self.s.tick(discover(self.root))
        self.assertEqual(self.api.starts, [42, 42])

    def test_query_failure(self):
        self.api.value = -1
        with self.assertRaises(RuntimeError):
            self.s.tick(discover(self.root))
        self.assertEqual(self.api.starts, [])

    def test_temporary_missing_scan_retains_registration(self):
        self.s.tick(discover(self.root))
        self.s.tick({})
        self.assertEqual(self.s.owned, {42: '100'})
        self.assertEqual(self.api.ends, [])

    def test_exit_releases_tracking(self):
        self.s.tick(discover(self.root))
        (self.p/'stat').unlink()
        self.s.tick({})
        self.assertEqual(self.s.owned, {})
        self.assertEqual(self.api.ends, [])

    def test_registration_rejection_is_reported(self):
        self.api.start = lambda pid: -2
        with self.assertRaises(RuntimeError):
            self.s.tick(discover(self.root))
        self.assertEqual(self.s.owned, {})

    def test_foreign_registration_after_daemon_restart_not_removed(self):
        self.s.tick(discover(self.root))
        self.api.requester = lambda pid: os.getpid() + 1
        self.s.close()
        self.assertEqual(self.api.ends, [])

    def test_unknown_requester_not_removed(self):
        self.s.tick(discover(self.root))
        self.api.requester = lambda pid: None
        self.s.close()
        self.assertEqual(self.api.ends, [])

    def test_transient_identity_failure_preserves_tracking(self):
        self.s.tick(discover(self.root))
        with patch('wow_gamemode.identity', side_effect=PermissionError):
            self.s.tick({})
            self.assertEqual(self.s.owned, {42: '100'})
        self.s.close()
        self.assertEqual(self.api.ends, [42])

    def test_multiple_games(self):
        import shutil
        shutil.copytree(self.p, self.root/'43')
        # This mock models per-PID registrations, not global active state.
        active = set()
        self.api.status = lambda pid: 2 if pid in active else 1
        self.api.start = lambda pid: (active.add(pid), 0)[1]
        self.api.end = lambda pid: (active.discard(pid), 0)[1]
        self.s.tick(discover(self.root))
        self.assertEqual(active, {42, 43})
        self.s.close()
        self.assertEqual(active, set())


if __name__ == '__main__':
    unittest.main()

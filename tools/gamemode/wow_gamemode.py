#!/usr/bin/env python3
"""Host-side GameMode supervisor. Never changes affinity or thread priorities itself."""
import argparse
import ctypes
import fcntl
import json
import os
from pathlib import Path
import signal
import subprocess
import time


class GameMode:
    def __init__(self):
        self.lib = ctypes.CDLL('libgamemode.so.0')
        for name in ('query_status_for', 'request_start_for', 'request_end_for'):
            fn = getattr(self.lib, 'real_gamemode_' + name)
            fn.argtypes = [ctypes.c_int]
            fn.restype = ctypes.c_int

    def status(self, pid):
        return self.lib.real_gamemode_query_status_for(pid)

    def start(self, pid):
        return self.lib.real_gamemode_request_start_for(pid)

    def end(self, pid):
        return self.lib.real_gamemode_request_end_for(pid)

    def requester(self, pid):
        """Return the registering process, or None when ownership is unknown."""
        try:
            result = subprocess.run([
                'busctl', '--user', '--timeout=2', 'get-property',
                'com.feralinteractive.GameMode',
                f'/com/feralinteractive/GameMode/Games/{pid}',
                'com.feralinteractive.GameMode.Game', 'Requester',
            ], capture_output=True, text=True, timeout=3, check=True)
            signature, value = result.stdout.split()
            return int(value) if signature == 'i' else None
        except (OSError, ValueError, subprocess.SubprocessError):
            return None


def identity(path):
    return (path / 'stat').read_text().rsplit(')', 1)[1].split()[19]


def discover(proc=Path('/proc')):
    games = {}
    for path in proc.iterdir():
        if not path.name.isdigit():
            continue
        try:
            if path.stat().st_uid != os.getuid() or (path / 'comm').read_text().strip().lower() != 'wow.exe':
                continue
            born = identity(path)
            env = dict(item.split(b'=', 1) for item in (path / 'environ').read_bytes().split(b'\0') if b'=' in item)
            runner = env.get(b'PROTONPATH', b'').decode(errors='replace')
            if not Path(runner).name.startswith('ErgenProton-WoW-') or env.get(b'UMU_ID') != b'umu-wow':
                continue
            if identity(path) == born:
                games[int(path.name)] = born
        except (OSError, ValueError, IndexError):
            continue
    return games


class Supervisor:
    def __init__(self, api, proc=Path('/proc')):
        self.api, self.proc, self.owned = api, proc, {}

    def same(self, pid, born):
        try:
            return identity(self.proc / str(pid)) == born
        except FileNotFoundError:
            return False
        except (OSError, ValueError, IndexError):
            return None

    def tick(self, games):
        for pid, born in list(self.owned.items()):
            if self.same(pid, born) is False:
                # A transient failed /proc scan is not evidence the game exited.
                # The daemon reaps dead clients; never touch a reused PID.
                del self.owned[pid]
        for pid, born in games.items():
            status = self.api.status(pid)
            if status < 0:
                raise RuntimeError(f'GameMode query failed for {pid}')
            if status == 2 or not self.same(pid, born):
                continue
            result = self.api.start(pid)
            if result != 0:
                raise RuntimeError(f'GameMode rejected WoW PID {pid}: {result}')
            self.owned[pid] = born
            if self.api.status(pid) != 2:
                raise RuntimeError(f'GameMode did not confirm registration for {pid}')
            print(f'GameMode registered WoW PID {pid}', flush=True)

    def close(self):
        for pid, born in self.owned.items():
            if (self.same(pid, born) is True
                    and self.api.requester(pid) == os.getpid()
                    and self.api.end(pid) != 0):
                print(f'Warning: could not unregister PID {pid}', flush=True)
        self.owned.clear()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', action='store_true', help='Read-only report; no registration changes')
    args = parser.parse_args()
    api = GameMode()
    if args.report:
        print(json.dumps([{'pid': p, 'starttime': b, 'gamemode_status': api.status(p)} for p, b in discover().items()], indent=2))
        return
    runtime = Path(os.environ.get('XDG_RUNTIME_DIR', f'/run/user/{os.getuid()}'))
    with (runtime / 'ergenwow-gamemode.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit('An ErgenWoW GameMode supervisor is already running.')
        stopped = False

        def stop(*_):
            nonlocal stopped
            stopped = True

        signal.signal(signal.SIGTERM, stop)
        signal.signal(signal.SIGINT, stop)
        supervisor = Supervisor(api)
        try:
            while not stopped:
                supervisor.tick(discover())
                time.sleep(2)
        finally:
            supervisor.close()


if __name__ == '__main__':
    main()

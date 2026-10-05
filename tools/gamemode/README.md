# WoW/GameMode integration prototype

Host-side supervisor for the existing ErgenProton-WoW runner and `umu-wow` ID.
Run outside the Steam runtime/container, as the same user as the game:

```sh
python3 tools/gamemode/wow_gamemode.py --report
python3 tools/gamemode/wow_gamemode.py
```

The second command watches for WoW.exe, registers its actual host PID using
GameMode's supervisor API and releases its own registrations on Ctrl+C/SIGTERM.
The daemon reaps clients which exit. Processes already registered by another
client are left alone. PID start times protect cleanup against PID reuse.
Only same-user processes with an ErgenProton-WoW-* PROTONPATH and UMU_ID=umu-wow
are considered. No changes to launcher configuration, daemon configuration,
thread affinity, global SMT, or per-thread niceness are made by this tool.
GameMode applies its existing policy. Root is neither needed nor recommended.

This is a prototype, not automatically installed or started. If the daemon is
unavailable or rejects registration, the tool stops and releases registrations
it owns; the game continues independently. A forced SIGKILL cannot run cleanup.
Cleanup checks the daemon's `Requester` property through host `busctl` before
unregistering. Unknown or foreign ownership is left untouched. This check and
unregister are separate API calls, so a concurrent daemon restart/re-registration
between them is not atomic. A transient process-read error preserves tracking
for the next scan. Host `busctl` (systemd) is required for ownership checks.
Do not run multiple copies; a per-user runtime lock prevents this.

## Verification on 2026-10-05

- Host: i5-12400F, 6 physical cores / 12 logical CPUs, GameMode 1.8.2.
- Faugus GameMode toggle already enabled; governor was performance.
- Actual WoW process had all 12 CPUs available and mixed Wine thread priorities.
- Daemon had two launcher clients, but WoW query returned 1 (active, not registered).
- Live supervisor test changed WoW status 1 -> 2 -> 1, verifying registration
  and cleanup without leaving a registration behind.
- Fourteen unit tests cover registration, duplicate avoidance, preserving external
  registrations, PID reuse, filtering, daemon restart, query/rejection errors,
  transient missing scans, game exit, multiple games, unreadable process identity,
  foreign replacement registrations and unavailable ownership information.
- Three real systemd service start/stop cycles successfully registered WoW and
  released the registrations. No test service was left running.
- A separate live process test verified the daemon Requester matches the Python
  supervisor PID and confirmed successful unregister with GameMode 1.8.2.
- The user-service unit passed systemd-analyze verification. Installer tested
  with an isolated home, non-default XDG config path and backup creation.
- After a user restart with MangoHud, a valid baseline capture was obtained.
  Initial scene is GPU-bound (99.5% average GPU load); it cannot demonstrate
  CPU optimization benefits. Performance comparisons are still in progress.

## Optional user service

```sh
bash tools/gamemode/install-user.sh --install
systemctl --user start ergenwow-gamemode.service
```

The installer backs up existing files and does not enable/start the service.
After validation, enable automatic startup in graphical sessions with
`systemctl --user enable ergenwow-gamemode.service`. Disable and stop using
`systemctl --user disable --now ergenwow-gamemode.service`.
Inspect logs with `journalctl --user -u ergenwow-gamemode.service`.
The service does not launch or terminate the game.

## Work remaining before release

1. Validate daemon start/stop, game restart, multiple WoW processes and launcher
   lifecycle in the real container setup; add packaging and opt-out integration.
2. Compare identical scenes, camera and settings with supervisor off/on in
   alternating order. Keep WriteCopy and the Proton build unchanged. Collect
   repeated 60-second MangoHud captures, 1% lows and thread CPU measurements.
3. Separately evaluate any daemon renice or topology policy; do not combine
   changes or assume physical-core-only pinning is faster. The current CPU has
   six symmetric cores, not a P/E hybrid topology.
4. Require no regressions in raid/dungeon gameplay and a sustained stability
   run. A successful API test is not evidence of an FPS improvement.

No global GameMode config has been installed. No commits or pushes were made.

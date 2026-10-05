#!/usr/bin/env bash
set -euo pipefail
(( EUID != 0 )) || { echo 'Uruchom jako zwykły użytkownik, bez sudo.' >&2; exit 1; }
base=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
if [[ $# != 1 || "$1" != --install ]]; then
  echo 'Użycie: bash install-user.sh --install'
  echo 'Instaluje pliki użytkownika; nie włącza usługi ani nie zmienia GameMode.'
  exit 1
fi
for dependency in python3 systemctl busctl; do
  command -v "$dependency" >/dev/null || {
    printf 'Brak wymaganego narzędzia: %s. Instalacja przerwana.\n' "$dependency" >&2
    exit 1
  }
done
# Check API compatibility without registering a client.
PYTHONDONTWRITEBYTECODE=1 python3 - "$base" <<'PY'
import sys
sys.path.insert(0, sys.argv[1])
from wow_gamemode import GameMode
GameMode()
PY
dest="$HOME/.local/lib/ergenwow-gamemode"
units="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
mkdir -p "$dest" "$units"
# Save previous versions before replacing them.
for target in "$dest/wow_gamemode.py" "$units/ergenwow-gamemode.service"; do
  if [[ -e "$target" ]]; then
    backup=$(mktemp "$target.backup.XXXXXX")
    cp -p -- "$target" "$backup"
    printf 'Kopia poprzedniej wersji: %s\n' "$backup"
  fi
done
install -m 644 "$base/wow_gamemode.py" "$dest/wow_gamemode.py"
install -m 644 "$base/ergenwow-gamemode.service" "$units/ergenwow-gamemode.service"
systemctl --user daemon-reload
echo 'Pliki zainstalowane. Usługa nie została automatycznie uruchomiona.'
echo 'Start: systemctl --user start ergenwow-gamemode.service'
echo 'Stop:  systemctl --user stop ergenwow-gamemode.service'
echo 'Autostart: systemctl --user enable ergenwow-gamemode.service'

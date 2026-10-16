#!/usr/bin/env python3
"""Installe le thème localement ; le CSS et le lanceur restent dans ce dépôt."""

import argparse
from datetime import datetime
import os
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parent


def xdg_path(name, fallback):
    value = os.environ.get(name)
    return Path(value).expanduser() if value else Path.home() / fallback


def desktop_quote(value):
    # Deux niveaux d'échappement : valeur Desktop Entry, puis argument Exec.
    value = str(value)
    for char in ('\\', '"', '`', '$'):
        value = value.replace(char, '\\' + char)
    return '"' + value.replace('\\', '\\\\').replace('%', '%%') + '"'


def backup_if_needed(path):
    if not path.exists() and not path.is_symlink():
        return
    suffix = datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    backup = path.with_name(path.name + '.backup-' + suffix)
    shutil.move(str(path), str(backup))
    print(f'Sauvegarde : {backup}')


def link(source, destination):
    if destination.is_symlink() and destination.resolve() == source.resolve():
        return
    backup_if_needed(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.symlink_to(source)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--appimage', type=Path, default=Path.home() / 'AppImages/kchat.appimage')
    args = parser.parse_args()
    appimage = args.appimage.expanduser().absolute()
    if not appimage.is_file() or not os.access(appimage, os.X_OK):
        parser.error(f'AppImage absente ou non exécutable : {appimage}')
    for name in ('custom.css', 'launch.py'):
        if not (ROOT / name).is_file():
            parser.error(f'Fichier manquant dans le dépôt : {name}')
    python = Path(sys.executable).absolute()  # Préserver le chemin du virtualenv.
    if subprocess.run([str(python), '-c', 'import websockets'], capture_output=True).returncode:
        parser.error('Dépendance manquante. Installer requirements.txt avec ce Python.')

    config = xdg_path('XDG_CONFIG_HOME', '.config') / 'kchat-custom'
    data_home = xdg_path('XDG_DATA_HOME', '.local/share')
    data = data_home / 'kchat-custom-css'
    state = xdg_path('XDG_CACHE_HOME', '.cache') / 'kchat-custom-css'
    desktop = data_home / 'applications/kchat-custom-css.desktop'
    link(ROOT / 'custom.css', config / 'custom.css')
    link(ROOT / 'launch.py', data / 'launch.py')

    arguments = [python, data / 'launch.py', '--appimage', appimage,
                 '--css', config / 'custom.css', '--state-dir', state]
    entry = '\n'.join([
        '[Desktop Entry]', 'Type=Application', 'Name=kChat (CSS custom)',
        'Comment=kChat avec le thème CSS versionné', 'Icon=applications-internet',
        'Exec=env DESKTOPINTEGRATION=1 ' + ' '.join(map(desktop_quote, arguments)) + ' %U',
        'Terminal=false', 'Categories=Network;InstantMessaging;', 'StartupWMClass=kChat', '',
    ])
    desktop.parent.mkdir(parents=True, exist_ok=True)
    if not desktop.exists() or desktop.read_text(encoding='utf-8') != entry:
        backup_if_needed(desktop)
        desktop.write_text(entry, encoding='utf-8')
        desktop.chmod(0o644)
    refresh = shutil.which('update-desktop-database')
    if refresh:
        subprocess.run([refresh, str(desktop.parent)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f'CSS : {config / "custom.css"} → {ROOT / "custom.css"}')
    print(f'Raccourci : {desktop}')
    print('Fermer complètement kChat puis ouvrir « kChat (CSS custom) ».')


if __name__ == '__main__':
    main()

#!/usr/bin/python3
"""Lance kChat et recharge un fichier CSS local toutes les secondes."""

import argparse
import asyncio
import fcntl
import json
from pathlib import Path
import subprocess
import sys
import time
import urllib.parse
import urllib.request

import websockets

PORT = 9223
STYLE_ID = "kchat-custom-css"
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def targets():
    with OPENER.open(f"http://127.0.0.1:{PORT}/json/list", timeout=2) as response:
        return json.load(response)


def is_chat(target):
    url = urllib.parse.urlsplit(target.get("url", ""))
    host = url.hostname or ""
    return target.get("type") == "page" and url.scheme == "https" and (
        host == "kchat.infomaniak.com"
        or host.endswith(".kchat.infomaniak.com")
        or (host == "ksuite.infomaniak.com" and url.path.startswith("/kchat"))
    )


def is_shell(target):
    url = urllib.parse.urlsplit(target.get("url", ""))
    return target.get("type") == "page" and url.scheme == "kchat-desktop" and url.hostname == "renderer" and url.path.endswith(".html") and url.path not in {"/call.html", "/callDialing.html"}


def expression(css, shared_theme=None):
    return """(() => {
      const id = %s;
      const css = %s;
      if (!document.head || !document.body) return {ready: false};
      const root = document.documentElement;
      const shared = %s;
      const shell = location.protocol === 'kchat-desktop:';
      const mode = (value, fallback) => {
        let color = value.trim();
        if (/^#[0-9a-f]{3}$/i.test(color)) color = '#' + [...color.slice(1)].map(c => c+c).join('');
        const rgb = /^#[0-9a-f]{6}$/i.test(color)
          ? [1,3,5].map(i => parseInt(color.slice(i,i+2),16))
          : color.match(/^rgba?\\(\\s*(\\d+)[, ]+\\s*(\\d+)[, ]+\\s*(\\d+)/)?.slice(1).map(Number);
        return rgb ? (rgb[0]*.2126+rgb[1]*.7152+rgb[2]*.0722 < 128 ? 'dark' : 'light') : fallback;
      };
      // Lire les valeurs inline d'origine, indépendantes de notre CSS prioritaire.
      const appearance = shell ? shared.appearance : mode(root.style.getPropertyValue('--center-channel-bg'), document.body.classList.contains('kchat-dark-theme') ? 'dark' : 'light');
      // La navigation suit le mode global, même si le thème clair natif a une sidebar sombre.
      const sidebar = appearance;
      const surface = shell ? (location.pathname.includes('serversSidebar') ? 'spaces' : 'window') : 'web';
      const modeChanged = root.dataset.kchatAppearance !== appearance || root.dataset.kchatSidebar !== sidebar;
      if (root.dataset.kchatAppearance !== appearance) root.dataset.kchatAppearance = appearance;
      if (root.dataset.kchatSidebar !== sidebar) root.dataset.kchatSidebar = sidebar;
      if (root.dataset.kchatShell !== surface) root.dataset.kchatShell = surface;
      let style = document.getElementById(id);
      const changed = !style || style.textContent !== css;
      if (!style) {
        style = document.createElement('style');
        style.id = id;
        document.head.appendChild(style);
      }
      if (changed) style.textContent = css;
      return {ready: true, changed: changed || modeChanged, present: !!style.sheet,
        appearance, sidebar, shell, visible: document.visibilityState === 'visible'};
    })()""" % (json.dumps(STYLE_ID), json.dumps(css), json.dumps(shared_theme or {"appearance": "light", "sidebar": "light"}))


async def evaluate(target, javascript):
    address = urllib.parse.urlsplit(target["webSocketDebuggerUrl"])
    # Toujours utiliser la boucle locale, même si la réponse contient un autre hôte.
    websocket_url = f"ws://127.0.0.1:{PORT}{address.path}"
    async with websockets.connect(
        websocket_url, open_timeout=3, close_timeout=1, max_size=1024 * 1024
    ) as socket:
        await socket.send(json.dumps({"id": 1, "method": "Runtime.evaluate", "params": {
            "expression": javascript, "returnByValue": True,
        }}))
        while True:
            result = json.loads(await asyncio.wait_for(socket.recv(), timeout=3))
            if result.get("id") != 1:
                continue
            if "error" in result or "exceptionDetails" in result.get("result", {}):
                raise RuntimeError("L'injection CSS a été refusée par la vue kChat.")
            return result.get("result", {}).get("result", {}).get("value", {})


async def watch(css_path):
    deadline = time.monotonic() + 60
    connected = False
    failures = 0
    known = set()
    shared_theme = {"appearance": "light", "sidebar": "light"}
    while True:
        try:
            pages = await asyncio.to_thread(targets)
            connected = True
            failures = 0
        except Exception:
            failures += 1
            if (connected and failures >= 3) or (not connected and time.monotonic() > deadline):
                print("kChat fermé ou port de débogage indisponible.", flush=True)
                return 0 if connected else 1
            await asyncio.sleep(1)
            continue

        try:
            css = css_path.read_text(encoding="utf-8")
        except OSError:
            await asyncio.sleep(1)
            continue
        ordered = list(filter(is_chat, pages)) + list(filter(is_shell, pages))
        for page in ordered:
            try:
                result = await evaluate(page, expression(css, shared_theme))
                if result.get("ready") and not result.get("shell") and result.get("visible"):
                    shared_theme = {"appearance": result["appearance"], "sidebar": result["sidebar"]}
                if result.get("ready") and (result.get("changed") or page["id"] not in known):
                    print("CSS appliqué : " + json.dumps(result, ensure_ascii=False), flush=True)
                    known.add(page["id"])
            except (OSError, RuntimeError, asyncio.TimeoutError, websockets.WebSocketException):
                # Une navigation peut détruire la vue entre sa découverte et l'injection.
                continue
        await asyncio.sleep(1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--appimage", type=Path, default=Path.home() / "AppImages/kchat.appimage")
    parser.add_argument("--css", type=Path, default=Path.home() / ".config/kchat-custom/custom.css")
    parser.add_argument("--state-dir", type=Path, default=Path.home() / ".cache/kchat-custom-css")
    parser.add_argument("--attach", action="store_true", help="Injecter sans lancer l'AppImage")
    args, app_arguments = parser.parse_known_args()
    if not args.css.is_file():
        parser.error(f"Fichier CSS introuvable : {args.css}")
    if not args.attach and not args.appimage.is_file():
        parser.error(f"AppImage introuvable : {args.appimage}")
    args.state_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    lock = (args.state_dir / "injector.lock").open("w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        if not args.attach:
            subprocess.Popen([str(args.appimage), *app_arguments],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             start_new_session=True)
        return 0
    if not args.attach:
        with (args.state_dir / "app.log").open("a") as log:
            subprocess.Popen([
                str(args.appimage),
                "--remote-debugging-address=127.0.0.1",
                f"--remote-debugging-port={PORT}",
                *app_arguments,
            ], stdout=log, stderr=log, start_new_session=True)
    print(f"Surveillance CSS : {args.css}", flush=True)
    try:
        return asyncio.run(watch(args.css))
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    sys.exit(main())

"""Desktop app: the bridge server in a background thread + the dashboard in a native window (Edge WebView2).

    python desktop.py              # run the app
    python desktop.py --selftest   # start the server, check the API answers, exit 0/1 (used by CI on the built .exe)
    python desktop.py --windowtest # also open the real window, read the rendered page, close (CI)

Data (settings.json, accounts.json, bridge.db, app.log) lives in %APPDATA%\\TRADEBRIDGE on Windows.
"""
from __future__ import annotations

import os
import sys
import threading
import time
from pathlib import Path


def data_dir(brand: str) -> Path:
    base = os.environ.get("APPDATA") or str(Path.home() / ".config")
    d = Path(base) / brand
    d.mkdir(parents=True, exist_ok=True)
    return d


def message(title: str, text: str):
    """A native message box on Windows; stderr elsewhere."""
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, text, title, 0x10)
    else:
        print(f"{title}: {text}", file=sys.stderr)


def port_free(port: int) -> bool:
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


def main() -> int:
    from bridge.config import BRAND, load_settings

    home = data_dir(BRAND)
    log = open(home / "app.log", "a", encoding="utf-8", buffering=1)
    if sys.stdout is None or getattr(sys, "frozen", False):          # windowed .exe has no console
        sys.stdout = sys.stderr = log
    os.environ["BRIDGE_HOME"] = str(home)

    import uvicorn

    from bridge.server import create_app

    settings = load_settings(str(home))
    if not port_free(settings.port):
        message(BRAND, f"Port {settings.port} is busy — is {BRAND} already running?\n"
                       f"Close the other copy, or change \"port\" in {home / 'settings.json'}.")
        return 1

    app = create_app()
    token = app.state.bridge.s.admin_token
    port = app.state.bridge.s.port
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_config=None, access_log=False))
    th = threading.Thread(target=server.run, daemon=True)
    th.start()
    for _ in range(100):                                               # wait until it answers
        if server.started:
            break
        time.sleep(0.1)
    if not server.started:
        message(BRAND, f"The server didn't start. See {home / 'app.log'}")
        return 1
    url = f"http://127.0.0.1:{port}/?t={token}"
    print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {BRAND} running on {url.split('?')[0]}", flush=True)

    if "--selftest" in sys.argv:
        import httpx
        r = httpx.get(f"http://127.0.0.1:{port}/api/state", headers={"X-Token": token}, timeout=10)
        idx = httpx.get(f"http://127.0.0.1:{port}/", timeout=10)
        css = httpx.get(f"http://127.0.0.1:{port}/static/app.css", timeout=10)
        ok = r.status_code == 200 and r.json().get("brand") == BRAND and idx.status_code == 200 and css.status_code == 200
        print(f"selftest {'OK' if ok else 'FAILED'}: state {r.status_code} index {idx.status_code} css {css.status_code}", flush=True)
        server.should_exit = True
        th.join(timeout=5)
        return 0 if ok else 1

    import webview

    class Api:
        def quit(self):
            for w in list(webview.windows):
                w.destroy()

    win = webview.create_window(BRAND, url, width=1480, height=920, min_size=(1100, 700), background_color="#000000", js_api=Api())
    result = {"ok": True}

    if "--windowtest" in sys.argv:
        result["ok"] = False

        def check(w):
            for _ in range(60):                                        # wait for the dashboard to render
                time.sleep(1)
                try:
                    brand = w.evaluate_js("document.getElementById('brand').textContent")
                    rows = w.evaluate_js("document.querySelectorAll('.panel').length")
                except Exception as e:
                    print("windowtest: js not ready", repr(e), flush=True)
                    continue
                if brand == BRAND and rows and rows >= 3:
                    result["ok"] = True
                    print(f"windowtest OK: brand={brand} panels={rows}", flush=True)
                    break
            w.destroy()

        guard = threading.Timer(120, lambda: os._exit(3))              # never hang CI
        guard.daemon = True
        guard.start()
        webview.start(check, win, private_mode=False, storage_path=str(home / "webview"))
        guard.cancel()
    else:
        webview.start(private_mode=False, storage_path=str(home / "webview"))
    server.should_exit = True                                          # window closed → stop the copier
    th.join(timeout=5)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    try:
        code = main()
    except Exception as e:                                             # never die silently in a windowed app
        import traceback
        traceback.print_exc()
        message("TRADEBRIDGE", f"Unexpected error: {e!r}")
        code = 1
    sys.exit(code)

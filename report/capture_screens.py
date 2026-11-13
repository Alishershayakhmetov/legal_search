"""Screenshots of the running demo app for the report and the slides (headless Edge driven over the DevTools protocol).

Start the app first (python app/server.py), then run this script. It opens the app with a question prefilled through
the URL (?q=...&mode=articles|titles|compare), waits until the answer is on the page and saves report/figures/app_*.png.
"""
import asyncio
import base64
import json
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import websockets

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "report" / "figures"
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
APP = "http://localhost:8610/"
PORT = 9333
SIZE = (1400, 900)

SHOTS = [
    ("app_search", "Какое наказание грозит за кражу?", "articles", "Язык запроса"),
    ("app_article_ref", "статья 1 конституции рк", "articles", "Запрос содержит номер статьи"),
    ("app_compare", "Can my personal data be collected and passed on without my consent?", "compare", "Гибрид (смысл + слова)"),
]


class Cdp:
    def __init__(self, ws):
        self.ws, self.n = ws, 0

    async def call(self, method, **params):
        self.n += 1
        await self.ws.send(json.dumps({"id": self.n, "method": method, "params": params}))
        while True:
            msg = json.loads(await self.ws.recv())
            if msg.get("id") == self.n:
                return msg.get("result", {})

    async def text(self):
        r = await self.call("Runtime.evaluate", expression="document.body.innerText", returnByValue=True)
        return r.get("result", {}).get("value", "")


async def capture(cdp, name, query, mode, wait_for):
    url = f"{APP}?q={urllib.parse.quote(query)}&mode={mode}"
    await cdp.call("Page.navigate", url=url)
    deadline = time.time() + 120
    while time.time() < deadline:
        await asyncio.sleep(2)
        text = await cdp.text()
        if wait_for in text and "Running" not in text[:400]:
            break
    else:
        raise TimeoutError(f"{name}: '{wait_for}' never appeared")
    await asyncio.sleep(2)
    shot = await cdp.call("Page.captureScreenshot", format="png")
    (OUT / f"{name}.png").write_bytes(base64.b64decode(shot["data"]))
    print("saved", OUT / f"{name}.png", flush=True)


async def main():
    proc = subprocess.Popen([EDGE, "--headless=new", "--disable-gpu", f"--remote-debugging-port={PORT}", "--hide-scrollbars",
                             f"--window-size={SIZE[0]},{SIZE[1]}", "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        targets = None
        for _ in range(30):
            try:
                targets = json.load(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json"))
                break
            except OSError:
                time.sleep(1)
        page = next(t for t in targets if t["type"] == "page")
        async with websockets.connect(page["webSocketDebuggerUrl"], max_size=None) as ws:
            cdp = Cdp(ws)
            await cdp.call("Emulation.setDeviceMetricsOverride", width=SIZE[0], height=SIZE[1], deviceScaleFactor=1, mobile=False)
            for shot in SHOTS:
                await capture(cdp, *shot)
    finally:
        proc.terminate()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

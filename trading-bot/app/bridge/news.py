"""Economic calendar (Forex Factory's public weekly feed), cached. Only USD events matter for US index futures."""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

import httpx

FEED = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"


class News:
    def __init__(self, fetch=None, ttl: int = 1800):
        self._fetch = fetch or self._get
        self.ttl = ttl
        self._at = 0.0
        self._events: list[dict] = []
        self.error = ""

    async def _get(self) -> list[dict]:
        async with httpx.AsyncClient(timeout=10, headers={"User-Agent": "Mozilla/5.0"}) as c:
            r = await c.get(FEED)
            r.raise_for_status()
            return r.json()

    async def events(self) -> list[dict]:
        if time.time() - self._at > self.ttl:
            try:
                raw = await self._fetch()
                out = []
                for e in raw:
                    if e.get("country") != "USD":
                        continue
                    try:
                        t = datetime.fromisoformat(e["date"]).astimezone(timezone.utc)
                    except (KeyError, ValueError):
                        continue
                    out.append(dict(title=e.get("title", ""), impact=e.get("impact", ""), time=t.isoformat(),
                                    forecast=e.get("forecast", ""), previous=e.get("previous", "")))
                self._events = sorted(out, key=lambda x: x["time"])
                self.error = ""
            except Exception as ex:          # offline / feed down: keep the last good copy
                self.error = f"news feed unavailable ({type(ex).__name__})"
            self._at = time.time()
        return self._events

    async def summary(self, now: datetime) -> dict:
        ev = await self.events()
        high = [e for e in ev if e["impact"] == "High"]
        nxt = next((e for e in high if e["time"] > now.isoformat()), None)
        last = next((e for e in reversed(high) if e["time"] <= now.isoformat()), None)
        return dict(next=nxt, last=last, events=ev, error=self.error)

    async def blackout(self, now: datetime, minutes: int) -> str:
        """Reason to block new entries if a high-impact USD event is within ±minutes, else ''."""
        if minutes <= 0:
            return ""
        w = timedelta(minutes=minutes)
        for e in await self.events():
            if e["impact"] == "High" and abs(datetime.fromisoformat(e["time"]) - now) <= w:
                return f"news blackout: {e['title']}"
        return ""

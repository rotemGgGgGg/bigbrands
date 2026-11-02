"""Stage 1 - harvest the pre-2002 internet's trading talk from the Usenet archives on archive.org (the Wayback Machine itself is
not reachable from this environment). Each group's mbox is downloaded, mined (mine.py) and deleted, so disk stays small.
Groups: English investing / technical analysis / futures / neural-net / chaos groups, Japanese (fj.*, japan.*), Taiwanese
(tw.*), German (de.etc.finanz.*) and UK finance groups."""
import os, subprocess, sys, time, json
import mine
SP = "/tmp/claude-0/-home-user-bigbrands/e3584704-f927-5cd0-bdfb-3c26d638e529/scratchpad/oldweb/"
GROUPS = {
    "usenet-misc": ["misc.invest.futures", "misc.invest.technical", "misc.invest.index-futures", "misc.invest.options",
                    "misc.invest.stocks", "misc.invest.commodities", "misc.invest.forex", "misc.invest.misc", "misc.invest",
                    "misc.invest.stock"],
    "usenet-alt": ["alt.invest", "alt.invest.technical-analysis", "alt.invest.technical-analysis.omega", "alt.invest.market.crash",
                   "alt.investors", "alt.agriculture.commodities"],
    "usenet-comp": ["comp.ai.neural-nets"],
    "usenet-sci": ["sci.econ.research", "sci.finance.abstracts", "sci.chaos", "sci.fractals"],
    "usenet-japan": ["japan.finance.invest", "japan.finance", "japan.finance.virtual-stock"],
    "usenet-fj": ["fj.life.money", "fj.soc.economy", "fj.sci.economics"],
    "usenet-tw": ["tw.bbs.sci.finance", "tw.infotimes.stock-market.world", "tw.infotimes.stock-market.criticism", "tw.infotimes.finance"],
    "usenet-de": ["de.etc.finanz.boerse", "de.etc.finanz.boerse.misc"],
    "usenet-uk": ["uk.finance.stockmarket"],
}


def fetch(col, grp, out):
    url = f"https://archive.org/download/{col}/{grp}.mbox.zip"
    for k in range(6):
        loc = subprocess.run(["curl", "-sS", "-m", "60", "-o", "/dev/null", "-w", "%{redirect_url}", url], capture_output=True, text=True).stdout.strip()
        if loc:
            r = subprocess.run(["curl", "-sS", "-m", "1800", "-o", out, "-w", "%{http_code}", loc], capture_output=True, text=True)
            if r.stdout.strip() == "200" and os.path.getsize(out) > 0: return True
        time.sleep(2 ** (k + 1))
    return False


if __name__ == "__main__":
    os.makedirs(SP + "raw", exist_ok=True); os.makedirs(SP + "mined", exist_ok=True)
    for col, gs in GROUPS.items():
        for g in gs:
            res = SP + f"mined/{g}.jsonl"
            if os.path.exists(res): continue
            z = SP + f"raw/{g}.zip"; t0 = time.time()
            if not fetch(col, g, z): print("FAILED", g, flush=True); continue
            st = mine.mine_zip(z, res, g)
            os.remove(z); print(g, json.dumps(st), f"{time.time() - t0:.0f}s", flush=True)
    print("harvest done", flush=True)

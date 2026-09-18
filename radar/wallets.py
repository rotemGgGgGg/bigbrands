"""Loading the tracked-wallet list exported from the wallet tracker."""
import json

import config


def load_wallets() -> list:
    raw = json.loads(config.WALLETS_FILE.read_text())
    wallets = []
    for entry in raw:
        address = entry.get("trackedWalletAddress")
        if not address:
            continue
        if config.ONLY_PRIORITY_WALLETS and not entry.get("alertsOnToast"):
            continue
        wallets.append(
            {
                "address": address,
                "name": entry.get("name") or address[:4],
                "emoji": entry.get("emoji", ""),
                "priority": bool(entry.get("alertsOnToast")),
            }
        )
    if config.MAX_WALLETS:
        wallets = wallets[: config.MAX_WALLETS]
    return wallets


def name_map(wallets: list) -> dict:
    return {w["address"]: f"{w['emoji']} {w['name']}".strip() for w in wallets}

"""Runs the parser over real messages and shows exactly what it read.

Messages are separated by a line containing only '---'. Every signal is
printed with what was extracted and, where it refused, why — so the gap
between what the sender writes and what the parser understands is visible
before any of it reaches a broker.

    python3 signals/check.py signals/messages.txt
"""
import sys

from parse import parse


def main(path: str) -> int:
    blocks = [b.strip() for b in open(path, encoding="utf-8").read().split("\n---\n")]
    blocks = [b for b in blocks if b]
    if not blocks:
        print("no messages found; separate them with a line containing only ---")
        return 1

    ok = 0
    for i, text in enumerate(blocks, 1):
        sig = parse(text)
        first = text.splitlines()[0][:58] if text.splitlines() else ""
        if sig.tradeable:
            ok += 1
            zone = f"-{sig.entry_high}" if sig.entry_high else ""
            print(f"{i:>3}. OK      {sig.side.upper():<4} {sig.symbol} "
                  f"entry {sig.entry}{zone} ({sig.order_type})  "
                  f"SL {sig.stop}  TP {sig.targets}")
        else:
            print(f"{i:>3}. REFUSED {first!r}")
            for p in sig.problems:
                print(f"        - {p}")

    print(f"\nparsed {ok} of {len(blocks)}  ({100 * ok / len(blocks):.0f}%)")
    print("A refusal costs one missed signal. A wrong read costs a position.")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        raise SystemExit(1)
    raise SystemExit(main(sys.argv[1]))

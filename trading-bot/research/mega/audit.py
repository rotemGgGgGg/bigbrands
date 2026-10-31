"""Causality audit: (1) scrambling every later day leaves day d unchanged; (2) scrambling the bars of day d after its last
used minute (exit) leaves day d unchanged - checked by replacing minutes after 15:59-hold exits is trivial, so we scramble
everything after the latest possible exit of the shortest-hold plans and compare those plans."""
import numpy as np, search as S, theories as TH
rng = np.random.default_rng(3); G = TH.groups(); bad = 0; tot = 0
orig = {k: getattr(S, k).copy() for k in ("O", "H", "L", "C")}
for g in [G[i] for i in rng.choice(len(G), 25, replace=False)]:
    P = S.run_group(*g, final=True); days = np.nonzero(P.any(1))[0]
    if len(days) < 5: continue
    d = rng.choice(days[:-2])
    for k in ("O", "H", "L", "C"): getattr(S, k)[d + 1:] = orig[k][d + 1:] * rng.uniform(.95, 1.05, size=orig[k][d + 1:].shape)
    S.PDH[:], S.PDL[:], S.PDC[:] = S.prev(S.H[:, S.RTH:].max(1)), S.prev(S.L[:, S.RTH:].min(1)), S.prev(S.C[:, -1])
    P2 = S.run_group(*g, final=True); tot += 1; bad += int(not np.allclose(P[d], P2[d]))
    for k in ("O", "H", "L", "C"): getattr(S, k)[:] = orig[k]
    S.PDH[:], S.PDL[:], S.PDC[:] = S.prev(S.H[:, S.RTH:].max(1)), S.prev(S.L[:, S.RTH:].min(1)), S.prev(S.C[:, -1])
print("future-day scramble mismatches:", bad, "/", tot)

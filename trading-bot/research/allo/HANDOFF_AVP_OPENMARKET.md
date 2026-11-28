# Handoff: test the paid AVP Zones indicator on OpenMarket (Nov 28, 2026)

## Where we are
- Rotem bought AVP Zones (άλλο research) for one week (₪74.63) and cancelled at once. Access ends Dec 5, 2026.
- The indicator runs on OpenMarket (openmarket.xyz). It is shared with the user's OpenMarket username "indilola".
- Chart id F0pHhBzM. It must be on NQ1! (CME futures), not US100. Use the 5m timeframe.
- The indicator's own table showed: 7 zones, 10 trades, 40% win rate, net +2.62R (noise, too few trades).
- Settings seen: Signals ON, Past days' zones ON, Exits ON, One trade per zone ON, Flip trades ON,
  Target = Next zone, RZ + SZ zones ON, RZ/SZ signals OFF, trading hours RTH 09:30-16:00 NY. 19 settings in total.
- Our own reconstruction of the idea had no edge over 14 years (see AVP_RESULTS.md: -0.04 to -0.08R after costs,
  p=0.42 vs random zones; only weak hint: wide zones + small risk + longs, +0.07R, t 1.23).

## Access for the agent
- The user's OpenMarket agent token is meant to be stored as an environment Network secret for host
  mcp.openmarket.xyz (Authorization: Bearer). Never ask for it in chat.
- Docs: https://mcp.openmarket.xyz/llms.txt (Streamable HTTP MCP at https://mcp.openmarket.xyz/).
  Steps: chart_workspace_select {workspaceId:"F0pHhBzM"} -> chart_status -> chart_read with bars (up to 300 per call,
  per-bar indicator values). Read-only: do not change the chart without asking.

## Goal
1. Pull AVP Zones' zones/signals/trades for as much NQ 5m history as possible.
2. Compare its zones with ours (allo/avp_port.py) and test its trades with our gates: choose on early data,
   judge later data once, 1 NQ point round-trip cost, random-zone placebo.
3. Answer Rotem short, in Hebrew: is there a real edge or not.

//+------------------------------------------------------------------+
//| NQ_Portfolio_EA.mq5 — GapFB + Pre-Open Fade + Opex short           |
//| Rules: trading-bot/STRATEGY_NQ.md · research: research/gapfb        |
//| Attach to ONE chart of the Nasdaq-100 CFD (NAS100 / US100 / USTEC), |
//| any timeframe. All decisions use New York time, computed from GMT   |
//| (US daylight-saving rules), so the broker's server time zone does   |
//| not matter. Enable "Algo Trading".                                  |
//+------------------------------------------------------------------+
#property copyright "bigbrands"
#property version   "1.00"
#include <Trade/Trade.mqh>

input double RiskPct        = 1.0;    // risk per trade, % of equity
input bool   UseGapFB       = true;
input bool   UsePreFade     = true;
input bool   UseOpex        = true;
input double GapMinPct      = 0.30;   // GapFB: |gap| ≥ this %
input int    MinScore       = 2;      // GapFB: quality score ≥ this
input double StopATR        = 2.0;    // GapFB: initial stop × ATR(14, M1)
input double TrailATR       = 5.0;    // GapFB: trailing stop × ATR
input double PreFadeZ       = 2.0;    // Pre-Fade: |z| above
input double OpexStopSigma  = 0.4;    // Opex: stop × σ (14-day mean |RTH open→close|)
input double OpexRR         = 2.0;    // Opex: target = RR × stop
input bool   OpexToday      = false;  // force opex today (holiday-shifted Thursday)
input string TelegramToken  = "";     // optional; add https://api.telegram.org to Tools → Options → Expert Advisors → WebRequest
input string TelegramChatId = "";

#define MAGIC_GAP  880101
#define MAGIC_PF   880102
#define MAGIC_OPEX 880103

CTrade trade;
void Market(long magic, string name, int s, double stopPts, double tgtPts, string info);   // defined below

//---------------------------------------------------------------- time helpers
// US DST: from the 2nd Sunday of March 07:00 GMT to the 1st Sunday of November 06:00 GMT
datetime NthSunday(int year, int month, int n)
{
   MqlDateTime t; t.year = year; t.mon = month; t.day = 1; t.hour = 0; t.min = 0; t.sec = 0;
   datetime d = StructToTime(t); TimeToStruct(d, t);
   int add = (7 - t.day_of_week) % 7;
   return d + (add + 7 * (n - 1)) * 86400;
}
int NyOffsetSeconds(datetime gmt)
{
   MqlDateTime t; TimeToStruct(gmt, t);
   datetime start = NthSunday(t.year, 3, 2) + 7 * 3600;
   datetime end   = NthSunday(t.year, 11, 1) + 6 * 3600;
   return (gmt >= start && gmt < end) ? -4 * 3600 : -5 * 3600;
}
datetime NyNow()                    { datetime g = TimeGMT(); return g + NyOffsetSeconds(g); }
int      ServerToGmtSeconds()       { return (int)(TimeCurrent() - TimeGMT()); }
datetime BarToNy(datetime serverT)  { datetime g = serverT - ServerToGmtSeconds(); return g + NyOffsetSeconds(g); }
datetime NyToServer(datetime nyT)   { datetime g = nyT - NyOffsetSeconds(nyT); return g + ServerToGmtSeconds(); }
int      MinuteOfDay(datetime t)    { MqlDateTime s; TimeToStruct(t, s); return s.hour * 60 + s.min; }
datetime DateOf(datetime t)         { return t - (t % 86400); }
string   Day(datetime ny)           { return TimeToString(ny, TIME_DATE); }

bool Done(string job)  { return GlobalVariableCheck("NQEA|" + Day(NyNow()) + "|" + job); }
void Mark(string job)  { GlobalVariableSet("NQEA|" + Day(NyNow()) + "|" + job, 1); }

void Say(string msg)
{
   Print(msg);
   if(TelegramToken == "" || TelegramChatId == "") return;
   char body[], res[]; string hdr;
   string txt = msg; StringReplace(txt, "\"", "'");
   StringToCharArray("{\"chat_id\":\"" + TelegramChatId + "\",\"text\":\"[" + _Symbol + "] " + txt + "\"}", body, 0, WHOLE_ARRAY, CP_UTF8);
   ArrayResize(body, ArraySize(body) - 1);
   WebRequest("POST", "https://api.telegram.org/bot" + TelegramToken + "/sendMessage", "Content-Type: application/json\r\n", 5000, body, res, hdr);
}

//---------------------------------------------------------------- data helpers (bars converted to NY time)
int LoadM1(MqlRates &r[], int count)  { ArraySetAsSeries(r, false); return CopyRates(_Symbol, PERIOD_M1, 0, count, r); }

// RTH stats of one NY date: open 09:30, high/low 09:30–15:59, close 15:59 (last RTH bar)
bool RthDay(MqlRates &r[], int n, datetime nyDate, double &o, double &h, double &l, double &c)
{
   bool any = false;
   for(int i = 0; i < n; i++)
   {
      datetime t = BarToNy(r[i].time);
      if(DateOf(t) != nyDate) continue;
      int m = MinuteOfDay(t);
      if(m < 570 || m >= 960) continue;
      if(!any) { o = r[i].open; h = r[i].high; l = r[i].low; any = true; }
      h = MathMax(h, r[i].high); l = MathMin(l, r[i].low); c = r[i].close;
   }
   return any;
}

double LotsForRisk(double stopPoints)
{
   double tv = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE), ts = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   double step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP), vmin = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN), vmax = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   if(tv <= 0 || ts <= 0 || stopPoints <= 0) return 0;
   double lossPerLot = stopPoints / ts * tv;
   double lots = MathFloor(AccountInfoDouble(ACCOUNT_EQUITY) * RiskPct / 100.0 / lossPerLot / step) * step;
   if(lots < vmin) return 0;
   return MathMin(lots, vmax);
}

bool HasOpposite(int side)
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(PositionGetSymbol(i) != _Symbol) continue;
      long type = PositionGetInteger(POSITION_TYPE);
      if((side == 1 && type == POSITION_TYPE_SELL) || (side == -1 && type == POSITION_TYPE_BUY)) return true;
   }
   return false;
}

void CloseMagic(long magic)
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong tk = PositionGetTicket(i);
      if(PositionGetString(POSITION_SYMBOL) == _Symbol && PositionGetInteger(POSITION_MAGIC) == magic) trade.PositionClose(tk);
   }
   for(int i = OrdersTotal() - 1; i >= 0; i--)
   {
      ulong tk = OrderGetTicket(i);
      if(OrderGetString(ORDER_SYMBOL) == _Symbol && OrderGetInteger(ORDER_MAGIC) == magic) trade.OrderDelete(tk);
   }
}

//---------------------------------------------------------------- GapFB (09:45)
void JobGapFB()
{
   MqlRates r[]; int n = LoadM1(r, 6000);
   if(n < 500) { Say("GapFB: not enough M1 history"); return; }
   datetime today = DateOf(NyNow());
   double dO, dH, dL, dC; if(!RthDay(r, n, today, dO, dH, dL, dC)) { Say("GapFB: no 09:30 bar today"); return; }
   // previous RTH session
   datetime prev = today - 86400; double yO = 0, yH = 0, yL = 0, yC = 0; bool ok = false;
   for(int k = 0; k < 6 && !ok; k++, prev -= 86400) ok = RthDay(r, n, prev, yO, yH, yL, yC);
   if(!ok) { Say("GapFB: previous session not found"); return; }
   // opening range 09:30–09:44, close of 09:44, ATR of the last 14 closed M1 bars
   double orH = -DBL_MAX, orL = DBL_MAX, c944 = 0; int last = -1;
   for(int i = 0; i < n; i++)
   {
      datetime t = BarToNy(r[i].time); if(DateOf(t) != today) continue;
      int m = MinuteOfDay(t);
      if(m >= 570 && m < 585) { orH = MathMax(orH, r[i].high); orL = MathMin(orL, r[i].low); c944 = r[i].close; last = i; }
   }
   if(last < 15) { Say("GapFB: opening range incomplete"); return; }
   double gap = dO / yC - 1.0;
   if(MathAbs(gap) * 100.0 < GapMinPct) { Say(StringFormat("GapFB: no trade — gap %+.2f%%", gap * 100)); return; }
   int s = gap > 0 ? 1 : -1;
   int score = ((s * (yC - yO) <= 0) ? 1 : 0) + (((s == 1 && dO > yH) || (s == -1 && dO < yL)) ? 1 : 0) + ((s * (c944 - dO) > 0) ? 1 : 0);
   if(score < MinScore) { Say(StringFormat("GapFB: no trade — score %d", score)); return; }
   double atr = 0; for(int i = last - 13; i <= last; i++) atr += MathMax(r[i].high - r[i].low, MathMax(MathAbs(r[i].high - r[i - 1].close), MathAbs(r[i].low - r[i - 1].close)));
   atr /= 14.0;
   if(HasOpposite(s)) { Say("GapFB: skipped, opposite position open"); return; }
   double level = s == 1 ? orH : orL, stopPts = StopATR * atr, lots = LotsForRisk(stopPts);
   if(lots <= 0) { Say("GapFB: lot below broker minimum — skipped"); return; }
   int dg = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   double sl = NormalizeDouble(level - s * stopPts, dg); level = NormalizeDouble(level, dg);
   datetime exp = NyToServer(today + 10 * 3600 + 30 * 60);
   GlobalVariableSet("NQEA|ATR|" + Day(NyNow()), atr);
   trade.SetExpertMagicNumber(MAGIC_GAP);
   bool res = s == 1 ? trade.BuyStop(lots, level, _Symbol, sl, 0, ORDER_TIME_SPECIFIED, exp, "GapFB")
                     : trade.SellStop(lots, level, _Symbol, sl, 0, ORDER_TIME_SPECIFIED, exp, "GapFB");
   Say(StringFormat("GapFB %s stop-entry %.2f until 10:30 NY | gap %+.2f%% score %d | SL %.2f trail %.2f pts | %.2f lots | %s",
       s == 1 ? "LONG" : "SHORT", level, gap * 100, score, stopPts, TrailATR * atr, lots, res ? "placed" : trade.ResultRetcodeDescription()));
}

// trailing stop: best price since entry − TrailATR × ATR (never loosens)
void ManageTrail()
{
   if(!GlobalVariableCheck("NQEA|ATR|" + Day(NyNow()))) return;
   double atr = GlobalVariableGet("NQEA|ATR|" + Day(NyNow()));
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong tk = PositionGetTicket(i);
      if(PositionGetString(POSITION_SYMBOL) != _Symbol || PositionGetInteger(POSITION_MAGIC) != MAGIC_GAP) continue;
      datetime opened = (datetime)PositionGetInteger(POSITION_TIME);
      double hi[], lo[];
      if(CopyHigh(_Symbol, PERIOD_M1, opened, TimeCurrent(), hi) <= 0 || CopyLow(_Symbol, PERIOD_M1, opened, TimeCurrent(), lo) <= 0) continue;
      double sl = PositionGetDouble(POSITION_SL), nsl;
      int dg = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
      if(PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY)
      {  nsl = NormalizeDouble(hi[ArrayMaximum(hi)] - TrailATR * atr, dg); if(nsl > sl + _Point) trade.PositionModify(tk, nsl, 0); }
      else
      {  nsl = NormalizeDouble(lo[ArrayMinimum(lo)] + TrailATR * atr, dg); if(sl == 0 || nsl < sl - _Point) trade.PositionModify(tk, nsl, 0); }
   }
}

//---------------------------------------------------------------- Pre-Open Fade (09:00) and Opex short (09:30)
void JobPreFade()
{
   MqlRates r[]; ArraySetAsSeries(r, false);
   int n = CopyRates(_Symbol, PERIOD_M30, 0, 2000, r);
   if(n < 100) { Say("PreFade: not enough M30 history"); return; }
   datetime today = DateOf(NyNow()); double rets[]; ArrayResize(rets, 0);
   double o8 = 0, c859 = 0; datetime d = 0; double oo = 0;
   for(int i = 0; i < n; i++)
   {
      datetime t = BarToNy(r[i].time); int m = MinuteOfDay(t);
      if(m == 480) { d = DateOf(t); oo = r[i].open; }
      if(m == 510 && DateOf(t) == d && oo > 0)
      {
         if(d == today) { o8 = oo; c859 = r[i].close; }
         else { int k = ArraySize(rets); ArrayResize(rets, k + 1); rets[k] = r[i].close / oo - 1.0; }
         oo = 0;
      }
   }
   int k = ArraySize(rets);
   if(o8 == 0 || k < 20) { Say("PreFade: no data for today's 08:00–08:59 window"); return; }
   double mean = 0, var = 0; for(int i = k - 20; i < k; i++) mean += rets[i]; mean /= 20;
   for(int i = k - 20; i < k; i++) var += (rets[i] - mean) * (rets[i] - mean);
   double sd = MathSqrt(var / 19), ret = c859 / o8 - 1.0, z = sd > 0 ? ret / sd : 0;
   if(MathAbs(z) <= PreFadeZ) { Print(StringFormat("PreFade: no trade — z %+.2f", z)); return; }
   int s = ret > 0 ? -1 : 1; double size = MathAbs(c859 - o8);
   Market(MAGIC_PF, "PreFade", s, size, 0.5 * size, StringFormat("move %+.1f pts z %+.2f", c859 - o8, z));
}

bool IsOpex(datetime ny) { MqlDateTime t; TimeToStruct(ny, t); return OpexToday || (t.day_of_week == 5 && t.day >= 15 && t.day <= 21); }

void JobOpex()
{
   if(!IsOpex(NyNow())) return;
   MqlRates r[]; ArraySetAsSeries(r, false);
   int n = CopyRates(_Symbol, PERIOD_M30, 0, 2000, r);
   datetime today = DateOf(NyNow()); double sum = 0; int cnt = 0;
   for(datetime d = today - 86400; d > today - 40 * 86400 && cnt < 14; d -= 86400)
   {
      double o = 0, c = 0; bool fo = false, fc = false;
      for(int i = 0; i < n; i++)
      {
         datetime t = BarToNy(r[i].time); if(DateOf(t) != d) continue;
         int m = MinuteOfDay(t);
         if(m == 570) { o = r[i].open; fo = true; }
         if(m == 930) { c = r[i].close; fc = true; }
      }
      if(fo && fc) { sum += MathAbs(c / o - 1.0); cnt++; }
   }
   if(cnt < 14) { Say("Opex: not enough history"); return; }
   double sigma = sum / 14 * SymbolInfoDouble(_Symbol, SYMBOL_BID), stopPts = OpexStopSigma * sigma;
   Market(MAGIC_OPEX, "Opex", -1, stopPts, OpexRR * stopPts, StringFormat("σ %.1f pts", sigma));
}

void Market(long magic, string name, int s, double stopPts, double tgtPts, string info)
{
   if(HasOpposite(s)) { Say(name + ": skipped, opposite position open"); return; }
   double lots = LotsForRisk(stopPts);
   if(lots <= 0) { Say(name + ": lot below broker minimum — skipped"); return; }
   int dg = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   double px = s == 1 ? SymbolInfoDouble(_Symbol, SYMBOL_ASK) : SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double sl = NormalizeDouble(px - s * stopPts, dg), tp = NormalizeDouble(px + s * tgtPts, dg);
   trade.SetExpertMagicNumber(magic);
   bool res = s == 1 ? trade.Buy(lots, _Symbol, 0, sl, tp, name) : trade.Sell(lots, _Symbol, 0, sl, tp, name);
   Say(StringFormat("%s %s %.2f lots | SL %.1f TP %.1f pts | %s | %s", name, s == 1 ? "LONG" : "SHORT", lots, stopPts, tgtPts, info,
       res ? "filled" : trade.ResultRetcodeDescription()));
}

//---------------------------------------------------------------- scheduler
int OnInit()
{
   EventSetTimer(1);
   Say(StringFormat("NQ Portfolio EA started on %s — risk %.1f%%, NY time now %s", _Symbol, RiskPct, TimeToString(NyNow(), TIME_DATE | TIME_MINUTES)));
   return INIT_SUCCEEDED;
}
void OnDeinit(const int reason) { EventKillTimer(); }

void Run(string job, int fromMin, int fromSec, int toMin, bool enabled, int which)
{
   if(!enabled || Done(job)) return;
   datetime ny = NyNow(); MqlDateTime t; TimeToStruct(ny, t);
   if(t.day_of_week == 0 || t.day_of_week == 6) return;
   int sec = t.hour * 3600 + t.min * 60 + t.sec;
   if(sec < fromMin * 60 + fromSec || sec >= toMin * 60) return;
   Mark(job);
   switch(which)
   {
      case 1: JobPreFade(); break;
      case 2: JobOpex(); break;
      case 3: JobGapFB(); break;
      case 4: CloseMagic(MAGIC_PF); break;
      case 5: CloseMagic(MAGIC_GAP); CloseMagic(MAGIC_OPEX); CloseMagic(MAGIC_PF); Say("15:55 NY — flat"); break;
   }
}

void OnTimer()
{
   Run("prefade", 9 * 60, 5, 9 * 60 + 10, UsePreFade, 1);
   Run("opex", 9 * 60 + 30, 5, 9 * 60 + 35, UseOpex, 2);
   Run("gapfb", 9 * 60 + 45, 5, 10 * 60 + 25, UseGapFB, 3);
   Run("close_pf", 13 * 60, 0, 13 * 60 + 10, UsePreFade, 4);
   Run("flat", 15 * 60 + 55, 0, 15 * 60 + 59, true, 5);
   ManageTrail();
}
//+------------------------------------------------------------------+

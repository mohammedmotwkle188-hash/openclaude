#property copyright "Gold/BTC Scalper EA"
#property version   "1.00"

#include <Trade\Trade.mqh>

CTrade trade;

input group "=== Core Settings ==="
input ulong  InpMagic              = 990033;   // Magic number (use a different value per chart/instance)
input double InpLotSize            = 0.01;     // Fixed lot size per trade
input int    InpMaxTrades          = 10;       // Max concurrent open positions (this symbol/magic)
input bool   InpAllowHedging       = true;     // Allow simultaneous buy+sell positions (needs hedging account)

input group "=== Signal: EMA crossover + RSI momentum ==="
input int    InpFastEMA            = 5;        // Fast EMA period
input int    InpSlowEMA            = 13;       // Slow EMA period
input bool   InpUseRSIFilter       = true;     // Require RSI momentum confirmation
input int    InpRSIPeriod          = 7;        // RSI period
input double InpRSIMidline         = 50.0;     // RSI midline for momentum bias

input group "=== Volatility-based stops (ATR) ==="
input int    InpATRPeriod          = 14;       // ATR period
input double InpSLATRMult          = 1.5;      // Initial SL distance = ATR * this
input double InpTPATRMult          = 3.0;      // Initial TP distance = ATR * this

input group "=== Breakeven / trailing stop ==="
input double InpBreakevenATRMult   = 1.0;      // Move SL to breakeven once profit reaches ATR * this
input double InpBreakevenLockATR   = 0.1;      // Extra profit locked at breakeven = ATR * this
input double InpTrailATRMult       = 1.0;      // Trailing distance behind price = ATR * this

input group "=== Let winners run (optional TP extension) ==="
input bool   InpExtendTP           = true;     // Push TP further out while trend continues
input double InpTPExtendTriggerATR = 0.5;      // Extend when price is within this*ATR of current TP
input double InpTPExtendStepATR    = 2.0;      // Extend TP by this*ATR each time

input group "=== Optional safety valve (0 = disabled, no filter) ==="
input int    InpMaxSpreadPoints    = 0;        // Skip new entries above this spread, in points (0 = off)

int hFastEMA, hSlowEMA, hATR, hRSI;
datetime lastBarTime = 0;

int OnInit()
{
   trade.SetExpertMagicNumber(InpMagic);
   trade.SetDeviationInPoints(50);

   hFastEMA = iMA(_Symbol, PERIOD_M1, InpFastEMA, 0, MODE_EMA, PRICE_CLOSE);
   hSlowEMA = iMA(_Symbol, PERIOD_M1, InpSlowEMA, 0, MODE_EMA, PRICE_CLOSE);
   hATR     = iATR(_Symbol, PERIOD_M1, InpATRPeriod);
   hRSI     = iRSI(_Symbol, PERIOD_M1, InpRSIPeriod, PRICE_CLOSE);

   if(hFastEMA == INVALID_HANDLE || hSlowEMA == INVALID_HANDLE ||
      hATR == INVALID_HANDLE || hRSI == INVALID_HANDLE)
     {
      Print("Failed to create indicator handle(s)");
      return INIT_FAILED;
     }

   if((ENUM_ACCOUNT_MARGIN_MODE)AccountInfoInteger(ACCOUNT_MARGIN_MODE) != ACCOUNT_MARGIN_MODE_RETAIL_HEDGING)
      Print("WARNING: account is not in hedging mode - simultaneous buy+sell positions on ",
            _Symbol, " will net against each other instead of hedging.");

   Print("GoldBtcScalperEA initialized on ", _Symbol, " magic=", InpMagic);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   IndicatorRelease(hFastEMA);
   IndicatorRelease(hSlowEMA);
   IndicatorRelease(hATR);
   IndicatorRelease(hRSI);
}

double GetATR()
{
   double buf[];
   ArraySetAsSeries(buf, true);
   if(CopyBuffer(hATR, 0, 0, 1, buf) < 1) return 0.0;
   return buf[0];
}

bool EMAUpNow()
{
   double f[1], s[1];
   if(CopyBuffer(hFastEMA, 0, 0, 1, f) < 1) return false;
   if(CopyBuffer(hSlowEMA, 0, 0, 1, s) < 1) return false;
   return f[0] > s[0];
}

bool EMADownNow()
{
   double f[1], s[1];
   if(CopyBuffer(hFastEMA, 0, 0, 1, f) < 1) return false;
   if(CopyBuffer(hSlowEMA, 0, 0, 1, s) < 1) return false;
   return f[0] < s[0];
}

bool NewBar()
{
   datetime t = iTime(_Symbol, PERIOD_M1, 0);
   if(t != lastBarTime)
     {
      lastBarTime = t;
      return true;
     }
   return false;
}

void CountPositions(int &total, int &buys, int &sells)
{
   total = 0; buys = 0; sells = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong ticket = PositionGetTicket(i);
      if(!PositionSelectByTicket(ticket)) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
      if((ulong)PositionGetInteger(POSITION_MAGIC) != InpMagic) continue;

      total++;
      if((ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY) buys++;
      else sells++;
     }
}

double NormalizeLot(double lot)
{
   double minLot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double maxLot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double step   = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);

   lot = MathRound(lot / step) * step;
   if(lot < minLot) lot = minLot;
   if(lot > maxLot) lot = maxLot;
   return lot;
}

bool SpreadOK()
{
   if(InpMaxSpreadPoints <= 0) return true;
   long spread = SymbolInfoInteger(_Symbol, SYMBOL_SPREAD);
   return spread <= InpMaxSpreadPoints;
}

void TryOpenTrades()
{
   double fastArr[2], slowArr[2], rsiArr[1];
   ArraySetAsSeries(fastArr, true);
   ArraySetAsSeries(slowArr, true);
   ArraySetAsSeries(rsiArr, true);

   if(CopyBuffer(hFastEMA, 0, 0, 2, fastArr) < 2) return;
   if(CopyBuffer(hSlowEMA, 0, 0, 2, slowArr) < 2) return;
   if(InpUseRSIFilter && CopyBuffer(hRSI, 0, 0, 1, rsiArr) < 1) return;

   bool crossUp   = fastArr[1] <= slowArr[1] && fastArr[0] > slowArr[0];
   bool crossDown = fastArr[1] >= slowArr[1] && fastArr[0] < slowArr[0];

   if(InpUseRSIFilter)
     {
      if(crossUp   && rsiArr[0] < InpRSIMidline) crossUp = false;
      if(crossDown && rsiArr[0] > InpRSIMidline) crossDown = false;
     }

   if(!crossUp && !crossDown) return;
   if(!SpreadOK()) return;

   int total, buys, sells;
   CountPositions(total, buys, sells);
   if(total >= InpMaxTrades) return;

   double atr = GetATR();
   if(atr <= 0) return;

   double lot = NormalizeLot(InpLotSize);
   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);

   if(crossUp && (InpAllowHedging || sells == 0))
     {
      double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      double sl  = NormalizeDouble(ask - InpSLATRMult * atr, digits);
      double tp  = NormalizeDouble(ask + InpTPATRMult * atr, digits);
      trade.Buy(lot, _Symbol, ask, sl, tp, "scalp-buy");
     }
   else if(crossDown && (InpAllowHedging || buys == 0))
     {
      double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      double sl  = NormalizeDouble(bid + InpSLATRMult * atr, digits);
      double tp  = NormalizeDouble(bid - InpTPATRMult * atr, digits);
      trade.Sell(lot, _Symbol, bid, sl, tp, "scalp-sell");
     }
}

void ManageTrailing()
{
   double atr = GetATR();
   if(atr <= 0) return;
   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);

   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong ticket = PositionGetTicket(i);
      if(!PositionSelectByTicket(ticket)) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
      if((ulong)PositionGetInteger(POSITION_MAGIC) != InpMagic) continue;

      ENUM_POSITION_TYPE type = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
      double openPrice = PositionGetDouble(POSITION_PRICE_OPEN);
      double curSL = PositionGetDouble(POSITION_SL);
      double curTP = PositionGetDouble(POSITION_TP);
      double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);

      double newSL = curSL;
      double newTP = curTP;
      double beTrigger = InpBreakevenATRMult * atr;
      double lock = InpBreakevenLockATR * atr;

      if(type == POSITION_TYPE_BUY)
        {
         double profit = bid - openPrice;
         if(profit >= beTrigger)
           {
            double beSL = openPrice + lock;
            double trailSL = bid - InpTrailATRMult * atr;
            double candidate = MathMax(beSL, trailSL);
            if(curSL <= 0 || candidate > curSL)
               newSL = NormalizeDouble(candidate, digits);
           }

         if(InpExtendTP && curTP > 0 && (curTP - bid) <= InpTPExtendTriggerATR * atr && EMAUpNow())
            newTP = NormalizeDouble(curTP + InpTPExtendStepATR * atr, digits);
        }
      else
        {
         double profit = openPrice - ask;
         if(profit >= beTrigger)
           {
            double beSL = openPrice - lock;
            double trailSL = ask + InpTrailATRMult * atr;
            double candidate = MathMin(beSL, trailSL);
            if(curSL <= 0 || candidate < curSL)
               newSL = NormalizeDouble(candidate, digits);
           }

         if(InpExtendTP && curTP > 0 && (ask - curTP) <= InpTPExtendTriggerATR * atr && EMADownNow())
            newTP = NormalizeDouble(curTP - InpTPExtendStepATR * atr, digits);
        }

      if(newSL != curSL || newTP != curTP)
         trade.PositionModify(ticket, newSL, newTP);
     }
}

void OnTick()
{
   ManageTrailing();
   if(NewBar())
      TryOpenTrades();
}

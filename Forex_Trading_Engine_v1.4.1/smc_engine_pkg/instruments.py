# === Forex Trading Engine v1.1.0 (Phase-1) | Amex Solutions ===
"""
Instrument Universe & Selection
==============================
The engine REGISTERS the full universe (majors, crosses, exotics, metals).
The TRADER OPTS IN — by cluster, by category, or by individual instrument.
Nothing trades unless selected. Backtest is blocked on instruments with no
verified local data (data_status='live_only') so results are never faked.

Each instrument: category, base/quote, correlation cluster, pip factor,
spread tier (cost realism), and data_status.
"""
from dataclasses import dataclass, field

@dataclass
class Instrument:
    symbol: str; name: str; category: str; base: str; quote: str
    cluster: str; pip: float; spread_tier: str; data_status: str = "live_only"

# ---- clusters: pairs that move together (feed portfolio risk caps + SMT) ----
# USD_MAJ, EUR, GBP, JPYX (yen crosses), COMM (AUD/NZD/CAD commodity), CHF,
# METAL, SCANDI, EM (emerging/exotic)

def _mk(sym,name,cat,base,quote,cluster,pip,tier,ds="live_only"):
    return Instrument(sym,name,cat,base,quote,cluster,pip,tier,ds)

UNIVERSE = {}
def _add(*args): i=_mk(*args); UNIVERSE[i.symbol]=i

# ---------------- Majors (7) ----------------
_add("EURUSD","Euro/USD (Fiber)","major","EUR","USD","EUR",0.0001,"low","verified")
_add("GBPUSD","Pound/USD (Cable)","major","GBP","USD","GBP",0.0001,"low","verified")
_add("USDJPY","USD/Yen (Gopher)","major","USD","JPY","USD_MAJ",0.01,"low","verified")
_add("USDCHF","USD/Franc (Swissie)","major","USD","CHF","CHF",0.0001,"low","verified")
_add("AUDUSD","Aussie","major","AUD","USD","COMM",0.0001,"low","verified")
_add("USDCAD","Loonie","major","USD","CAD","COMM",0.0001,"low","verified")
_add("NZDUSD","Kiwi","major","NZD","USD","COMM",0.0001,"low")
# ---------------- Metals ----------------
_add("XAUUSD","Gold","metal","XAU","USD","METAL",0.01,"low","verified")
_add("XAGUSD","Silver","metal","XAG","USD","METAL",0.001,"med","verified")
# ---------------- Euro crosses ----------------
_add("EURGBP","Euro/Pound","cross","EUR","GBP","EUR",0.0001,"low")
_add("EURAUD","Euro/Aussie","cross","EUR","AUD","EUR",0.0001,"med")
_add("EURNZD","Euro/Kiwi","cross","EUR","NZD","EUR",0.0001,"med")
_add("EURCAD","Euro/Loonie","cross","EUR","CAD","EUR",0.0001,"med")
_add("EURCHF","Euro/Franc","cross","EUR","CHF","CHF",0.0001,"low")
_add("EURJPY","Euro/Yen","cross","EUR","JPY","JPYX",0.01,"low","verified")
# ---------------- Yen crosses ----------------
_add("GBPJPY","Pound/Yen (Beast)","cross","GBP","JPY","JPYX",0.01,"med")
_add("AUDJPY","Aussie/Yen","cross","AUD","JPY","JPYX",0.01,"med")
_add("NZDJPY","Kiwi/Yen","cross","NZD","JPY","JPYX",0.01,"med")
_add("CADJPY","Loonie/Yen","cross","CAD","JPY","JPYX",0.01,"med")
_add("CHFJPY","Franc/Yen","cross","CHF","JPY","JPYX",0.01,"med")
# ---------------- Pound crosses ----------------
_add("GBPAUD","Pound/Aussie","cross","GBP","AUD","GBP",0.0001,"med")
_add("GBPNZD","Pound/Kiwi","cross","GBP","NZD","GBP",0.0001,"high")
_add("GBPCAD","Pound/Loonie","cross","GBP","CAD","GBP",0.0001,"med")
_add("GBPCHF","Pound/Franc","cross","GBP","CHF","GBP",0.0001,"med")
# ---------------- Other minor crosses ----------------
_add("AUDCAD","Aussie/Loonie","cross","AUD","CAD","COMM",0.0001,"med")
_add("AUDNZD","Aussie/Kiwi","cross","AUD","NZD","COMM",0.0001,"med")
_add("AUDCHF","Aussie/Franc","cross","AUD","CHF","COMM",0.0001,"med")
_add("CADCHF","Loonie/Franc","cross","CAD","CHF","COMM",0.0001,"med")
_add("NZDCAD","Kiwi/Loonie","cross","NZD","CAD","COMM",0.0001,"med")
_add("NZDCHF","Kiwi/Franc","cross","NZD","CHF","COMM",0.0001,"med")
# ---------------- USD exotics ----------------
for sym,name,quote,cl,pip,tier in [
 ("USDSGD","USD/Singapore","SGD","EM",0.0001,"high"),("USDHKD","USD/HongKong","HKD","EM",0.0001,"high"),
 ("USDINR","USD/Indian Rupee","INR","EM",0.01,"high"),("USDMXN","USD/Peso","MXN","EM",0.0001,"high"),
 ("USDZAR","USD/Rand","ZAR","EM",0.0001,"high"),("USDTRY","USD/Lira","TRY","EM",0.0001,"high"),
 ("USDCNH","USD/Offshore Yuan","CNH","EM",0.0001,"high"),("USDBRL","USD/Real","BRL","EM",0.0001,"high"),
 ("USDKRW","USD/Won","KRW","EM",0.01,"high"),("USDSEK","USD/Krona","SEK","SCANDI",0.0001,"high"),
 ("USDNOK","USD/Krone","NOK","SCANDI",0.0001,"high"),("USDDKK","USD/Danish Krone","DKK","SCANDI",0.0001,"high"),
 ("USDPLN","USD/Zloty","PLN","EM",0.0001,"high"),("USDTHB","USD/Baht","THB","EM",0.01,"high")]:
    _add(sym,name,"exotic","USD",quote,cl,pip,tier)
# ---------------- EUR/GBP exotics ----------------
for sym,name,base,quote,cl,tier in [
 ("EURTRY","Euro/Lira","EUR","TRY","EM","high"),("EURZAR","Euro/Rand","EUR","ZAR","EM","high"),
 ("EURMXN","Euro/Peso","EUR","MXN","EM","high"),("EURSEK","Euro/Krona","EUR","SEK","SCANDI","high"),
 ("EURNOK","Euro/Krone","EUR","NOK","SCANDI","high"),("GBPZAR","Pound/Rand","GBP","ZAR","EM","high"),
 ("GBPMXN","Pound/Peso","GBP","MXN","EM","high"),("GBPTRY","Pound/Lira","GBP","TRY","EM","high")]:
    _add(sym,name,"exotic",base,quote,cl,0.0001,tier)

CLUSTERS = sorted(set(i.cluster for i in UNIVERSE.values()))
CATEGORIES = ["major","metal","cross","exotic"]

# ---- best-effort data verification (v1.1.0) ----
# verified = raw real data (fully testable, wick-accurate)
# derived  = cross computed from real USD-majors. GROUND-TRUTH TESTED vs raw
#            EURJPY: movement matches (returns-corr 0.985 @1h) so STRUCTURE is
#            valid, BUT a systematic ~0.7% level bias exists (independent feeds /
#            quote-side). => derived pairs are for STRUCTURE-LEVEL BACKTESTING
#            ONLY, never pip-exact levels or live execution.
# live_only= no local data; tradeable only when your broker feed supplies it
for s in ["EURGBP"]:
    if s in UNIVERSE: UNIVERSE[s].data_status="verified"
for s in ["GBPJPY","AUDJPY","CADJPY","CHFJPY","EURAUD","EURCAD","EURCHF",
          "GBPAUD","GBPCAD","GBPCHF","AUDCAD","AUDCHF","CADCHF"]:
    if s in UNIVERSE: UNIVERSE[s].data_status="derived"

# ------------------------- SELECTION API -------------------------
def select(clusters=None, categories=None, symbols=None, verified_only=False,
           testable_only=False, exclude_tiers=None):
    """Trader opts in: by cluster, category, explicit symbols. Union of filters."""
    picked={}
    def ok(i):
        if exclude_tiers and i.spread_tier in exclude_tiers: return False
        if verified_only and i.data_status!="verified": return False
        if testable_only and i.data_status not in ("verified","derived"): return False
        return True
    if symbols:
        for s in symbols:
            if s in UNIVERSE and ok(UNIVERSE[s]): picked[s]=UNIVERSE[s]
    if clusters:
        for i in UNIVERSE.values():
            if i.cluster in clusters and ok(i): picked[i.symbol]=i
    if categories:
        for i in UNIVERSE.values():
            if i.category in categories and ok(i): picked[i.symbol]=i
    if not (symbols or clusters or categories):        # nothing specified -> all that pass ok()
        for i in UNIVERSE.values():
            if ok(i): picked[i.symbol]=i
    return list(picked.keys())

def cluster_of(sym): return UNIVERSE[sym].cluster if sym in UNIVERSE else "UNKNOWN"
def summary():
    from collections import Counter
    cat=Counter(i.category for i in UNIVERSE.values())
    cl=Counter(i.cluster for i in UNIVERSE.values())
    from collections import Counter as _C
    st=_C(i.data_status for i in UNIVERSE.values())
    return dict(total=len(UNIVERSE), by_category=dict(cat), by_cluster=dict(cl), by_data_status=dict(st))

if __name__ == "__main__":
    from version import banner
    print(banner()); s=summary()
    print(f"\nINSTRUMENT UNIVERSE: {s['total']} instruments, {s['verified']} with verified local data")
    print(f"  by category: {s['by_category']}")
    print(f"  clusters:    {s['by_cluster']}")
    print(f"\nSELECTION EXAMPLES (trader opts in):")
    print(f"  majors only         -> {select(categories=['major'])}")
    print(f"  metals cluster      -> {select(clusters=['METAL'])}")
    print(f"  JPY crosses         -> {select(clusters=['JPYX'])}")
    print(f"  pick 3 by symbol    -> {select(symbols=['EURUSD','XAUUSD','GBPJPY'])}")
    print(f"  verified + no-exotic-> {select(verified_only=True)}")
    print(f"  commodity bloc, tradable data only -> {select(clusters=['COMM'], verified_only=True)}")

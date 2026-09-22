"""
Forex Trading Engine — central version + brand stamp.
Import this everywhere so the version is single-sourced.
"""
ENGINE_NAME    = "Forex Trading Engine"
ENGINE_VERSION = "1.4.1"          # MAJOR.MINOR.PATCH
ENGINE_STAGE   = "Phase-1 (SMT + strategy framework + precision batch)"
ENGINE_BUILD   = "2026-09-22"
ENGINE_AUTHOR  = "Amex Solutions"

def banner():
    return f"{ENGINE_NAME} v{ENGINE_VERSION} — {ENGINE_STAGE} — build {ENGINE_BUILD}"

if __name__ == "__main__":
    print(banner())

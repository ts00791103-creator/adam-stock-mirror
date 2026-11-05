"""Read-only live probe of official market schemas and coverage."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from market_universe import SOURCES, read_json, normalize_market

for exchange, (company_url, quote_url) in SOURCES.items():
    companies, quotes = read_json(company_url), read_json(quote_url)
    print(exchange, "company fields", sorted(companies[0]), "quote fields", sorted(quotes[0]), flush=True)
    result = normalize_market(companies, quotes, exchange)
    print(exchange, "companies", result["公司數"], "valid", len(result["rows"]),
          "missing/invalid", len(result["failures"]), "sample", result["rows"][0], flush=True)
    assert len(result["rows"]) > 200, "Unexpectedly small universe; never claim full coverage"
print("Official market snapshot PASS")

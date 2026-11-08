"""Stable symbol search: exact codes outrank partial code/name matches."""


def search_stocks(stocks, query):
    needle = query.strip().casefold()
    if not needle:
        return []
    matches = [row for row in stocks
               if needle in row[0].casefold() or needle in row[1].casefold()]
    def rank(row):
        code, name = row[0].casefold(), row[1].casefold()
        return (0 if code == needle else 1 if name == needle else
                2 if code.startswith(needle) else 3 if name.startswith(needle) else 4)
    return sorted(matches, key=rank)


def preferred_stock_index(choices, query, requested_symbol=""):
    exact = next((i for i, row in enumerate(choices) if row[0].casefold() == query.strip().casefold()), None)
    if exact is not None:
        return exact
    return next((i for i, row in enumerate(choices)
                 if row[0] + (".TW" if row[2] == "上市" else ".TWO") == requested_symbol), 0)

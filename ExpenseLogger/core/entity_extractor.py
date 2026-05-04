import re
from rapidfuzz import process, fuzz


class EntityExtractor:
    MERCHANT_ALIASES = {
        "makemy trip":   "makemytrip",
        "make my trip":  "makemytrip",
        "book my show":  "bookmyshow",
        "big basket":    "bigbasket",
        "insta mart":    "instamart",
        "air india":     "airindia",
        "uber eats":     "swiggy",
    }

    def __init__(self):
        self._known_categories = []
        self._known_merchants  = []

    def register_categories(self, categories: list):
        seen = set()
        merged = []
        for cat in categories:
            key = cat.strip().lower()
            if key and key not in seen:
                seen.add(key)
                merged.append(cat.strip())
        self._known_categories = merged

    def register_merchants(self, merchants: list):
        self._known_merchants = [m.lower().strip() for m in merchants if m.strip()]

    def get_known_categories(self) -> list:
        return list(self._known_categories)

    def extract(self, query: str) -> dict:
        q      = query.lower().strip()
        tokens = re.findall(r"[a-zA-Z]+", q)

        category = None
        merchant = None
        amount   = None

        for alias, canonical in self.MERCHANT_ALIASES.items():
            if alias in q:
                merchant = canonical
                break

        if not merchant:
            for m in self._known_merchants:
                if m and m in q:
                    merchant = m
                    break

        if not merchant and self._known_merchants:
            for token in tokens:
                if len(token) < 4:
                    continue
                result = process.extractOne(token, self._known_merchants, scorer=fuzz.ratio)
                if result:
                    match, score, _ = result
                    if score >= 88:
                        merchant = match
                        break

        cats_lower = [c.lower() for c in self._known_categories]
        for i, cat_lower in enumerate(cats_lower):
            if _word_in_query(cat_lower, q):
                category = self._known_categories[i]
                break

        if not category and self._known_categories:
            for token in tokens:
                if len(token) < 3:
                    continue
                result = process.extractOne(token, cats_lower, scorer=fuzz.ratio)
                if result:
                    match, score, _ = result
                    if score >= 85:
                        idx = cats_lower.index(match)
                        category = self._known_categories[idx]
                        break

        m = re.search(r"(above|over|greater than|>=|more than)\s*(\d+)", q)
        if m:
            amount = int(m.group(2))

        return {"category": category, "merchant": merchant, "amount": amount}


def _word_in_query(word: str, query: str) -> bool:
    if " " in word:
        return word in query
    return bool(re.search(rf"\b{re.escape(word)}\b", query))

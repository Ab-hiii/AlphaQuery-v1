import re
from datetime import datetime, timedelta
import calendar
import dateparser


class DateParser:
    """
    Deterministic date parser.
    Handles:
    - specific dates
    - full months / years
    - standalone years (e.g. 2025)
    - since <month>
    - last week / yesterday / last N days
    - between <date> and <date>
    - compare_periods: 'this month vs last month' -> parses THIS month
    """

    # Matches month-only strings like "january", "march 2025"
    MONTH_ONLY = re.compile(
        r"^\s*(january|february|march|april|may|june|july|august|"
        r"september|october|november|december)(\s+\d{4})?\s*$",
        re.IGNORECASE
    )

    def _start(self, dt):
        return datetime(dt.year, dt.month, dt.day, 0, 0, 0)

    def _end(self, dt):
        return datetime(dt.year, dt.month, dt.day, 23, 59, 59)

    def _full_month(self, year, month):
        last_day = calendar.monthrange(year, month)[1]
        return (
            self._start(datetime(year, month, 1)),
            self._end(datetime(year, month, last_day)),
        )

    def _snap_to_month_start(self, dt, raw_text):
        """
        If raw_text is a month-only expression (e.g. 'january 2025'),
        snap dt to the 1st of that month.
        dateparser may return today's day-of-month projected into that month.
        """
        if self.MONTH_ONLY.match(raw_text.strip()):
            return self._start(datetime(dt.year, dt.month, 1))
        return self._start(dt)

    def _snap_to_month_end(self, dt, raw_text):
        """
        If raw_text is a month-only expression (e.g. 'march 2025'),
        snap dt to the last day of that month.
        """
        if self.MONTH_ONLY.match(raw_text.strip()):
            last_day = calendar.monthrange(dt.year, dt.month)[1]
            return self._end(datetime(dt.year, dt.month, last_day))
        return self._end(dt)

    def parse(self, query: str):
        if not query:
            return None, None

        q = query.lower()
        now = datetime.now()

        # --------------------------------------------------
        # COMPARE PERIODS: "this month vs last month"
        # Both phrases present — executor handles prev period.
        # Give it the CURRENT period (this month).
        # --------------------------------------------------
        if "this month" in q and ("last month" in q or "vs" in q or "versus" in q):
            return self._full_month(now.year, now.month)

        # --------------------------------------------------
        # COMPARE PERIODS: "this year vs last year"
        # --------------------------------------------------
        if "this year" in q and ("last year" in q or "vs" in q or "versus" in q):
            return (
                self._start(datetime(now.year, 1, 1)),
                self._end(datetime(now.year, 12, 31)),
            )

        # --------------------------------------------------
        # BETWEEN <date> AND <date>
        # FIX: snap both d1 and d2 if they are month-only strings
        # --------------------------------------------------
        m = re.search(r"between\s+(.+?)\s+and\s+(.+)", q)
        if m:
            raw_d1 = m.group(1).strip()
            raw_d2 = m.group(2).strip()
            d1 = dateparser.parse(raw_d1)
            d2 = dateparser.parse(raw_d2)
            if d1 and d2:
                return (
                    self._snap_to_month_start(d1, raw_d1),
                    self._snap_to_month_end(d2, raw_d2)
                )

        # --------------------------------------------------
        # TODAY
        # --------------------------------------------------
        if "today" in q:
            return self._start(now), self._end(now)

        # --------------------------------------------------
        # YESTERDAY
        # --------------------------------------------------
        if "yesterday" in q:
            d = now - timedelta(days=1)
            return self._start(d), self._end(d)

        # --------------------------------------------------
        # LAST WEEK (Mon-Sun)
        # --------------------------------------------------
        if "last week" in q:
            start = now - timedelta(days=now.weekday() + 7)
            end = start + timedelta(days=6)
            return self._start(start), self._end(end)

        # --------------------------------------------------
        # LAST N DAYS
        # "last 30 days" = today and the 29 days before it (30 total)
        # --------------------------------------------------
        m = re.search(r"last\s+(\d+)\s+days", q)
        if m:
            days = int(m.group(1))
            start = now - timedelta(days=days - 1)
            return self._start(start), self._end(now)

        # --------------------------------------------------
        # SINCE <MONTH>
        # FIX: if month is in the future, use previous year
        # --------------------------------------------------
        m = re.search(
            r"since\s+(january|february|march|april|may|june|july|august|"
            r"september|october|november|december)",
            q
        )
        if m:
            month = datetime.strptime(m.group(1), "%B").month
            year = now.year if month <= now.month else now.year - 1
            start = datetime(year, month, 1)
            return self._start(start), self._end(now)

        # --------------------------------------------------
        # SPECIFIC DATE: "on September 2, 2025"
        # --------------------------------------------------
        m = re.search(r"on\s+([a-z]+)\s+(\d{1,2}),?\s*(\d{4})", q)
        if m:
            dt = datetime.strptime(" ".join(m.groups()), "%B %d %Y")
            return self._start(dt), self._end(dt)

        # --------------------------------------------------
        # LAST MONTH
        # --------------------------------------------------
        if "last month" in q:
            y, mth = now.year, now.month - 1
            if mth == 0:
                y -= 1
                mth = 12
            return self._full_month(y, mth)

        # --------------------------------------------------
        # THIS MONTH
        # --------------------------------------------------
        if "this month" in q:
            return self._full_month(now.year, now.month)

        # --------------------------------------------------
        # THIS YEAR / LAST YEAR
        # --------------------------------------------------
        if "this year" in q:
            return (
                self._start(datetime(now.year, 1, 1)),
                self._end(datetime(now.year, 12, 31)),
            )

        if "last year" in q:
            y = now.year - 1
            return (
                self._start(datetime(y, 1, 1)),
                self._end(datetime(y, 12, 31)),
            )

        # --------------------------------------------------
        # IN <MONTH> -- no explicit year
        # FIX: if month is in the future, use previous year
        # --------------------------------------------------
        m = re.search(
            r"in\s+(january|february|march|april|may|june|july|august|"
            r"september|october|november|december)",
            q
        )
        if m:
            month = datetime.strptime(m.group(1), "%B").month
            year = now.year if month <= now.month else now.year - 1
            return self._full_month(year, month)

        # --------------------------------------------------
        # STANDALONE YEAR e.g. "in 2024"
        # Guard: skip if the number follows an amount keyword
        # e.g. "above 2000", "over 1500" — those are amounts not years
        # --------------------------------------------------
        m = re.search(r"\b(19|20)\d{2}\b", q)
        if m:
            # Check if this 4-digit number is preceded by an amount keyword
            before = q[:m.start()].rstrip()
            amount_keywords = ("above", "over", "greater than", ">=", "more than", "exceeding")
            if not any(before.endswith(kw) for kw in amount_keywords):
                year = int(m.group())
                return (
                    self._start(datetime(year, 1, 1)),
                    self._end(datetime(year, 12, 31)),
                )

        # --------------------------------------------------
        # FALLBACK (single date via dateparser)
        # --------------------------------------------------
        parsed = dateparser.parse(q)
        if parsed:
            return self._start(parsed), self._end(parsed)

        return None, None
import calendar
import pandas as pd
from datetime import datetime


class Executor:

    def execute(self, intent, entities, start_date, end_date):
        df = self.df.copy()

        df["_cat_lower"]      = df["category"].str.lower().str.strip()
        df["_merchant_lower"] = df["merchant"].str.lower().str.strip()

        if start_date and end_date:
            df = df[(df["date"] >= pd.to_datetime(start_date)) & (df["date"] <= pd.to_datetime(end_date))]
        elif start_date:
            df = df[df["date"] >= pd.to_datetime(start_date)]

        if entities.get("merchant"):
            df = df[df["_merchant_lower"] == entities["merchant"].lower().strip()]
        elif entities.get("category"):
            df = df[df["_cat_lower"] == entities["category"].lower().strip()]

        if entities.get("amount"):
            df = df[df["amount"] >= entities["amount"]]

        if intent == "total_spend":
            return int(df["amount"].sum())

        if intent == "list_transactions":
            return df[["date", "amount", "category", "merchant", "description"]].to_dict(orient="records")

        if intent == "top_category":
            return self._top_category(df)

        if intent == "compare_periods":
            return self._compare_periods(start_date, end_date, entities)

        if intent == "average_spend":
            return round(float(df["amount"].mean()), 2) if not df.empty else 0.0

        raise ValueError(f"Unknown intent: {intent}")

    def _top_category(self, df=None):
        target = df if df is not None else self.df
        if target.empty:
            return None
        return target.groupby("category")["amount"].sum().idxmax()

    def _prev_month(self, year, month):
        if month == 1:
            return year - 1, 12
        return year, month - 1

    def _compare_periods(self, start_date, end_date, entities):
        if not start_date or not end_date:
            return {}

        start = pd.to_datetime(start_date)
        end   = pd.to_datetime(end_date)

        full = self.df.copy()
        full["_cat_lower"]      = full["category"].str.lower().str.strip()
        full["_merchant_lower"] = full["merchant"].str.lower().str.strip()

        def _apply_entity_filters(fdf):
            if entities.get("merchant"):
                fdf = fdf[fdf["_merchant_lower"] == entities["merchant"].lower().strip()]
            elif entities.get("category"):
                fdf = fdf[fdf["_cat_lower"] == entities["category"].lower().strip()]
            return fdf

        current_df = _apply_entity_filters(full[(full["date"] >= start) & (full["date"] <= end)])

        prev_year, prev_month = self._prev_month(start.year, start.month)
        prev_last_day = calendar.monthrange(prev_year, prev_month)[1]
        prev_start = pd.Timestamp(datetime(prev_year, prev_month, 1, 0, 0, 0))
        prev_end   = pd.Timestamp(datetime(prev_year, prev_month, prev_last_day, 23, 59, 59))

        prev_df = _apply_entity_filters(full[(full["date"] >= prev_start) & (full["date"] <= prev_end)])

        return {
            start.strftime("%Y-%m"):      int(current_df["amount"].sum()),
            prev_start.strftime("%Y-%m"): int(prev_df["amount"].sum()),
        }

from fastapi import FastAPI, HTTPException, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel
from typing import List, Optional
import os
import pandas as pd
from core.intent_matcher import IntentMatcher
from core.entity_extractor import EntityExtractor
from core.date_parser import DateParser
from core.executor import Executor

app = FastAPI(title="Expense NLP API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

API_KEY        = os.environ.get("API_KEY", "dev-key")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def verify_key(key: str = Security(api_key_header)):
    if key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid or missing API key")
    return key

intent_matcher   = IntentMatcher()
entity_extractor = EntityExtractor()
date_parser      = DateParser()

executor = Executor.__new__(Executor)
executor.df = pd.DataFrame(columns=["date", "amount", "category", "merchant", "description"])

class Transaction(BaseModel):
    date:        str
    amount:      float
    category:    str
    merchant:    str
    description: Optional[str] = ""

class SyncRequest(BaseModel):
    transactions: List[Transaction]

class SyncCategoriesRequest(BaseModel):
    categories: List[str]

@app.post("/sync")
def sync_transactions(body: SyncRequest, _: str = Security(verify_key)):
    if not body.transactions:
        raise HTTPException(status_code=400, detail="No transactions provided")
    records = [{"date": t.date, "amount": t.amount, "category": t.category.strip(), "merchant": t.merchant.strip(), "description": t.description or ""} for t in body.transactions]
    df = pd.DataFrame(records)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])
    executor.df = df
    unique_cats = df["category"].dropna().unique().tolist()
    entity_extractor.register_categories(unique_cats)
    unique_merchants = df["merchant"].dropna().str.lower().unique().tolist()
    entity_extractor.register_merchants(unique_merchants)
    return {"status": "ok", "loaded": len(df), "categories": sorted(set(c.lower() for c in unique_cats))}

@app.post("/sync-categories")
def sync_categories(body: SyncCategoriesRequest, _: str = Security(verify_key)):
    if not body.categories:
        raise HTTPException(status_code=400, detail="No categories provided")
    entity_extractor.register_categories(body.categories)
    return {"status": "ok", "registered": sorted(entity_extractor.get_known_categories())}

@app.get("/query")
def process_query(q: str, _: str = Security(verify_key)):
    if executor.df is None or executor.df.empty:
        raise HTTPException(status_code=503, detail="No data loaded. Open the AlphaQuery screen in the app to sync.")
    intent_result        = intent_matcher.match_intent(q)
    entities             = entity_extractor.extract(q)
    start_date, end_date = date_parser.parse(q)
    result = executor.execute(intent=intent_result["intent"], entities=entities, start_date=start_date, end_date=end_date)
    return {"query": q, "intent": intent_result, "entities": entities, "start_date": str(start_date) if start_date else None, "end_date": str(end_date) if end_date else None, "result": result}

@app.get("/health")
def health():
    rows = len(executor.df) if executor.df is not None else 0
    return {"status": "ok", "rows_loaded": rows, "known_categories": sorted(entity_extractor.get_known_categories())}

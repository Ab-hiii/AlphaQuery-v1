# AlphaQuery: NLP-Driven Personal Finance Analytics and Expense Management System

> Ask your expenses anything. In plain English.

AlphaQuery is a hybrid Android + Python system that lets users query their personal financial data using natural language. Instead of tapping through dashboards and filters, you just ask — *"How much did I spend on food last month?"* — and get an instant, accurate answer.

---

## What it does

- **Log expenses** manually, via UPI notification capture, or by sharing a PhonePe receipt screenshot
- **Ask questions** in plain English through the AlphaQuery NLP screen
- **Group expenses** into trips or events with their own filtered views and exports
- **Import** app-exported CSV or Excel files with automatic deduplication
- **Export** your data to CSV or Excel at any time
- **Visualise** spending via category pie charts and monthly bar charts

---

## Architecture

The system has two components:

```
Android App (Kotlin + Jetpack Compose)
        │
        │  REST API (FastAPI)
        │  POST /sync
        │  POST /sync-categories
        │  GET  /query
        │  GET  /health
        ▼
Python NLP Backend (Hugging Face Spaces)
        │
        ├── Intent Matcher     (keyword rules + SBERT cosine similarity)
        ├── Entity Extractor   (alias matching + exact + RapidFuzz fuzzy)
        ├── Date Parser        (regex rules + dateparser fallback)
        └── Executor           (Pandas DataFrame aggregation)
```

---

## NLP Pipeline

A natural language query goes through 4 stages:

```
User Query
    ↓
Intent Matcher
  Stage 1: keyword rules (fast path)
  Stage 2: cosine similarity via all-MiniLM-L6-v2 (semantic fallback, margin ≥ 0.05)
  Supports: total_spend | list_transactions | top_category | compare_periods | average_spend
    ↓
Entity Extractor
  Multi-word alias matching → exact substring → RapidFuzz fuzzy (threshold 88)
  Extracts: merchant | category | amount threshold
    ↓
Date Parser
  15+ expression types: "last month", "since January", "past 7 days", "this year vs last year"
  Fallback: dateparser library
    ↓
Executor
  Pandas DataFrame filtering (date → entity → amount)
  Deterministic aggregation — no hallucination
    ↓
JSON Response
```

---

## Performance

| Metric | Score |
|--------|-------|
| Intent Classification Macro F1 | 0.93 |
| Entity Extraction Micro F1 | 0.91 |
| Date Parsing Accuracy | 97.5% |
| Average End-to-End Latency | 1.82s |
| Throughput (concurrent) | 5.1 req/s |

Evaluated on a 423-transaction synthetic dataset with 100 labeled natural language queries.

---

## Example Queries

| Query | Intent | Result |
|-------|--------|--------|
| How much did I spend on food last month? | total_spend | ₹4,850 |
| Show Amazon transactions above ₹1000 | list_transactions | 9 records |
| Where did I spend the most? | top_category | Food |
| Compare this month and last month | compare_periods | Mar ₹12,200 \| Feb ₹9,800 |
| What is my average transport expense? | average_spend | ₹342.50 |

---

## Tech Stack

**Android App**
- Kotlin + Jetpack Compose
- MVVM architecture + Room (SQLite)
- Google ML Kit OCR
- NotificationListenerService for UPI capture

**NLP Backend**
- Python 3.11 + FastAPI
- sentence-transformers (`all-MiniLM-L6-v2`)
- Pandas, RapidFuzz, dateparser
- Docker + Hugging Face Spaces

---

## Project Structure

```
Android App (ExpenseLogger3/)
├── data/
│   ├── entity/          ExpenseEntity, CategoryEntity, TripEntity, TripExpenseCrossRef
│   ├── dao/             ExpenseDao, CategoryDao, TripDao
│   └── repository/      ExpenseRepository, CategoryRepository, TripRepository
├── ui/
│   ├── screen/          ExpenseListScreen, AddExpenseScreen, EditExpenseScreen,
│   │                    AlphaQueryScreen, TripListScreen, TripDetailScreen,
│   │                    CreateTripScreen, ImportPreviewScreen, ReceiptReviewScreen
│   ├── viewmodel/       ExpenseViewModel, ExpenseViewModelFactory
│   └── navigation/      AppNavGraph, Routes
├── receipt/             OcrUtil, UpiParser, ReceiptShareActivity
└── util/                ExportCsvUtil, ExportExcelUtil, ImportUtil, OnboardingPrefs

NLP Backend (ExpenseLogger/)
├── app/api.py           FastAPI endpoints
├── core/
│   ├── intent_matcher.py
│   ├── entity_extractor.py
│   ├── date_parser.py
│   └── executor.py
├── data/
│   └── intent_templates.json   46 template phrases across 5 intents
├── Dockerfile
└── requirements.txt
```

---

## Backend Deployment

The backend runs on Hugging Face Spaces:

```
https://abhiice-expenselogger.hf.space
```

**Endpoints:**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/sync` | POST | Sync transactions from the app |
| `/sync-categories` | POST | Register user categories |
| `/query` | GET | Run a natural language query |

**Authentication:** `X-API-Key` header required on all endpoints.

**To deploy your own:**
```bash
# Clone and push to your own HF Space
git clone https://huggingface.co/spaces/Abhiice/ExpenseLogger
# Set API_KEY in Space secrets
```

---

## Android Setup

1. Clone the repository
2. Open `ExpenseLogger3/` in Android Studio
3. Update `BASE_URL` and `API_KEY` in `AlphaQueryScreen.kt` if using your own backend
4. Run on a device with Android 8.0 (API 26) or above

**To build a release APK:**
- Build → Generate Signed APK → release
- Use your `.jks` keystore

---

## Database

Room (SQLite) on-device. Version 8.

| Table | Contents |
|-------|----------|
| `expenses` | All transactions |
| `categories` | Default + user-created categories |
| `trips` | Trip/event records |
| `trip_expense_cross_ref` | Many-to-many: trips ↔ expenses |

`fallbackToDestructiveMigration` is enabled — bumping the DB version number wipes all data.

---

## Team

| Name | USN |
|------|-----|
| Abhinav Narayan | 1NT22CS008 |
| Akshaye Aaron Azariah | 1NT22CS021 |
| Atharv Bhale | 1NT22CS042 |
| Surya Praveen | 1NT22CS200 |

**Guide:** Dr. Sujata Joshi, Professor, Dept. of CSE  
**Institution:** Nitte Meenakshi Institute of Technology, Bengaluru  
**Academic Year:** 2025–26

---

## License

This project was developed as a Final Year Engineering Project at NMIT under VTU. Not licensed for commercial use.

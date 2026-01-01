from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from datetime import datetime, date
import csv
import io

from backend.app.db import SessionLocal, engine
from backend.app import crud, schemas, models
from backend.app.auth import get_current_user

# =====================================================
# FastAPI App
# =====================================================
app = FastAPI(
    title="💸 Expense Tracker API",
    description="Backend for Expense Tracker with Clerk Auth + SQLite",
    version="1.0.0",
)

# =====================================================
# CORS Middleware (🔥 MUST BE BEFORE ROUTES)
# =====================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =====================================================
# Global OPTIONS handler (extra safety)
# =====================================================
@app.options("/{path:path}")
async def options_handler():
    return {}

# =====================================================
# Routers (AFTER CORS)
# =====================================================
from backend.app.routers import insights
app.include_router(insights.router)

# =====================================================
# Database Initialization
# =====================================================
models.Base.metadata.create_all(bind=engine)

@app.on_event("startup")
def on_startup():
    import sqlite3
    try:
        conn = sqlite3.connect("expense_tracker.db")
        cursor = conn.cursor()

        try:
            cursor.execute(
                "ALTER TABLE users ADD COLUMN reminder_enabled BOOLEAN DEFAULT 0"
            )
        except Exception:
            pass

        try:
            cursor.execute(
                "ALTER TABLE users ADD COLUMN reminder_time VARCHAR DEFAULT '20:00'"
            )
        except Exception:
            pass

        conn.commit()
        conn.close()
    except Exception as e:
        print(f"⚠️ Migration Warning: {e}")

# =====================================================
# DB Session Dependency
# =====================================================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# =====================================================
# Root
# =====================================================
@app.get("/")
def read_root():
    return {"message": "🚀 Expense Tracker API is running!"}

# =====================================================
# User Preferences
# =====================================================
@app.put("/user/preferences", response_model=schemas.User)
async def update_preferences(
    prefs: schemas.UserPreferences,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = crud.get_or_create_user_by_clerk(
        db, current_user["clerk_id"], current_user["email"]
    )
    return crud.update_user_preferences(db, user.id, prefs)

# =====================================================
# Expenses
# =====================================================
@app.get("/expenses/", response_model=list[schemas.Expense])
async def read_expenses(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = crud.get_or_create_user_by_clerk(
        db, current_user["clerk_id"], current_user["email"]
    )
    return crud.get_expenses(db, user.id)

@app.post("/expenses/", response_model=schemas.Expense)
async def create_expense(
    expense: schemas.ExpenseCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = crud.get_or_create_user_by_clerk(
        db, current_user["clerk_id"], current_user["email"]
    )
    return crud.create_expense(db, expense, user.id)

@app.put("/expenses/{expense_id}", response_model=schemas.Expense)
async def update_expense(
    expense_id: int,
    expense: schemas.ExpenseCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = crud.get_or_create_user_by_clerk(
        db, current_user["clerk_id"], current_user["email"]
    )
    updated = crud.update_expense(db, expense_id, user.id, expense)
    if not updated:
        raise HTTPException(status_code=404, detail="Expense not found or unauthorized")
    return updated

@app.delete("/expenses/{expense_id}")
async def delete_expense(
    expense_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = crud.get_or_create_user_by_clerk(
        db, current_user["clerk_id"], current_user["email"]
    )
    if not crud.delete_expense(db, expense_id, user.id):
        raise HTTPException(status_code=404, detail="Expense not found or unauthorized")
    return {"success": True}

# =====================================================
# Budgets
# =====================================================
@app.post("/budgets/", response_model=schemas.Budget)
async def set_budget(
    budget: schemas.BudgetCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = crud.get_or_create_user_by_clerk(
        db, current_user["clerk_id"], current_user["email"]
    )
    return crud.set_budget(db, user.id, budget)

@app.get("/budgets/{month}", response_model=schemas.Budget)
async def get_budget(
    month: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = crud.get_or_create_user_by_clerk(
        db, current_user["clerk_id"], current_user["email"]
    )
    budget = crud.get_budget(db, user.id, month)
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    return budget

@app.get("/budgets_all/", response_model=list[schemas.Budget])
async def get_all_budgets(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = crud.get_or_create_user_by_clerk(
        db, current_user["clerk_id"], current_user["email"]
    )
    return crud.get_all_budgets(db, user.id)

# =====================================================
# Reports
# =====================================================
@app.get("/summary/")
async def summary(
    month: str | None = None,
    category: str | None = None,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = crud.get_or_create_user_by_clerk(
        db, current_user["clerk_id"], current_user["email"]
    )
    return crud.summary_expenses(db, user.id, month, category)

@app.get("/report_by_category/")
async def report_by_category(
    month: str | None = None,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = crud.get_or_create_user_by_clerk(
        db, current_user["clerk_id"], current_user["email"]
    )
    return crud.report_by_category(db, user.id, month)

# =====================================================
# Export CSV
# =====================================================
@app.get("/export/expenses")
async def export_expenses_csv(
    from_date: date,
    to_date: date,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = crud.get_or_create_user_by_clerk(
        db, current_user["clerk_id"], current_user["email"]
    )

    expenses = (
        db.query(models.Expense)
        .filter(
            models.Expense.user_id == user.id,
            models.Expense.date >= from_date,
            models.Expense.date <= to_date,
        )
        .order_by(models.Expense.date)
        .all()
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "Category", "Amount", "Description"])

    for e in expenses:
        writer.writerow([e.date, e.category, e.amount, e.description or ""])

    output.seek(0)

    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=expenses.csv"},
    )

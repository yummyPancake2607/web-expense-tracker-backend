from sqlalchemy.orm import Session
from sqlalchemy import extract
from . import models, schemas
from typing import List, Optional, Dict, Any
from collections import defaultdict
from datetime import datetime

# =====================================================
# User Functions
# =====================================================
def get_or_create_user_by_clerk(db: Session, clerk_id: str, email: str) -> models.User:
    """
    Get a user by Clerk ID or create if not exist.
    """
    user = db.query(models.User).filter(models.User.google_id == clerk_id).first()
    if not user:
        user = models.User(email=email, google_id=clerk_id)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user

# =====================================================
# Expense Functions
# =====================================================
def get_expenses(db: Session, user_id: int) -> List[models.Expense]:
    return db.query(models.Expense).filter(models.Expense.user_id == user_id).all()

def create_expense(db: Session, expense: schemas.ExpenseCreate, user_id: int) -> models.Expense:
    db_expense = models.Expense(**expense.dict(), user_id=user_id)
    db.add(db_expense)
    db.commit()
    db.refresh(db_expense)
    return db_expense

def update_expense(db: Session, expense_id: int, user_id: int, expense_update: schemas.ExpenseCreate) -> Optional[models.Expense]:
    expense = db.query(models.Expense).filter(
        models.Expense.id == expense_id,
        models.Expense.user_id == user_id
    ).first()
    if not expense:
        return None
    for field, value in expense_update.dict().items():
        setattr(expense, field, value)
    db.commit()
    db.refresh(expense)
    return expense

def delete_expense(db: Session, expense_id: int, user_id: int) -> bool:
    expense = db.query(models.Expense).filter(
        models.Expense.id == expense_id,
        models.Expense.user_id == user_id
    ).first()
    if expense:
        db.delete(expense)
        db.commit()
        return True
    return False

# =====================================================
# Budget Functions
# =====================================================
def set_budget(db: Session, user_id: int, budget: schemas.BudgetCreate) -> models.Budget:
    db_budget = db.query(models.Budget).filter(
        models.Budget.user_id == user_id,
        models.Budget.month == budget.month
    ).first()
    if db_budget:
        db_budget.amount = budget.amount
    else:
        db_budget = models.Budget(user_id=user_id, month=budget.month, amount=budget.amount)
        db.add(db_budget)
    db.commit()
    db.refresh(db_budget)
    return db_budget

def get_budget(db: Session, user_id: int, month: str) -> Optional[models.Budget]:
    return db.query(models.Budget).filter(
        models.Budget.user_id == user_id,
        models.Budget.month == month
    ).first()

def get_all_budgets(db: Session, user_id: int):
    return db.query(models.Budget).filter(models.Budget.user_id == user_id).all()

# =====================================================
# Reports / Analytics
# =====================================================
def summary_expenses(db: Session, user_id: int, month: str = None, category: str = None) -> Dict[str, Any]:
    """
    Generate a summary of expenses with totals, categories, budget usage,
    daily trends, and comparison to last month.
    """
    q = db.query(models.Expense).filter(models.Expense.user_id == user_id)

    # ✅ Use extract for Year/Month filtering
    if month:
        year, month_num = map(int, month.split("-"))
        q = q.filter(
            extract("year", models.Expense.date) == year,
            extract("month", models.Expense.date) == month_num
        )
    if category:
        q = q.filter(models.Expense.category == category)

    expenses = q.all()
    total = sum(e.amount for e in expenses)

    # --- Daily spending trend ---
    daily_spending = defaultdict(float)
    for e in expenses:
        daily_spending[e.date] += e.amount
    avg_daily = round(total / max(1, len(daily_spending)), 2) if expenses else 0.0

    # --- Top category ---
    cat_totals = defaultdict(float)
    for e in expenses:
        cat_totals[e.category] += e.amount
    top_category = max(cat_totals, key=cat_totals.get) if cat_totals else None

    # --- Budget progress ---
    budget = 0.0
    percent_used = 0.0
    if month:
        b = db.query(models.Budget).filter(
            models.Budget.user_id == user_id,
            models.Budget.month == month
        ).first()
        if b:
            budget = b.amount
            percent_used = round((total / b.amount) * 100, 2) if b.amount > 0 else 0.0

    # --- Month vs Last Month ---
    month_comparison = {"this_month": total, "last_month": 0.0, "difference": 0.0}
    if month:
        current_month = datetime.strptime(month, "%Y-%m")
        year, month_num = current_month.year, current_month.month
        last_month_year = year if month_num > 1 else year - 1
        last_month_num = month_num - 1 if month_num > 1 else 12
        last_month = f"{last_month_year}-{str(last_month_num).zfill(2)}"

        last_year, last_month_num = map(int, last_month.split("-"))
        q_last = db.query(models.Expense).filter(
            models.Expense.user_id == user_id,
            extract("year", models.Expense.date) == last_year,
            extract("month", models.Expense.date) == last_month_num
        )
        last_expenses = q_last.all()
        last_month_total = sum(e.amount for e in last_expenses)

        month_comparison = {
            "this_month": total,
            "last_month": last_month_total,
            "difference": total - last_month_total
        }

    return {
        "expenses": expenses,
        "total": total,
        "average_daily": avg_daily,
        "top_category": top_category or None,
        "budget": budget,
        "percent_used": percent_used,
        "daily_trend": [
            {"date": str(d), "amount": amt}
            for d, amt in sorted(daily_spending.items())
        ],
        "month_comparison": month_comparison
    }

def report_by_category(db: Session, user_id: int, month: str = None) -> Dict[str, float]:
    """
    Returns expense totals grouped by category.
    """
    q = db.query(models.Expense).filter(models.Expense.user_id == user_id)

    if month:
        year, month_num = map(int, month.split("-"))
        q = q.filter(
            extract("year", models.Expense.date) == year,
            extract("month", models.Expense.date) == month_num
        )

    cat_total = defaultdict(float)
    for expense in q.all():
        cat_total[expense.category] += expense.amount
    return dict(cat_total)
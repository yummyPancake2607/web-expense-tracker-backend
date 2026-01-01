from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import date, timedelta, datetime
import calendar
from collections import defaultdict
from sqlalchemy import func
from .. import crud, models, db
from ..auth import get_current_user

router = APIRouter()

def get_db():
    db_session = db.SessionLocal()
    try:
        yield db_session
    finally:
        db_session.close()

# Helper to calculate days remaining in current month
def days_remaining_in_month():
    today = date.today()
    # Month range
    last_day_of_month = calendar.monthrange(today.year, today.month)[1]
    last_date = date(today.year, today.month, last_day_of_month)
    remaining = (last_date - today).days
    return max(remaining, 0) # Avoid negative if last day

@router.get("/budget/risk")
def get_budget_risk(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    user = crud.get_or_create_user_by_clerk(db, current_user["clerk_id"], current_user["email"])
    # 1. Get current month budget
    today = date.today()
    month_str = today.strftime("%Y-%m")
    
    budget = db.query(models.Budget).filter(models.Budget.user_id == user.id, models.Budget.month == month_str).first()
    
    if not budget:
        return {"status": "no_budget", "message": "No budget set for this month."}

    # 2. Calculate current spending
    start_date = date(today.year, today.month, 1)
    expenses = db.query(models.Expense).filter(
        models.Expense.user_id == user.id,
        models.Expense.date >= start_date,
        models.Expense.date <= today
    ).all()
    
    total_spent = sum(e.amount for e in expenses)
    remaining_budget = budget.amount - total_spent
    
    days_passed = today.day
    days_left = days_remaining_in_month()
    
    # Avoid division by zero
    if days_passed == 0:
         projected_burn = 0
    else:
        avg_daily_spend = total_spent / days_passed
        projected_total_spend = total_spent + (avg_daily_spend * days_left)
        projected_overrun = projected_total_spend > budget.amount

    days_to_exhaust = 99
    if avg_daily_spend > 0:
        days_to_exhaust = remaining_budget / avg_daily_spend

    warning_level = "safe"
    if projected_overrun:
        warning_level = "danger"
    elif remaining_budget < (budget.amount * 0.2):
         warning_level = "warning"

    return {
        "projected_overrun": projected_overrun,
        "days_to_exhaustion": int(days_to_exhaust) if days_to_exhaust < 99 else ">30",
        "warning_level": warning_level,
        "projected_total_spend": round(projected_total_spend, 2),
        "budget_limit": budget.amount
    }

@router.get("/insights")
def get_insights(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    user = crud.get_or_create_user_by_clerk(db, current_user["clerk_id"], current_user["email"])
    # Simple insights based on comparison with last month
    today = date.today()
    this_month_start = date(today.year, today.month, 1)
    
    # Last month dates
    last_month_end = this_month_start - timedelta(days=1)
    last_month_start = date(last_month_end.year, last_month_end.month, 1)
    
    # Fetch RAW expenses for analysis
    this_month_expenses_raw = db.query(models.Expense).filter(
        models.Expense.user_id == user.id,
        models.Expense.date >= this_month_start
    ).all()
    
    last_month_expenses_agg = db.query(
        models.Expense.category, func.sum(models.Expense.amount)
    ).filter(
        models.Expense.user_id == user.id,
        models.Expense.date >= last_month_start,
        models.Expense.date <= last_month_end
    ).group_by(models.Expense.category).all()
    
    insights = []
    
    # 1. Spending Concentration & Category Surge
    this_month_totals = defaultdict(float)
    weekend_spending = 0
    coffee_count = 0
    
    for e in this_month_expenses_raw:
        this_month_totals[e.category] += e.amount
        
        # Weekend Warrior
        # e.date is already a date object from SQLAlchemy
        d = e.date
        if d.weekday() >= 5: # 5=Sat, 6=Sun
            weekend_spending += e.amount
            
        # Coffeeshop
        desc = e.description.lower()
        if "coffee" in desc or "starbucks" in desc or "cafe" in desc:
            coffee_count += 1
            
    total_curr = sum(this_month_totals.values())
    
    # -- Insight 1: Concentration
    if this_month_totals:
        top_cat = max(this_month_totals, key=this_month_totals.get)
        top_amt = this_month_totals[top_cat]
        if total_curr > 0:
            percentage = (top_amt / total_curr) * 100
            if percentage > 40:
                insights.append({
                    "type": "concentration",
                    "text": f"{top_cat} makes up {int(percentage)}% of your spending — a deviation here will immediately impact your ability to pay essential bills.",
                    "icon": "📊"
                })

    # -- Insight 2: Category Surge
    last_month_dict = {cat: amt for cat, amt in last_month_expenses_agg}
    for cat, curr_amt in this_month_totals.items():
        prev_amt = last_month_dict.get(cat, 0)
        if prev_amt > 50: # Only significant amounts
            change = ((curr_amt - prev_amt) / prev_amt) * 100
            if change > 30: 
                insights.append({
                    "type": "increase",
                    "text": f"Spending on {cat} spiked {int(change)}% vs last month. This unexpected volatility shortens your budget runway.",
                    "icon": "📈"
                })

    # -- Insight 3: Weekend Warrior
    if total_curr > 0 and (weekend_spending / total_curr) > 0.5:
        insights.append({
             "type": "weekend",
             "text": "Over 50% of your spending happens on weekends. This 'binge-spending' pattern leaves you vulnerable on weekdays.",
             "icon": "🎉"
        })
        
    # -- Insight 4: Coffeeshop
    if coffee_count > 5:
        insights.append({
            "type": "habit",
            "text": f"You made {coffee_count} coffee trips this month. These micro-transactions are silently draining your adjustable income.",
            "icon": "☕"
        })
    
    return insights

@router.get("/reports/monthly-diff")
def get_monthly_diff(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    user = crud.get_or_create_user_by_clerk(db, current_user["clerk_id"], current_user["email"])
    today = date.today()
    this_month_start = date(today.year, today.month, 1)
    last_month_end = this_month_start - timedelta(days=1)
    last_month_start = date(last_month_end.year, last_month_end.month, 1)

    this_month = db.query(models.Expense.category, func.sum(models.Expense.amount)).filter(
        models.Expense.user_id == user.id, models.Expense.date >= this_month_start
    ).group_by(models.Expense.category).all()
    
    last_month = db.query(models.Expense.category, func.sum(models.Expense.amount)).filter(
        models.Expense.user_id == user.id, models.Expense.date >= last_month_start, models.Expense.date <= last_month_end
    ).group_by(models.Expense.category).all()

    current_map = {c: a for c, a in this_month}
    last_map = {c: a for c, a in last_month}
    
    all_cats = set(current_map.keys()) | set(last_map.keys())
    diffs = []
    
    for cat in all_cats:
        curr = current_map.get(cat, 0)
        prev = last_map.get(cat, 0)
        diff = curr - prev
        diffs.append({"category": cat, "current": curr, "previous": prev, "diff": diff})
        
    # Sort by absolute difference
    diffs.sort(key=lambda x: abs(x["diff"]), reverse=True)
    return diffs

@router.get("/anomalies")
def get_anomalies(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    user = crud.get_or_create_user_by_clerk(db, current_user["clerk_id"], current_user["email"])
    # Return last 5 anomalies
    anomalies = db.query(models.Expense).filter(
        models.Expense.user_id == user.id,
        models.Expense.is_anomaly == True
    ).order_by(models.Expense.date.desc()).limit(5).all()
    
    
    return anomalies

@router.get("/spending-profile")
def get_spending_profile(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    user = crud.get_or_create_user_by_clerk(db, current_user["clerk_id"], current_user["email"])
    
    # Fetch this month's expenses
    today = date.today()
    start_date = date(today.year, today.month, 1)
    expenses = db.query(models.Expense).filter(
        models.Expense.user_id == user.id,
        models.Expense.date >= start_date
    ).all()
    
    if not expenses:
         return {"profile": "Newcomer", "description": "Not enough data yet.", "icon": "🌱"}

    total_spent = sum(e.amount for e in expenses)
    weekend_spent = sum(e.amount for e in expenses if e.date.weekday() >= 5)
    
    cat_totals = defaultdict(float)
    for e in expenses:
        cat_totals[e.category] += e.amount
        
    food_spent = cat_totals.get("Food", 0) + cat_totals.get("Groceries", 0) + cat_totals.get("Restaurants", 0)
    
    # Logic Rules
    profile = "Balanced Spender"
    desc = "Your spending is distributed, but you lack a clear saving strategy for unexpected costs."
    icon = "⚖️"

    if total_spent > 0:
        if (weekend_spent / total_spent) > 0.40:
            profile = "Weekend Spender"
            desc = "You spend 40% of your money in 2 days. This volatility creates Monday-Friday cash flow gaps."
            icon = "🎉"
        elif (food_spent / total_spent) > 0.50:
            profile = "Food-Dominant"
            desc = "Food costs are eating 50% of your budget. One less meal out extends your runway by 3 days."
            icon = "🍔"
    
    # Check for Budget Drifter (if applicable)
    # This overrides others if critical
    # Reuse simple logic: if > 80% usage before day 20
    # (Simple check for now)
    
    return {"profile": profile, "description": desc, "icon": icon}

from pydantic import BaseModel

class ScenarioInput(BaseModel):
    scenario_type: str # 'reduce_food_20', 'eat_out_less'

@router.post("/budget/simulate")
def simulate_budget(scenario: ScenarioInput, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    user = crud.get_or_create_user_by_clerk(db, current_user["clerk_id"], current_user["email"])
    
    # Get current state
    today = date.today()
    start_date = date(today.year, today.month, 1)
    expenses = db.query(models.Expense).filter(
        models.Expense.user_id == user.id,
        models.Expense.date >= start_date
    ).all()
    
    # Get Budget
    month_str = today.strftime("%Y-%m")
    budget = db.query(models.Budget).filter(models.Budget.user_id == user.id, models.Budget.month == month_str).first()
    budget_amt = budget.amount if budget else 1000 # default
    
    total_spent = sum(e.amount for e in expenses)
    remaining_budget = budget_amt - total_spent
    
    # Calculate daily average so far
    days_passed = today.day
    avg_daily_now = total_spent / days_passed if days_passed > 0 else 0
    
    days_left = days_remaining_in_month()
    
    # Apply Scenario Logic
    projected_savings = 0
    new_daily_avg = avg_daily_now
    
    if scenario.scenario_type == 'reduce_food_20':
        # Calculate food spend per day
        food_spent = sum(e.amount for e in expenses if e.category in ['Food', 'Groceries', 'Restaurants'])
        food_daily = food_spent / days_passed if days_passed > 0 else 0
        savings_per_day = food_daily * 0.20
        new_daily_avg = avg_daily_now - savings_per_day
        
    elif scenario.scenario_type == 'cut_subscription':
        # Assume a fixed saving (e.g., $15/month prorated? or just one off?)
        # Let's say saving $5/day purely for simulation
        new_daily_avg = avg_daily_now - 5
        
    if new_daily_avg < 0: new_daily_avg = 0
    
    projected_total = total_spent + (new_daily_avg * days_left)
    days_to_exhaust = 99
    if new_daily_avg > 0:
        days_to_exhaust = remaining_budget / new_daily_avg
        
    days_safe = int(days_to_exhaust) if days_to_exhaust < 99 else ">30"
    
    risk_msg = ""
    if projected_total > budget_amt:
        risk_msg = f"Even with this change, you will run out of money in {days_safe} days. You need deeper cuts."
    else:
        risk_msg = f"This change secures your budget for {days_safe} days. You have a small safety buffer."

    return {
        "original_projected": total_spent + (avg_daily_now * days_left),
        "new_projected": projected_total,
        "days_to_exhaustion": days_safe,
        "risk_status": "danger" if projected_total > budget_amt else "safe",
        "savings_message": risk_msg
    }

@router.get("/wrapped")
def get_money_wrapped(period: str = "month", current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    user = crud.get_or_create_user_by_clerk(db, current_user["clerk_id"], current_user["email"])
    
    today = date.today()
    month_str = today.strftime("%Y-%m")
    start_date = date(today.year, today.month, 1)
    
    expenses = db.query(models.Expense).filter(
        models.Expense.user_id == user.id,
        models.Expense.date >= start_date
    ).all()
    
    budget = db.query(models.Budget).filter(models.Budget.user_id == user.id, models.Budget.month == month_str).first()
    budget_amt = budget.amount if budget else 1000
    
    total_spent = sum(e.amount for e in expenses)
    remaining = budget_amt - total_spent
    
    # --- Analysis Data Prep ---
    cat_totals = defaultdict(float)
    weekend_spent = 0
    transaction_count = len(expenses)
    
    for e in expenses:
        cat_totals[e.category] += e.amount
        if e.date.weekday() >= 5: weekend_spent += e.amount
        
    top_cat = "General"
    top_cat_amt = 0
    if cat_totals:
        top_cat = max(cat_totals, key=cat_totals.get)
        top_cat_amt = cat_totals[top_cat]
        
    # --- 1. Patterns (Strictly 3 Max) ---
    patterns = []
    
    # P1: Dominant Category
    if total_spent > 0:
        top_pct = (top_cat_amt / total_spent) * 100
        if top_pct > 40:
             patterns.append(f"🎬 {int(top_pct)}% spent on {top_cat}")
             
    # P2: Weekend Vibe (Proxy for 'Late Night' if we lack time)
    if total_spent > 0 and (weekend_spent / total_spent) > 0.35:
         patterns.append(f"⚡ One weekend consumed {int((weekend_spent/total_spent)*100)}% of your budget")
         
    # P3: Frequency / "Coffee" check (Impulse)
    if transaction_count > 15:
        patterns.append("🛒 You averaged a purchase every 2 days")
    elif transaction_count > 0 and (total_spent / transaction_count) > 100:
        patterns.append("💎 You prefer few, high-value purchases")

    # Fallback pattern
    if not patterns:
        patterns.append("🌱 You are building your spending history")

    # Limit to 3
    patterns = patterns[:3]

    # --- 2. Money Personality (Deterministic) ---
    personality_label = "Balanced but Fragile"
    personality_desc = "Good distribution, but your buffer is running thin."
    
    # Logic Tree
    if total_spent > 0:
        ent_amt = cat_totals.get("Entertainment", 0) + cat_totals.get("Shopping", 0)
        food_amt = cat_totals.get("Food", 0) + cat_totals.get("Groceries", 0) + cat_totals.get("Restaurants", 0)
        
        if (ent_amt / total_spent) > 0.5:
            personality_label = "Late-Night Entertainer"
            personality_desc = "Your money wakes up after 9 PM. Entertainment rules your weekends."
        elif (food_amt / total_spent) > 0.5:
            personality_label = "Food-First Thinker"
            personality_desc = "Taste comes first. Dining out is your primary love language."
        elif transaction_count > 20 and (total_spent / budget_amt) < 0.8:
            personality_label = "Impulse Buyer"
            personality_desc = "Lots of small taps. You love the dopamine of a new purchase."
        elif (total_spent / budget_amt) < 0.3:
            personality_label = "Budget Optimist"
            personality_desc = "You're playing it safe. Maybe too safe? Live a little."
        elif (weekend_spent / total_spent) > 0.6:
            personality_label = "Weekend Warrior"
            personality_desc = "Mon-Fri you save. Sat-Sun you behave like a different person."
            
    # --- 3. Risk / Consequence ---
    days_left = days_remaining_in_month()
    avg_daily = total_spent / today.day if today.day > 0 else 0
    projected = total_spent + (avg_daily * days_left)
    
    risk_status = "STABLE"
    days_until_break = 99
    
    if projected > budget_amt:
        risk_status = "FRAGILE"
        if avg_daily > 0:
            days_until_break = remaining / avg_daily
            
    days_safe = int(days_until_break) if days_until_break < 30 else 30
    
    # --- 4. Recommendation (One Action) ---
    rec = "Keep tracking every expense."
    if risk_status == "FRAGILE":
        rec = f"Cut {top_cat} by 25% and you stay safe."
    else:
        rec = "You're safe. Save 10% of your remaining budget."

    return {
        "period": today.strftime("%B %Y"),
        "total_spent": int(total_spent),
        "patterns": patterns,
        "personality": {
            "label": personality_label,
            "description": personality_desc
        },
        "risk": {
            "days_left": days_safe,
            "buffer": int(remaining) if remaining > 0 else 0,
            "status": risk_status
        },
        "recommendation": rec
    }

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

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
# CORS Middleware (MUST be here, at the top)
# =====================================================
origins = ["http://localhost:3000", 
           "http://127.0.0.1:3000"
           ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =====================================================
# Database Initialization
# =====================================================
models.Base.metadata.create_all(bind=engine)

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
# Expenses
# =====================================================
@app.get("/expenses/", response_model=list[schemas.Expense])
async def read_expenses(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    user = crud.get_or_create_user_by_clerk(db, current_user["clerk_id"], current_user["email"])
    return crud.get_expenses(db, user.id)

@app.post("/expenses/", response_model=schemas.Expense)
async def create_expense(expense: schemas.ExpenseCreate, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    user = crud.get_or_create_user_by_clerk(db, current_user["clerk_id"], current_user["email"])
    return crud.create_expense(db, expense, user.id)

@app.put("/expenses/{expense_id}", response_model=schemas.Expense)
async def update_expense(expense_id: int, expense: schemas.ExpenseCreate, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    user = crud.get_or_create_user_by_clerk(db, current_user["clerk_id"], current_user["email"])
    out = crud.update_expense(db, expense_id, user.id, expense)
    if not out:
        raise HTTPException(status_code=404, detail="Expense not found or unauthorized")
    return out

@app.delete("/expenses/{expense_id}")
async def delete_expense(expense_id: int, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    user = crud.get_or_create_user_by_clerk(db, current_user["clerk_id"], current_user["email"])
    success = crud.delete_expense(db, expense_id, user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Expense not found or unauthorized")
    return {"success": True}

# =====================================================
# Budgets
# =====================================================
@app.post("/budgets/", response_model=schemas.Budget)
async def set_budget(budget: schemas.BudgetCreate, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    user = crud.get_or_create_user_by_clerk(db, current_user["clerk_id"], current_user["email"])
    return crud.set_budget(db, user.id, budget)

@app.get("/budgets/{month}", response_model=schemas.Budget)
async def get_budget(month: str, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    user = crud.get_or_create_user_by_clerk(db, current_user["clerk_id"], current_user["email"])
    result = crud.get_budget(db, user.id, month)
    if not result:
        raise HTTPException(status_code=404, detail="Budget not found")
    return result

@app.get("/budgets_all/", response_model=list[schemas.Budget])
async def get_all_budgets(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    user = crud.get_or_create_user_by_clerk(db, current_user["clerk_id"], current_user["email"])
    return crud.get_all_budgets(db, user.id)

# =====================================================
# Reports
# =====================================================
@app.get("/summary/")
async def summary(month: str = None, category: str = None, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    user = crud.get_or_create_user_by_clerk(db, current_user["clerk_id"], current_user["email"])
    return crud.summary_expenses(db, user.id, month, category)

@app.get("/report_by_category/")
async def report_by_category(month: str = None, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    user = crud.get_or_create_user_by_clerk(db, current_user["clerk_id"], current_user["email"])
    return crud.report_by_category(db, user.id, month) 

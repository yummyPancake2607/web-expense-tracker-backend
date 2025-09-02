from pydantic import BaseModel
from datetime import date
from typing import Optional

class ExpenseBase(BaseModel):
    date: date
    description: str
    amount: float
    category: str

class ExpenseCreate(ExpenseBase):
    pass

class Expense(ExpenseBase):
    id: int
    class Config:
        orm_mode = True

class BudgetBase(BaseModel):
    month: str
    amount: float

class BudgetCreate(BudgetBase):
    pass

class Budget(BudgetBase):
    id: int
    class Config:
        orm_mode = True

class UserBase(BaseModel):
    email: str

class UserCreate(UserBase):
    google_id: Optional[str] = None

class User(UserBase):
    id: int
    class Config:
        orm_mode = True

class Summary(BaseModel):
    total: float
    expenses: list[Expense]
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey, UniqueConstraint, Boolean
from sqlalchemy.orm import relationship

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    google_id = Column(String, unique=True, index=True, nullable=True)  # stores Clerk ID

    expenses = relationship("Expense", back_populates="owner")
    budgets = relationship("Budget", back_populates="owner")

class Expense(Base):
    __tablename__ = "expenses"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    date = Column(Date, nullable=False)
    description = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    category = Column(String, nullable=False)
    is_anomaly = Column(Boolean, default=False)

    owner = relationship("User", back_populates="expenses")

class Budget(Base):
    __tablename__ = "budgets"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    month = Column(String, nullable=False)  # format: YYYY-MM
    amount = Column(Float, nullable=False)

    owner = relationship("User", back_populates="budgets")
    __table_args__ = (UniqueConstraint('user_id', 'month', name='_user_month_uc'),)
# app/models/base.py
import pytz
#from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, DateTime
from datetime import datetime

Base = declarative_base()

class BaseModel(Base):
    __abstract__ = True
    
    id = Column(Integer, primary_key=True, index=True)
    #created_at = Column(DateTime, default=datetime.timezone.utc)
    created_at = Column(DateTime, default=lambda: datetime.now(pytz.utc))
    
    #updated_at = Column(DateTime, default=datetime.timezone.utc, onupdate=datetime.timezone.utc)
    updated_at = Column(DateTime, default=lambda: datetime.now(pytz.utc), onupdate=lambda: datetime.now(pytz.utc))


from pydantic import BaseModel
from typing import Optional

class ProductBase(BaseModel):
    name: str
    price: float
    unit: str
    quantity: float
    source: str

class ProductCreate(ProductBase):
    pass

class Product(ProductBase):
    id: int
    standard_price: float

    class Config:
        from_attributes = True 
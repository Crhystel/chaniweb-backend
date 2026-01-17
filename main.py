from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import create_all_tables
from sqlalchemy.orm import Session
import models, schemas, database
from typing import List

app = FastAPI(title="ChaniWeb Core API")

models.database.Base.metadata.create_all(bind=database.engine)

def normalize_price(price: float, quantity: float, unit: str):
    # Convierte todo a precio por 1kg o 1L
    unit = unit.lower()
    if unit in ['gr', 'g']:
        return (price / quantity) * 1000
    if unit in ['ml']:
        return (price / quantity) * 1000
    return price / quantity

@app.get("/productos", response_model=List[schemas.Product])
def get_products(db: Session = Depends(database.get_db)):
    return db.query(models.Product).all()

@app.post("/productos", response_model=schemas.Product)
def create_product(product: schemas.ProductCreate, db: Session = Depends(database.get_db)):
    std_price = normalize_price(product.price, product.quantity, product.unit)
    db_product = models.Product(**product.dict(), standard_price=std_price)
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product
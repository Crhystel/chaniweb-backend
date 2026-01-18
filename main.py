from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import models, schemas, database
from typing import List
import redis
import json
import threading
import time
import os

app = FastAPI(title="ChaniWeb Core API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_methods=["*"],
    allow_headers=["*"],
)

database.Base.metadata.create_all(bind=database.engine)

# Conexión a Redis para caché y colas
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
redis_client = redis.from_url(REDIS_URL)

def calculate_std_price(price: float, quantity: float, unit: str):
    # HU-03: Normalización a 1kg o 1L
    u = unit.lower().strip()
    if u in ['gr', 'g', 'ml']:
        return (price / quantity) * 1000
    return price / quantity

@app.get("/productos", response_model=List[schemas.Product])
def get_products(db: Session = Depends(database.get_db)):
    # Intentar caché primero
    cached = redis_client.get("productos_cache")
    if cached:
        return json.loads(cached)
    
    # Si no hay caché, consultar BD
    products = db.query(models.Product).all()
    
    # Convertir a dict y cachear por 30 segundos
    products_data = [
        {
            "id": p.id,
            "name": p.name,
            "price": p.price,
            "unit": p.unit,
            "quantity": p.quantity,
            "source": p.source,
            "standard_price": p.standard_price
        } for p in products
    ]
    redis_client.setex("productos_cache", 30, json.dumps(products_data))
    
    return products_data

@app.post("/productos", response_model=schemas.Product)
def create_product(product: schemas.ProductCreate, db: Session = Depends(database.get_db)):
    std_p = calculate_std_price(product.price, product.quantity, product.unit)
    db_prod = models.Product(**product.dict(), standard_price=std_p)
    db.add(db_prod)
    db.commit()
    db.refresh(db_prod)
    
    # Invalidar caché
    redis_client.delete("productos_cache")
    
    return db_prod

@app.post("/internal/products")
def process_queue_item(product_data: dict, db: Session = Depends(database.get_db)):
    """Endpoint interno para consumir de la cola Redis"""
    try:
        product = schemas.ProductCreate(**product_data)
        return create_product(product, db)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

def start_queue_consumer():
    """Inicia consumidor de colas en background"""
    while True:
        try:
            # Obtener mensaje de la cola (blocking)
            message = redis_client.brpop('products_queue', timeout=5)
            if message:
                _, product_json = message
                product_data = json.loads(product_json)
                
                # Crear sesión de BD y guardar producto
                db = database.SessionLocal()
                try:
                    product = schemas.ProductCreate(**product_data)
                    std_p = calculate_std_price(product.price, product.quantity, product.unit)
                    db_prod = models.Product(**product.dict(), standard_price=std_p)
                    db.add(db_prod)
                    db.commit()
                    db.refresh(db_prod)
                    
                    # Invalidar caché
                    redis_client.delete("productos_cache")
                    
                    print(f" Guardado: {product.name} (ID: {db_prod.id})")
                    
                except Exception as e:
                    print(f" Error guardando {product_data.get('name', 'Unknown')}: {e}")
                    db.rollback()
                finally:
                    db.close()
                
        except Exception as e:
            print(f" Error en consumidor: {e}")
            time.sleep(1)

# Iniciar consumidor en background thread
consumer_thread = threading.Thread(target=start_queue_consumer, daemon=True)
consumer_thread.start()
print(" Consumidor de colas iniciado")

@app.on_event("startup")
def startup_event():
    print(" FastAPI iniciado")
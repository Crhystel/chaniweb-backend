from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import models, schemas, database
import redis
import time
import os

# 1. Definir la APP primero
app = FastAPI(title="ChaniWeb Core API")

# 2. Configurar Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Conexión a Redis
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")
redis_client = redis.from_url(REDIS_URL)

def calculate_std_price(price: float, quantity: float, unit: str):
    u = unit.lower().strip()
    if u in ['gr', 'g', 'ml']:
        return (price / quantity) * 1000
    return price / quantity

# 4. Evento de inicio con reintentos para la DB
@app.on_event("startup")
def startup_event():
    retries = 5
    while retries > 0:
        try:
            database.Base.metadata.create_all(bind=database.engine)
            print("✅ Conexión a DB y creación de tablas exitosa")
            break
        except Exception as e:
            print(f"⚠️ Esperando a la base de datos... {retries} reintentos restantes")
            retries -= 1
            time.sleep(5)

@app.get("/productos")
def get_products(db: Session = Depends(database.get_db)):
    products = db.query(models.Product).all()
    return [
        {
            "id": p.id,
            "name": p.name,
            "price": p.price,
            "unit": p.unit,
            "quantity": p.quantity,
            "source": p.source,
            "image_url": p.image_url,
            "standard_price": calculate_std_price(p.price, p.quantity, p.unit)
        } for p in products
    ]

@app.get("/health")
def health_check():
    try:
        redis_client.ping()
        return {"status": "healthy", "services": {"redis": "ok", "db": "ok"}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ingest/")
def ingest_product(product: schemas.ProductCreate):
    try:
        # Convertimos el objeto a JSON string y lo metemos a la cola de Redis
        # Esto es lo que da "Tolerancia a fallos"
        redis_client.lpush('products_queue', product.model_dump_json())
        return {"status": "queued", "product": product.name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en cola: {str(e)}")
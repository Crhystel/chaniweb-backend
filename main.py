from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import models, schemas, database
import redis
import json
import threading
import time
import os
import logging
from sqlalchemy import text

# Configuración de Logs (Vital para ver qué pasa en Azure)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

app = FastAPI(title="ChaniWeb Core API")
TTL_SECONDS = 3600  # 1 hora para control de duplicados

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_methods=["*"],
    allow_headers=["*"],
)

# Conexión a Redis
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
redis_client = redis.from_url(REDIS_URL)

def calculate_std_price(price: float, quantity: float, unit: str):
    """HU-03: Normalización a 1kg o 1L para comparación justa"""
    if not price or not quantity:
        return 0.0
    u = unit.lower().strip()
    if u in ['gr', 'g', 'ml']:
        return (price / quantity) * 1000
    return price / quantity

def should_process_product(product_data: dict) -> bool:
    """Controla duplicados y frecuencia usando Redis para no saturar la DB"""
    pid = product_data.get("external_id")
    price = product_data.get("price")

    if not pid or price is None:
        return False

    key = f"product:{pid}"
    now = time.time()
    cached = redis_client.get(key)

    if not cached:
        # Si no está en caché, es nuevo, lo dejamos pasar
        redis_client.set(key, json.dumps({"price": price, "last_saved": now}), ex=TTL_SECONDS)
        return True

    cached_data = json.loads(cached)
    # Si el precio es igual y no ha pasado el TTL, ignoramos
    if cached_data["price"] == price and (now - cached_data["last_saved"] < TTL_SECONDS):
        return False

    # Si el precio cambió, actualizamos caché y dejamos pasar
    redis_client.set(key, json.dumps({"price": price, "last_saved": now}), ex=TTL_SECONDS)
    return True

# --- ENDPOINTS ---

@app.get("/productos")
def get_products(db: Session = Depends(database.get_db)):
    """Retorna lista de productos con el cálculo de precio estándar"""
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

@app.post("/productos", response_model=schemas.Product)
def create_product(product: schemas.ProductCreate, db: Session = Depends(database.get_db)):
    """Guardado directo en DB (usado por el endpoint manual o interno)"""
    std_p = calculate_std_price(product.price, product.quantity, product.unit)
    
    # Pydantic v2 usa model_dump() en lugar de dict()
    product_dict = product.model_dump() if hasattr(product, "model_dump") else product.dict()
    
    db_prod = models.Product(**product_dict, standard_price=std_p)
    db.add(db_prod)
    db.commit()
    db.refresh(db_prod)
    return db_prod

@app.get("/health")
def health_check():
    """Endpoint para ver el error real en el navegador"""
    status = {}
    try:
        # Prueba 1: Redis
        try:
            redis_client.ping()
            status["redis"] = "ok"
        except Exception as redis_err:
            status["redis"] = f"ERROR: {str(redis_err)}"

        # Prueba 2: Base de Datos
        try:
            db = database.SessionLocal()
            # Usamos text("SELECT 1") de sqlalchemy
            from sqlalchemy import text
            db.execute(text("SELECT 1"))
            db.close()
            status["db"] = "ok"
        except Exception as db_err:
            status["db"] = f"ERROR: {str(db_err)}"

        # Si algo falló, devolvemos el detalle completo en lugar de un error genérico
        if "ERROR" in str(status):
            return {"status": "unhealthy", "details": status}
        
        return {"status": "healthy", "services": status}

    except Exception as e:
        return {"status": "critical_error", "message": str(e)}

def start_queue_consumer():
    """Inicia consumidor de colas en background"""
    while True:
        try:
            # Obtener mensaje de la cola (blocking)
            message = redis_client.brpop('products_queue', timeout=5)
            if not message:
                continue

            _, product_json = message
            product_data = json.loads(product_json)

            if not should_process_product(product_data):
                print(f"⏭ Ignorado (sin cambios): {product_data.get('name')}")
                continue

            # Crear sesión de BD
            db = database.SessionLocal()
            try:
                product = schemas.ProductCreate(**product_data)
                std_p = calculate_std_price(
                    product.price,
                    product.quantity,
                    product.unit
                )
                existing = db.query(models.Product).filter(
                    models.Product.external_id == product.external_id
                ).first()

                if existing:
                    existing.price = product.price
                    existing.standard_price = std_p
                    db.commit()
                    print(f"Precio actualizado: {existing.name}")
                else:
                    db_prod = models.Product(
                        **product.dict(),
                        standard_price=std_p
                    )
                    db.add(db_prod)
                    db.commit()
                    db.refresh(db_prod)
                    print(f"Guardado: {product.name} (ID: {db_prod.id})")

                # Invalidar caché
                redis_client.delete("productos_cache")

            except Exception as e:
                print(
                    f"Error guardando "
                    f"{product_data.get('name', 'Unknown')}: {e}"
                )
                db.rollback()
            finally:
                db.close()

        except Exception as e:
            print(f"Error en consumidor: {e}")
            time.sleep(1)


@app.on_event("startup")
def startup_event():
    logging.info("🔥 Aplicación iniciando... Creando tablas si no existen")
    database.Base.metadata.create_all(bind=database.engine)
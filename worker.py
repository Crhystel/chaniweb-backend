import os
import time
import json
import redis
import database
import models
import schemas
from sqlalchemy.orm import Session

# Configuración
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")
redis_client = redis.from_url(REDIS_URL)

def calculate_std_price(price: float, quantity: float, unit: str):
    u = unit.lower().strip()
    if u in ['gr', 'g', 'ml']:
        return (price / quantity) * 1000
    return price / quantity

def process_queue():
    print("🚀 Worker distribuido: Consumidor de colas iniciado...")
    
    while True:
        try:
            # Bloquea hasta que haya un mensaje en la cola
            message = redis_client.brpop('products_queue', timeout=10)
            
            if message:
                _, product_json = message
                data = json.loads(product_json)
                
                db = database.SessionLocal()
                try:
                    # Lógica para evitar duplicados (Upsert)
                    std_p = calculate_std_price(data['price'], data['quantity'], data['unit'])
                    
                    product = db.query(models.Product).filter(
                        models.Product.name == data['name'],
                        models.Product.source == data['source']
                    ).first()

                    if product:
                        product.price = data['price']
                        product.standard_price = std_p
                    else:
                        new_prod = models.Product(**data, standard_price=std_p)
                        db.add(new_prod)
                    
                    db.commit()
                    print(f"✅ Producto procesado: {data['name']} de {data['source']}")
                except Exception as e:
                    print(f"❌ Error al guardar producto: {e}")
                    db.rollback()
                finally:
                    db.close()
            
        except redis.ConnectionError:
            print("⚠️ Error de conexión con Redis, reintentando en 5s...")
            time.sleep(5)
        except Exception as e:
            print(f"💥 Error inesperado en el worker: {e}")
            time.sleep(2)

if __name__ == "__main__":
    process_queue()
# ChaniWeb Backend - API FastAPI

🚀 **API RESTful para comparación de precios de supermercados**

[![FastAPI](https://img.shields.io/badge/FastAPI-0.104.1-009688.svg)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue.svg)](https://www.postgresql.org/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-red.svg)](https://www.sqlalchemy.org/)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D.svg)](https://redis.io/)

## 🏗️ **Arquitectura**

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend    │◄──►│     Nginx      │◄──►│   FastAPI      │
│   (React)     │    │   (Proxy)       │    │   (Backend)    │
│   /api/*       │    │   Puerto 80     │    │   Puerto 8000   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
                                                        ▼
                                              ┌─────────────────┐
                                              │     Redis       │
                                              │   (Cache)      │
                                              │   /productos    │
                                              └─────────────────┘
                                                        │
                                                        ▼
                                              ┌─────────────────┐
                                              │  PostgreSQL     │
                                              │   products     │
                                              │   table        │
                                              └─────────────────┘
```

## 📊 **Modelo de Datos**

### **Product Model**
```python
class Product(Base):
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)                    # Nombre del producto
    price = Column(Float)                   # Precio
    unit = Column(String)                    # Unidad (kg, g, lt, etc.)
    quantity = Column(Float)                 # Cantidad
    source = Column(String)                  # Supermercado (Supermaxi, Aki, Mi Comisariato)
    image_url = Column(String, nullable=True) # URL de imagen real
```

## 🚀 **Endpoints**

### **GET /api/productos**
Retorna todos los productos disponibles para comparación.

**Response:**
```json
[
    {
        "id": 1,
        "name": "Arroz Diana Blanco",
        "price": 1.25,
        "unit": "kg",
        "quantity": 1.0,
        "source": "Supermaxi",
        "image_url": "https://i5.walmartimages.com/seo/..."
    }
]
```

### **GET /api/health**
Endpoint para health checks del sistema.

## 🔧 **Configuración**

### **Variables de Entorno**
```bash
DATABASE_URL=postgresql://chaniweb_user:chaniweb_password@db:5432/chaniweb_db
REDIS_URL=redis://redis:6379
```

### **Dependencias**
```python
fastapi==0.104.1          # Framework web
sqlalchemy==2.0.23         # ORM para base de datos
psycopg2-binary==2.9.7     # Driver PostgreSQL
redis==4.5.4              # Cliente Redis caché
uvicorn==0.24.0            # Servidor ASGI
```

## 🛠️ **Ejecución**

### **Desarrollo Local**
```bash
# Iniciar backend en desarrollo
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Ver documentación API
http://localhost:8000/docs
```

### **Docker**
```bash
# Construir imagen
docker build -t chaniweb-backend .

# Ejecutar contenedor
docker run -p 8000:8000 chaniweb-backend

# Con Docker Compose
docker-compose up backend
```

### **Verificación**
```bash
# Verificar conexión a base de datos
docker-compose exec backend python -c "
from database import SessionLocal
db = SessionLocal()
print('Conexión exitosa a la base de datos')
"

# Verificar productos en BD
docker-compose exec backend python -c "
from database import SessionLocal
from models import Product
db = SessionLocal()
print(f'Productos: {db.query(Product).count()}')
"
```

## 📊 **Estadísticas**

- **168 productos** en base de datos
- **9 categorías** organizadas
- **3 supermercados**: Supermaxi, Aki, Mi Comisariato
- **Endpoints**: 2 endpoints principales
- **Response time**: < 100ms para consultas cachadas

---

**🚀 Backend listo para producción**

*API estable • Base optimizada • Documentación completa*

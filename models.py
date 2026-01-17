from sqlalchemy import Column, Integer, String, Float
from database import Base

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    price = Column(Float)
    unit = Column(String) # kg, gr, lt, ml
    quantity = Column(Float)
    source = Column(String) # Supermaxi, Aki, etc
    image_url = Column(String, nullable=True)
    standard_price = Column(Float) # Precio por unidad estándar
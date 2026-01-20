from sqlalchemy import Column, Integer, String, Float, UniqueConstraint
from database import Base

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    price = Column(Float)
    unit = Column(String)
    quantity = Column(Float)
    source = Column(String)
    image_url = Column(String, nullable=True) # HU-08
    standard_price = Column(Float)
    __table_args__ = (UniqueConstraint('name', 'source', name='_name_source_uc'),)
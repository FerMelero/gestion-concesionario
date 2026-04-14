from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, Float, DateTime
from sqlalchemy.orm import relationship, declarative_base, validates # validates añadido
from datetime import datetime

Base = declarative_base()

class Vehiculo(Base):
    __tablename__ = "vehiculo"
    id = Column(Integer, primary_key=True, autoincrement=True)
    marca = Column(String(30), nullable=False)
    modelo = Column(String(80), nullable=False)
    kilometros = Column(Float, nullable=False)
    vin = Column(String(17), nullable=False, unique=True)
    anio = Column(DateTime, nullable=False)
    motor = Column(String(3), nullable=False)
    cilindrada = Column(Integer)
    consumo = Column(Float(6), nullable=False)
    marchas = Column(Integer)
    transmision = Column(String(12))
    precio_compra = Column(Float, nullable=False)
    precio_venta = Column(Float, nullable=False)
    fecha_entrada = Column(DateTime, nullable=False, default=datetime.now)
    estado = Column(String(1), nullable=False)
    potencia = Column(Integer, nullable=False)
    # falta equipamiento y si es eléctrico o híbrido enchufable velocidad de carga, KW, etc

    @validates('anio')
    def validate_anio(self, key, value):
        fecha_min = datetime(1900, 1, 1)
        fecha_max = datetime(2100, 12, 31)
        if not (fecha_min <= value <= fecha_max):
            raise ValueError(f"El año debe estar entre {fecha_min.year} y {fecha_max.year}")
        return value
    
    @validates('motor')
    def validate_motor(self, key, value): # Nombre único para que no se pisen
        motores = ["D", "G", "HB", "E", "HE"]
        if value not in motores:
            raise ValueError("Motor no válido")
        return value
    
    @validates('estado')
    def validate_estado(self, key, value): # Nombre único para que no se pisen
        estados = ["D", "R", "V"]
        if value not in estados:
            raise ValueError("Estado no válido")
        return value

    # Relación 1 a 1 para datos eléctricos
    electrico_info = relationship("DetalleElectrico", back_populates="vehiculo", uselist=False)
    # usmos uselist=False para una relación 1:1
    
    # Relación para el equipamiento variable
    lista_equipamiento = relationship("VehiculoEquipamiento", back_populates="vehiculo")
    # aqui no ponemos uselist porque un coche puede tener mucho equipamiento

class DetalleElectrico(Base):
    __tablename__ = "detalle_electrico"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    vehiculo_id = Column(Integer, ForeignKey('vehiculo.id'), unique=True)
    
    capacidad_bateria_kwh = Column(Float, nullable=False)
    velocidad_carga_kw = Column(Float, nullable=False)
    autonomia_wltp = Column(Integer, nullable=True)
    
    vehiculo = relationship("Vehiculo", back_populates="electrico_info")

class Atributo(Base):
    """Catálogo de extras: 'Techo Solar', 'Asientos Cuero', etc."""
    __tablename__ = "atributo"
    id = Column(Integer, primary_key=True)
    nombre = Column(String(50), unique=True, nullable=False)
    
    vehiculos = relationship("VehiculoEquipamiento", back_populates="atributo")

class VehiculoEquipamiento(Base):
    """Tabla puente: une un vehículo concreto con sus extras"""
    __tablename__ = "vehiculo_equipamiento"
    id = Column(Integer, primary_key=True)
    vehiculo_id = Column(Integer, ForeignKey('vehiculo.id'))
    atributo_id = Column(Integer, ForeignKey('atributo.id'))
    valor = Column(String(50)) # Ejemplo: "Sí", "Panorámico", "Negro"
    
    vehiculo = relationship("Vehiculo", back_populates="lista_equipamiento")
    atributo = relationship("Atributo", back_populates="vehiculos")
from sqlalchemy.orm import sessionmaker
import config
from models.entities import Base
from models.entities import Vehiculo
# en este archivo es en el que se crean enn el servidor postgres

engine = config.engine
Session = sessionmaker(bind=engine)
session = Session()

def crear_tablas():
    print("Estableciendoconexión con Postgres")
    Base.metadata.create_all(engine)
    print("Tablas creadas")

def get_all_vehicles():
    return session.query(Vehiculo).all()

def insert_vehicle(marca, modelo, kilometros, vin, anio, motor, potencia, pCompra, pVenta, estado, fEntrada):
    try:
        nuevo_vehiculo = Vehiculo(
            marca=marca,
            modelo=modelo,
            kilometros=kilometros,
            vin=vin, 
            anio=anio,
            motor=motor,              
            potencia=potencia,
            precio_compra= pCompra,
            precio_venta=pVenta,
            estado="D",
            fecha_entrada = fEntrada          
        )

        session.add(nuevo_vehiculo)
        session.commit()
    
    except Exception as e:
        session.rollback()
        print("Error", e)
    
    finally:
        session.close()




if __name__ == "__main__":
    crear_tablas()
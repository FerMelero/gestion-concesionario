from sqlalchemy.orm import sessionmaker
import config
from models.entities import Base
from models.entities import Vehiculo
# en este archivo es en el que se crean enn el servidor postgres

engine = config.engine
Session = sessionmaker(bind=engine)

def crear_tablas():
    print("Estableciendoconexión con Postgres")
    Base.metadata.create_all(engine)
    print("Tablas creadas")

def get_all_vehicles():
    session = Session()
    return session.query(Vehiculo).all()

def insert_vehicle(marca, modelo, kilometros, vin, anio, motor, potencia, pCompra, pVenta, estado, fEntrada):
    session = Session()
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
            estado=estado,
            fecha_entrada = fEntrada          
        )

        session.add(nuevo_vehiculo)
        session.commit()
    
    except Exception as e:
        session.rollback()
        print("Error", e)
    
    finally:
        session.close()

def vehicle_by_id(id):
    session = Session()
    try:
        return session.query(Vehiculo).filter(Vehiculo.id == id).first()
    except Exception as e:
        session.rollback()
        print("Error", e)
    finally:
        session.close()


def delete_vehicle(id):
    session = Session()
    try:
        vehiculo = session.query(Vehiculo).filter(Vehiculo.id == id).first()
        if vehiculo:
            session.delete(vehiculo)
            session.commit()
        
        else: 
            print(f"VEhiculo no encontado")
    
    except Exception as e:
        session.rollback()
        print("Error", e)

    finally:
        session.close()

def insert_masivo(lista_vehiculos):
    session = Session()

    try:
        session.add_all(lista_vehiculos)
        session.commit()
    
    except Exception as e:
        session.rollback()
        print("Error", e)

    finally:
        session.close()

def cambiar_cc_electricos():
    session = Session()
    try:
        session.query(Vehiculo).filter(Vehiculo.motor == "E").update({"cilindrada" : 0})
        session.commit() 
    except Exception as e:
        session.rollback()
        print("Error", e)
    finally:
        session.close()

def mod_vehiculo(id, datos_nuevos):
    session = Session()
    try:
        session.query(Vehiculo).filter(Vehiculo.id == id).update(datos_nuevos)
        session.commit() 
    except Exception as e:
        session.rollback()
        print("Error", e)
    finally:
        session.close()
    session = Session()
if __name__ == "__main__":
    cambiar_cc_electricos()
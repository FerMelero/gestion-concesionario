from sqlalchemy.orm import sessionmaker
import config
from models.entities import Base
from models.entities import Vehiculo

engine = config.engine
Session = sessionmaker(bind=engine)
session = Session()

from datetime import datetime
from models.entities import Vehiculo

def insert_demo_data():
    try:
        print("Preparando datos de prueba...")
        
        nuevo_vehiculo = Vehiculo(
            marca="Audi",
            modelo="RS6 Avant",
            kilometros=5000.0,
            vin="WUA12345678901234", 
            anio=datetime(2023, 1, 1),
            motor="G",              
            potencia=600,
            precio_compra=110000.50,
            precio_venta=135000.00,
            estado="D"              
        )

        session.add(nuevo_vehiculo)
        session.commit()
    
    except Exception as e:
        session.rollback()
        print("Error", e)
    
    finally:
        session.close()

if __name__ == "__main__":
    insert_demo_data()

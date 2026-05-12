from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
import config
from models.entities import Base
from models.entities import Vehiculo
from flask import request
# en este archivo es en el que se crean enn el servidor postgres

engine = config.engine
Session = sessionmaker(bind=engine)

def crear_tablas():
    print("Estableciendoconexión con Postgres")
    Base.metadata.create_all(engine)
    print("Tablas creadas")

def get_all_vehicles(page, per_page):
    session = Session()
    offset = (page - 1) * per_page
    
    query = session.query(Vehiculo).order_by(Vehiculo.id)
    
    items = query.limit(per_page).offset(offset).all()
    
    total = query.count()
    
    return {
        'items': items,
        'total': total,
        'page': page,
        'pages': (total + per_page - 1) // per_page
    }

def insert_vehicle(marca, modelo, kilometros, vin, anio, motor, potencia, pCompra, pVenta, estado, fEntrada, cilindrada, consumo, marchas, transmision):
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
            fecha_entrada = fEntrada,
            cilindrada= cilindrada,
            consumo = consumo,
            marchas = marchas,
            transmision = transmision
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

from sqlalchemy import text

def crear_audits():
    comandos = [
        """
        CREATE TABLE IF NOT EXISTS audit_vehiculo (
            operacion CHAR(1) NOT NULL,
            stamp TIMESTAMP NOT NULL,
            user_id VARCHAR(100) NOT NULL,
            id_vehiculo INTEGER,
            marca VARCHAR(30),
            modelo VARCHAR(80),
            kilometros FLOAT,
            vin VARCHAR(17),
            anio TIMESTAMP,
            motor VARCHAR(3),
            cilindrada INTEGER,
            consumo FLOAT,
            marchas INTEGER,
            transmision VARCHAR(12),
            precio_compra FLOAT,
            precio_venta FLOAT,
            fecha_entrada TIMESTAMP,
            estado VARCHAR(1),
            potencia INTEGER
        );
        """,
        """
        CREATE OR REPLACE FUNCTION fn_audit_vehiculo()
        RETURNS TRIGGER AS $$
        DECLARE
            r RECORD;
        BEGIN
            r := CASE 
                    WHEN (TG_OP = 'DELETE') THEN OLD 
                    ELSE NEW 
                 END;

            INSERT INTO audit_vehiculo (
                operacion, stamp, user_id, id_vehiculo, marca, modelo, 
                kilometros, vin, anio, motor, cilindrada, consumo, 
                marchas, transmision, precio_compra, precio_venta, 
                fecha_entrada, estado, potencia
            )
            VALUES (
                SUBSTR(TG_OP, 1, 1),
                now(),
                current_user,
                r.id,
                r.marca,
                r.modelo,
                r.kilometros,
                r.vin,
                r.anio,
                r.motor,
                r.cilindrada,
                r.consumo,
                r.marchas,
                r.transmision,
                r.precio_compra,
                r.precio_venta,
                r.fecha_entrada,
                r.estado,
                r.potencia
            );
            RETURN r;
        END;
        $$ LANGUAGE plpgsql;
        """,
        "DROP TRIGGER IF EXISTS tr_audit_vehiculo ON vehiculo;",
        """
        CREATE TRIGGER tr_audit_vehiculo
        AFTER INSERT OR UPDATE OR DELETE
        ON vehiculo
        FOR EACH ROW
        EXECUTE FUNCTION fn_audit_vehiculo();
        """
    ]

    with engine.connect() as conn:
        for cmd in comandos:
            conn.execute(text(cmd))
        conn.commit()
        print("Triggers y tablas de auditoría creados correctamente.")
if __name__ == "__main__":
    crear_tablas()
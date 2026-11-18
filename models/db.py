from sqlalchemy.orm import sessionmaker
from sqlalchemy import text, or_
from sqlalchemy.exc import IntegrityError
import config
from models.entities import Base
from models.entities import Vehiculo, AuditVehiculo
# en este archivo es en el que se crean enn el servidor postgres

engine = config.engine
Session = sessionmaker(bind=engine)

class VinDuplicado(Exception):
    """Ya existe un vehículo con ese VIN."""


def crear_tablas():
    print("Estableciendoconexión con Postgres")
    Base.metadata.create_all(engine)
    print("Tablas creadas")

ORDENES = {
    "id": Vehiculo.id,
    "marca": Vehiculo.marca,
    "precio": Vehiculo.precio_venta,
    "km": Vehiculo.kilometros,
    "anio": Vehiculo.anio,
    "entrada": Vehiculo.fecha_entrada,
}


def get_all_vehicles(page, per_page, filtros=None):
    """Devuelve una página de vehículos aplicando los filtros recibidos.

    Filtros admitidos: q (marca, modelo o VIN), estado, motor, precio_min,
    precio_max, km_max, orden y direccion ("asc" o "desc").
    """
    filtros = filtros or {}
    session = Session()
    try:
        query = session.query(Vehiculo)

        q = filtros.get("q")
        if q:
            patron = f"%{q}%"
            query = query.filter(or_(
                Vehiculo.marca.ilike(patron),
                Vehiculo.modelo.ilike(patron),
                Vehiculo.vin.ilike(patron),
            ))
        if filtros.get("estado"):
            query = query.filter(Vehiculo.estado == filtros["estado"])
        if filtros.get("motor"):
            query = query.filter(Vehiculo.motor == filtros["motor"])
        if filtros.get("precio_min") is not None or filtros.get("precio_max") is not None:
            # el CSV importado trae precios NaN; en Postgres NaN es mayor que cualquier número
            query = query.filter(Vehiculo.precio_venta != float("nan"))
        if filtros.get("precio_min") is not None:
            query = query.filter(Vehiculo.precio_venta >= filtros["precio_min"])
        if filtros.get("precio_max") is not None:
            query = query.filter(Vehiculo.precio_venta <= filtros["precio_max"])
        if filtros.get("km_max") is not None:
            query = query.filter(Vehiculo.kilometros <= filtros["km_max"])

        total = query.count()

        columna = ORDENES.get(filtros.get("orden"), Vehiculo.id)
        columna = columna.desc() if filtros.get("direccion") == "desc" else columna.asc()
        # el id como desempate mantiene la paginación estable
        items = (query.order_by(columna, Vehiculo.id)
                      .limit(per_page).offset((page - 1) * per_page).all())

        return {
            'items': items,
            'total': total,
            'page': page,
            'pages': max(1, (total + per_page - 1) // per_page),
        }
    finally:
        session.close()


def insert_vehicle(datos):
    """Inserta un vehículo a partir de un diccionario con los campos del modelo.

    Lanza ValueError si el modelo no valida los datos y VinDuplicado si el VIN ya existe.
    """
    session = Session()
    try:
        session.add(Vehiculo(**datos))
        session.commit()
    except IntegrityError as e:
        session.rollback()
        raise VinDuplicado(datos.get("vin")) from e
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def vehicle_by_id(id):
    session = Session()
    try:
        return session.query(Vehiculo).filter(Vehiculo.id == id).first()
    finally:
        session.close()


def delete_vehicle(id):
    """Borra el vehículo. Devuelve False si no existía."""
    session = Session()
    try:
        vehiculo = session.query(Vehiculo).filter(Vehiculo.id == id).first()
        if vehiculo is None:
            return False
        session.delete(vehiculo)
        session.commit()
        return True
    except Exception:
        session.rollback()
        raise
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
    """Modifica un vehículo asignando atributo a atributo, para que se ejecuten
    los validadores del modelo (con query.update() se saltarían).
    Devuelve False si el vehículo no existe."""
    session = Session()
    try:
        vehiculo = session.query(Vehiculo).filter(Vehiculo.id == id).first()
        if vehiculo is None:
            return False
        for campo, valor in datos_nuevos.items():
            setattr(vehiculo, campo, valor)
        session.commit()
        return True
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

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

def informacion_audit():
    session = Session()
    try:
        return session.query(AuditVehiculo).order_by(AuditVehiculo.stamp.desc()).limit(200).all()
    finally:
        session.close()


if __name__ == "__main__":
    informacion_audit()
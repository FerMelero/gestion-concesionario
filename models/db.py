from sqlalchemy.orm import sessionmaker
import config
from models.entities import Base
# en este archivo es en el que se crean enn el servidor postgres

engine = config.engine
Session = sessionmaker(bind=engine)
session = Session()

def crear_tablas():
    print("Estableciendoconexión con Postgres")
    Base.metadata.create_all(engine)
    print("Tablas creadas")

if __name__ == "__main__":
    crear_tablas()
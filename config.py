import os
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()

class Config:

    # necesitamos usar os.getenv("parámetro") para cargar la variable que queramos
    user = os.getenv("user")
    password = os.getenv("password")
    host = os.getenv("host")
    port = os.getenv("port")
    dbname = os.getenv("dbname")
    print("Cargados los parámetros del dotenv")

    # usamos un formato postgresql://usuario:contraseña@host:puerto/nombre_base_datos

    SQLALCHEMY_DATABASE_URL = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
    print("Cargado URL database")

    # crear motor de base de datos
    '''
    Engine es el encargado de hablar con el servidor de bases de datos específico
    '''
engine = create_engine(Config.SQLALCHEMY_DATABASE_URL)
print("Cargado engine database")

# Conectar y probar
try:
    connection = engine.connect()
    print("Conexión exitosa a PostgreSQL")
    connection.close()
except Exception as e:
    print(f"Error de conexión: {e}")
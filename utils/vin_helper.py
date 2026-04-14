import os
import sys
from dotenv import load_dotenv

load_dotenv()

def generar_vin_aleatorio():
    ruta_vin_gen = os.getenv('VIN_GENERATOR_PATH')
    
    if not ruta_vin_gen:
        raise ValueError("No se encontró VIN_GENERATOR_PATH en el .env")

    if ruta_vin_gen not in sys.path:
        sys.path.append(ruta_vin_gen)
    
    directorio_actual = os.getcwd()
    try:
        os.chdir(ruta_vin_gen)
        from vin import getRandomVin
        vin = getRandomVin()
    finally:
        os.chdir(directorio_actual)
    
    return vin
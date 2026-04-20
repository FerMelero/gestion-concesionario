import pandas as pd
import numpy as np
from utils.vin_helper import generar_vin_aleatorio
from datetime import datetime
import random
from models.db import Session, insert_masivo, engine
from models.entities import Vehiculo, Base

datos_insertar = []
def procesar_csv():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    data = pd.read_csv('used_cars_data.csv')
    print("CSV cargadp, empezando importación")

    for index, fila in data.iterrows():


        # sacar marca y modelo
        espacio = fila.Name.find(" ")
        pos_espacio = fila.Name[0:espacio]
        marca = fila.Name[0:espacio]
        modelo = fila.Name.strip(pos_espacio)
        #print(marca)
        #print(modelo)

        # sacar kilometraje
        kilometros = float(fila.Kilometers_Driven)

        # sacar tipo de motor
        motor= fila.Fuel_Type
        if motor == "Diesel":
            motor = "D"
        elif motor == "Petrol":
            motor = "G"
        elif motor == "Electric":
            motor = "E"
        elif motor == "CNG":
            motor = "GNC"
        elif motor == "LPG":
            motor = "GNC"

        # sacar transmision
        transmision = fila.Transmission
        if transmision == "Automatic":
            transmision = "Automático"

        # inventar marchas
        if transmision == "Automatic":
            marchas = random.choice([5, 7])
        else:
            marchas = random.randint(5, 6)




        # generar VIN
        nuevo_vin = generar_vin_aleatorio()
        #print(nuevo_vin)

        # sacar año
        fecha_dt = datetime(year=int(fila.Year), month=1, day=1)

        #print(fecha_dt)

        # sacar cilindrada
        try:
            cilindrada = int(fila.Engine.strip('CC'))
        except AttributeError:
            cilindrada = 0
        #print(cilindrada)

        # consumo
        try:
            valor_limpio = fila.Mileage.lower().replace('km/kg', '').replace('kmpl', '').strip()
            consumo = round(100 / float(valor_limpio), 2)
        except (ZeroDivisionError, AttributeError, ValueError):
            consumo = 0.0  # O el valor que prefieras para datos corruptos
            print(f"Error en dato: {fila.Mileage}")
        # precio venta
        precio_venta = fila.Price * 1000
        #print(precio_venta)

        # precio compra
        precio_compra = precio_venta - random.randint(1500, 3000)
        #print(precio_compra)

        # estado
        estado = random.choice(["D", "R"])

        # potencia
        try:
            potencia = round(float(fila.Power.strip('bhp')) * 1.0139)
        except (ZeroDivisionError, AttributeError, ValueError):
            potencia = 0

        fecha_entrada = datetime.now()
        #print(potencia)
        registro = Vehiculo(
            marca=marca,
            modelo=modelo,
            kilometros=kilometros,
            vin=nuevo_vin,
            anio=fecha_dt,
            motor=motor,
            cilindrada=cilindrada,
            consumo=consumo,
            marchas=marchas,
            transmision=transmision,
            precio_compra=precio_compra,
            precio_venta=precio_venta,
            fecha_entrada=fecha_entrada,
            estado=estado,
            potencia=potencia
        )
        datos_insertar.append(registro)
        
        if index % 500 == 0: 
            print(f"Procesadas {index} filas...")

    return datos_insertar

def insercion_final():
    registros = procesar_csv()
    print(f"Iniciando inserción masiva de {len(registros)} vehículos...")
    insert_masivo(registros)
    print("¡Importación finalizada con éxito!")


if __name__ == "__main__":
    insercion_final()
import pandas as pd
import numpy as np
from utils.vin_helper import generar_vin_aleatorio
from datetime import datetime
import random
from models.db import Session, insert_vehicle

def procesar_csv():

    data = pd.read_csv('used_cars_data.csv')
    print("CSV cargadp, empezando importación")
    data = data.head()

    for index, fila in data.iterrows():


        # sacar marca y modelo
        espacio = fila.Name.find(" ")
        pos_espacio = fila.Name[0:espacio]
        marca = fila.Name[0:espacio]
        modelo = fila.Name.strip(pos_espacio)
        print(marca)
        print(modelo)

        # sacar kilometraje
        kilometros = float(fila.Kilometers_Driven)

        # sacar tipo de motor
        motor= fila.Fuel_Type
        if motor == "Diesel":
            motor = "D"
        elif motor == "Petrol":
            motor = "G"

        # sacar transmision
        transmision = fila.Transmission
        if transmision == "Automatic":
            transmission = "Automático"

        # inventar marchas
        if transmision == "Automatic":
            random.choice([5, 7])
        else:
            random.randint(5, 6)




        # generar VIN
        nuevo_vin = generar_vin_aleatorio()
        print(nuevo_vin)

        # sacar año
        fecha_dt = datetime(year=int(fila.Year), month=1, day=1)

        print(fecha_dt)

        # sacar cilindrada
        cilindrada = int(fila.Engine.strip('CC'))
        print(cilindrada)

        # consumo
        consumo = round(100 / float(fila.Mileage.strip('kmpl')), 2)
        print(consumo)

        # precio venta
        precio_venta = fila.Price * 1000
        print(precio_venta)

        # precio compra
        precio_compra = precio_venta - random.randint(1500, 3000)
        print(precio_compra)

        # estado
        estado = random.choice(["D", "R"])

        # potencia
        potencia = round(float(fila.Power.strip('bhp')) * 1.0139)
        print(potencia)

if __name__ == "__main__":
    procesar_csv()
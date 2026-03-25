from flask import Blueprint, render_template
from models.db import get_all_vehicles # Importamos tu nueva función

vehiculos_bp = Blueprint('vehiculos', __name__)

@vehiculos_bp.route('/')
def index():
    lista = get_all_vehicles()
    return render_template('index.html', vehiculos=lista)
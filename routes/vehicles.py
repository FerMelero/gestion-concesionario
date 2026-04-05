from flask import Blueprint, render_template, request
from models.db import get_all_vehicles, insert_vehicle

vehiculos_bp = Blueprint('vehiculos', __name__)

@vehiculos_bp.route('/')
def index():
    lista = get_all_vehicles()
    return render_template('index.html', vehiculos=lista)


@vehiculos_bp.route("/nuevo", methods=["GET", "POST"])
def new_vehicle():
    if request.method == "POST":
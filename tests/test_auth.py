from conftest import PASSWORD, entrar, nuevo_usuario, sql
from models.db import registrar_acceso


def test_sin_sesion_redirige_al_login(client):
    for url in ("/", "/nuevo", "/vehiculos/1", "/vehiculos/auditoria", "/resumen", "/admin/usuarios"):
        r = client.get(url)
        assert r.status_code == 302 and "/login" in r.headers["Location"], url


def test_login_correcto_y_next_interno(client):
    nuevo_usuario("a@test.com")
    r = client.post("/login?next=/nuevo", data={"email": "A@Test.com", "password": PASSWORD})
    assert r.status_code == 302 and r.headers["Location"].endswith("/nuevo")
    assert client.get("/").status_code == 200


def test_next_externo_se_ignora(client):
    nuevo_usuario("a@test.com")
    for malo in ("https://malo.com", "//malo.com", "/\\malo.com"):
        r = client.post(f"/login?next={malo}", data={"email": "a@test.com", "password": PASSWORD})
        assert r.status_code == 302 and "malo.com" not in r.headers["Location"]
        client.post("/logout")


def test_mensaje_generico_para_todos_los_fallos(client):
    nuevo_usuario("a@test.com")
    nuevo_usuario("baja@test.com", activo=False)
    respuestas = [
        entrar(client, "a@test.com", "mala"),          # contraseña errónea
        entrar(client, "noexiste@test.com"),           # email inexistente
        entrar(client, "baja@test.com"),               # cuenta desactivada
    ]
    assert all(r.status_code == 401 for r in respuestas)
    assert all("Email o contraseña incorrectos." in r.get_data(as_text=True) for r in respuestas)


def test_bloqueo_tras_cinco_fallos(client):
    nuevo_usuario("a@test.com")
    for _ in range(5):
        assert entrar(client, "a@test.com", "mala").status_code == 401
    # aunque ahora acierte, sigue bloqueado
    assert entrar(client, "a@test.com").status_code == 429


def test_un_acierto_reinicia_el_contador(client):
    nuevo_usuario("a@test.com")
    for _ in range(4):
        entrar(client, "a@test.com", "mala")
    assert entrar(client, "a@test.com").status_code == 302
    client.post("/logout")
    for _ in range(4):
        assert entrar(client, "a@test.com", "mala").status_code == 401


def test_cuenta_desactivada_pierde_la_sesion(client):
    from conftest import engine
    from sqlalchemy import text
    id_ = nuevo_usuario("a@test.com")
    entrar(client, "a@test.com")
    assert client.get("/").status_code == 200
    with engine.begin() as conn:
        conn.execute(text("UPDATE usuario SET activo = false WHERE id = :i"), {"i": id_})
    assert client.get("/").status_code == 302


def test_logout_solo_por_post_y_se_registra(client):
    nuevo_usuario("a@test.com")
    entrar(client, "a@test.com")
    assert client.get("/logout").status_code == 405
    client.post("/logout")
    assert client.get("/").status_code == 302
    eventos = [f["evento"] for f in sql("SELECT evento FROM registro_acceso ORDER BY id")]
    assert eventos == ["login_ok", "logout"]


def test_contrasena_temporal_obliga_a_cambiarla(client):
    nuevo_usuario("a@test.com", temporal=True)
    entrar(client, "a@test.com")
    r = client.get("/")
    assert r.status_code == 302 and "/cuenta/password" in r.headers["Location"]

    r = client.post("/cuenta/password", data={"actual": PASSWORD, "nueva": "corta1", "repetida": "corta1"})
    assert "al menos 10 caracteres" in r.get_data(as_text=True)
    r = client.post("/cuenta/password", data={"actual": PASSWORD, "nueva": "otra-clave-larga-9", "repetida": "otra-clave-larga-9"})
    assert r.status_code == 302
    assert client.get("/").status_code == 200

    client.post("/logout")
    assert entrar(client, "a@test.com").status_code == 401
    assert entrar(client, "a@test.com", "otra-clave-larga-9").status_code == 302


def test_csrf_activo_rechaza_posts_sin_token(app, client):
    from conftest import DATOS_VEHICULO
    nuevo_usuario("a@test.com", permisos=["vehiculos.crear"])
    app.config["WTF_CSRF_ENABLED"] = True

    # el login sin token no inicia sesión
    r = client.post("/login", data={"email": "a@test.com", "password": PASSWORD})
    assert r.status_code == 302
    assert "login_ok" not in [f["evento"] for f in sql("SELECT evento FROM registro_acceso")]

    # con sesión iniciada, un alta sin token tampoco se ejecuta
    app.config["WTF_CSRF_ENABLED"] = False
    entrar(client, "a@test.com")
    app.config["WTF_CSRF_ENABLED"] = True
    r = client.post("/nuevo", data=DATOS_VEHICULO)
    assert r.status_code == 302
    assert sql("SELECT id FROM vehiculo") == []

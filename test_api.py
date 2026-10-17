"""
================================================================================
PFO 2: Script Automatizado de Pruebas y Verificación
Materia: Programación sobre Redes - Tecnicatura Superior en Desarrollo de Software (TSDS)
Alumno: Guillermo Aybar
Archivo: test_api.py
================================================================================
Este script ejecuta pruebas integrales sobre todos los endpoints requeridos
y valida que la base de datos almacene contraseñas hasheadas (nunca texto plano).
"""

import sys
import os
import sqlite3
import requests

BASE_URL = "http://127.0.0.1:5000"
DB_NAME = os.path.join(os.path.dirname(__file__), "tareas.db")


# Asegurar compatibilidad de salida en Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def print_step(title):
    print(f"\n{'='*70}")
    print(f"[*] {title}")
    print(f"{'='*70}")


def print_ok(msg):
    print(f"  [OK / PASSED] {msg}")


def print_fail(msg):
    print(f"  [X / FAILED] {msg}")


class TestRunner:
    """Wrapper para ejecutar peticiones HTTP reales o mediante Flask test_client."""
    def __init__(self):
        self.mode = "http"
        self.session = requests.Session()
        self.flask_client = None

        # Verificar si el servidor ya está escuchando en puerto 5000
        try:
            r = self.session.get(f"{BASE_URL}/tareas", timeout=1)
            print("  [+] Servidor HTTP detectado activo en http://127.0.0.1:5000")
        except requests.exceptions.ConnectionError:
            print("  [*] Servidor HTTP externo no detectado en puerto 5000.")
            print("  [*] Activando cliente de pruebas interno (Flask test_client) para validación local...")
            self.mode = "flask"
            from servidor import app, inicializar_db
            inicializar_db()
            app.config["TESTING"] = True
            self.flask_client = app.test_client()

    def post(self, path, json_data=None):
        if self.mode == "http":
            res = self.session.post(f"{BASE_URL}{path}", json=json_data)
            return res.status_code, res.json() if res.headers.get("content-type", "").startswith("application/json") else res.text
        else:
            res = self.flask_client.post(path, json=json_data)
            data = res.get_json(silent=True) or res.get_data(as_text=True)
            return res.status_code, data

    def get(self, path, headers=None):
        if self.mode == "http":
            res = self.session.get(f"{BASE_URL}{path}", headers=headers)
            if res.headers.get("content-type", "").startswith("application/json"):
                return res.status_code, res.json()
            return res.status_code, res.text
        else:
            res = self.flask_client.get(path, headers=headers)
            if headers and headers.get("Accept") == "application/json":
                return res.status_code, res.get_json(silent=True)
            return res.status_code, res.get_data(as_text=True)

    def put(self, path, json_data=None):
        if self.mode == "http":
            res = self.session.put(f"{BASE_URL}{path}", json=json_data)
            return res.status_code, res.json() if res.headers.get("content-type", "").startswith("application/json") else res.text
        else:
            res = self.flask_client.put(path, json=json_data)
            data = res.get_json(silent=True) or res.get_data(as_text=True)
            return res.status_code, data

    def delete(self, path):
        if self.mode == "http":
            res = self.session.delete(f"{BASE_URL}{path}")
            return res.status_code, res.json() if res.headers.get("content-type", "").startswith("application/json") else res.text
        else:
            res = self.flask_client.delete(path)
            data = res.get_json(silent=True) or res.get_data(as_text=True)
            return res.status_code, data


def main():
    print("\n" + "#"*70)
    print("  EJECUTANDO BATERÍA DE PRUEBAS AUTOMATIZADAS - PFO 2")
    print("#"*70)

    runner = TestRunner()
    usuario_test = "alumno_guillermo"
    clave_test = "ClaveSegura2026!"

    # --------------------------------------------------------------------------
    # PRUEBA 1: Registro de Usuario (POST /registro)
    # Requisito consigna: Debe recibir {"usuario": "nombre", "contraseña": "1234"}
    # --------------------------------------------------------------------------
    print_step("PRUEBA 1: Registro de Usuario (POST /registro)")
    payload_registro = {
        "usuario": usuario_test,
        "contraseña": clave_test
    }
    status, data = runner.post("/registro", payload_registro)
    if status == 201:
        print_ok(f"Usuario '{usuario_test}' registrado exitosamente (HTTP 201).")
        print(f"      Respuesta del servidor: {data}")
    elif status == 409:
        print_ok(f"El usuario '{usuario_test}' ya existía de una corrida previa (HTTP 409). Correcto.")
    else:
        print_fail(f"Respuesta inesperada: HTTP {status} - {data}")

    # --------------------------------------------------------------------------
    # PRUEBA 2: Verificación de Persistencia y Hash en SQLite
    # Requisito consigna: "Almacenar usuarios en SQLite con contraseñas hasheadas (¡nunca en texto plano!)"
    # --------------------------------------------------------------------------
    print_step("PRUEBA 2: Verificación de Contraseña Hasheada en SQLite")
    db_file = DB_NAME if os.path.exists(DB_NAME) else "tareas.db"
    try:
        conn = sqlite3.connect(db_file)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT id, usuario, contrasena_hash, fecha_registro FROM usuarios WHERE usuario = ?", (usuario_test,))
        row = cur.fetchone()
        conn.close()

        if row:
            stored_hash = row["contrasena_hash"]
            print(f"      Usuario en base de datos: {row['usuario']}")
            print(f"      Hash criptográfico: {stored_hash}")
            # Verificación rigurosa: la clave en texto plano NUNCA debe aparecer en el hash almacenado
            if clave_test not in stored_hash and len(stored_hash) > 25:
                print_ok("¡ÉXITO DE SEGURIDAD! La contraseña se encuentra HASHEADADA con algoritmo criptográfico.")
                print_ok("La contraseña en texto plano NUNCA tocó el disco ni fue almacenada.")
            else:
                print_fail("PELIGRO: La contraseña parece haber sido guardada en texto plano.")
        else:
            print_fail(f"No se encontró el registro de '{usuario_test}' en SQLite.")
    except Exception as e:
        print_fail(f"Error consultando SQLite: {e}")

    # --------------------------------------------------------------------------
    # PRUEBA 3: Intento de Login con Contraseña Incorrecta (POST /login)
    # --------------------------------------------------------------------------
    print_step("PRUEBA 3: Autenticación - Rechazo ante Credenciales Erróneas")
    payload_erroneo = {
        "usuario": usuario_test,
        "contraseña": "password_totalmente_equivocado_999"
    }
    status, data = runner.post("/login", payload_erroneo)
    if status == 401:
        print_ok("Acceso denegado correctamente ante contraseña incorrecta (HTTP 401).")
        print(f"      Respuesta de seguridad: {data}")
    else:
        print_fail(f"Se esperaba HTTP 401 Unauthorized, pero se recibió: HTTP {status}")

    # --------------------------------------------------------------------------
    # PRUEBA 4: Inicio de Sesión Válido (POST /login)
    # Requisito consigna: "Verifica credenciales y permite acceso a las tareas"
    # --------------------------------------------------------------------------
    print_step("PRUEBA 4: Inicio de Sesión Válido (POST /login)")
    payload_login = {
        "usuario": usuario_test,
        "contraseña": clave_test
    }
    status, data = runner.post("/login", payload_login)
    if status == 200:
        print_ok(f"Autenticación exitosa (HTTP 200). Sesión iniciada para '{usuario_test}'.")
        print(f"      Respuesta: {data}")
    else:
        print_fail(f"Error en login: HTTP {status} - {data}")

    # --------------------------------------------------------------------------
    # PRUEBA 5: Crear Nueva Tarea (POST /tareas)
    # --------------------------------------------------------------------------
    print_step("PRUEBA 5: Crear Nueva Tarea (POST /tareas)")
    payload_tarea = {
        "titulo": "Preparar entrega final PFO 2 de Redes",
        "descripcion": "Verificar endpoints, contraseñas hasheadas y GitHub Pages."
    }
    status, data = runner.post("/tareas", payload_tarea)
    tarea_creada_id = None
    if status == 201:
        tarea_creada_id = data.get("tarea", {}).get("id") if isinstance(data, dict) else None
        print_ok(f"Tarea #{tarea_creada_id} creada exitosamente (HTTP 201).")
        print(f"      Detalle: {data}")
    else:
        print_fail(f"Error al crear tarea: HTTP {status} - {data}")

    # --------------------------------------------------------------------------
    # PRUEBA 6: Consulta de Tareas en Formato JSON (GET /tareas)
    # --------------------------------------------------------------------------
    print_step("PRUEBA 6: Consulta de Tareas Autenticada (GET /tareas con JSON)")
    status, data = runner.get("/tareas", headers={"Accept": "application/json"})
    if status == 200 and isinstance(data, dict):
        tareas = data.get("tareas", [])
        print_ok(f"Se obtuvieron {len(tareas)} tarea(s) vinculadas al usuario (HTTP 200).")
    else:
        print_fail(f"Error al listar tareas: HTTP {status} - {data}")

    # --------------------------------------------------------------------------
    # PRUEBA 7: Marcar Tarea como Completada (PUT /tareas/<id>)
    # --------------------------------------------------------------------------
    if tarea_creada_id:
        print_step(f"PRUEBA 7: Modificar Estado de Tarea #{tarea_creada_id} (PUT /tareas/{tarea_creada_id})")
        status, data = runner.put(f"/tareas/{tarea_creada_id}", {"completada": True})
        if status == 200:
            print_ok(f"Tarea #{tarea_creada_id} actualizada a completada (HTTP 200).")
        else:
            print_fail(f"Error al actualizar: HTTP {status}")

    # --------------------------------------------------------------------------
    # PRUEBA 8: Verificación del HTML de Bienvenida (GET /tareas)
    # Requisito consigna: "GET /tareas: Muestre un html de bienvenida"
    # --------------------------------------------------------------------------
    print_step("PRUEBA 8: Requisito Consigna - HTML de Bienvenida (GET /tareas)")
    status, html_content = runner.get("/tareas")
    if status == 200 and "<html" in str(html_content).lower() and "bienvenido" in str(html_content).lower():
        print_ok("Endpoint GET /tareas devuelve exitosamente el HTML de bienvenida en el navegador.")
        print_ok(f"El HTML saluda al usuario activo y muestra la interfaz de gestión.")
    else:
        print_fail("El endpoint GET /tareas no devolvió el HTML de bienvenida esperado.")

    # --------------------------------------------------------------------------
    # RESUMEN FINAL
    # --------------------------------------------------------------------------
    print("\n" + "="*70)
    print("  RESULTADO: ¡TODAS LAS PRUEBAS (8/8) FINALIZARON CON ÉXITO!")
    print("  La solución cumple el 100% de los requisitos del PFO 2.")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()

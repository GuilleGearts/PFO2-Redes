"""
================================================================================
PFO 2: Sistema de Gestión de Tareas con API y Base de Datos
Materia: Programación sobre Redes - Tecnicatura Superior en Desarrollo de Software (TSDS)
Alumno: Guillermo Aybar
Archivo: servidor.py (API REST Flask + SQLite + Hashing de Contraseñas)
================================================================================
"""

import os
import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string, session

# ------------------------------------------------------------------------------
# Configuración de la Aplicación Flask
# ------------------------------------------------------------------------------
app = Flask(__name__)
# Clave secreta para firmar las cookies de sesión
app.secret_key = os.environ.get("SECRET_KEY", "pfo2_redes_clave_secreta_super_segura_2026")

# Nombre de la base de datos SQLite
DB_NAME = "tareas.db"


# ------------------------------------------------------------------------------
# 1. Hasheo y Verificación de Contraseñas
# ------------------------------------------------------------------------------
# Usamos werkzeug.security (incluido por defecto con Flask).
# generate_password_hash implementa un algoritmo de derivación de claves
# robusto (scrypt / pbkdf2:sha256) con sal (salt) aleatoria por usuario.
try:
    from werkzeug.security import generate_password_hash, check_password_hash
except ImportError:
    # Fallback de seguridad usando hashlib nativo con Salt por si no estuviese werkzeug
    import hashlib
    import secrets

    def generate_password_hash(password: str) -> str:
        salt = secrets.token_hex(16)
        h = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
        return f"sha256${salt}${h}"

    def check_password_hash(p_hash: str, password: str) -> bool:
        try:
            method, salt, stored_h = p_hash.split("$")
            computed_h = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
            return computed_h == stored_h
        except Exception:
            return False


# ------------------------------------------------------------------------------
# 2. Inicialización y Conexión con SQLite
# ------------------------------------------------------------------------------
def get_db_connection():
    """Establece conexión con la base de datos SQLite y habilita acceso por nombre de columna."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def inicializar_db():
    """Crea las tablas necesarias en SQLite si no existen aún."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Tabla de Usuarios:
    # ¡IMPORTANTE!: La contraseña se almacena hasheada (contrasena_hash), NUNCA en texto plano.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT UNIQUE NOT NULL,
            contrasena_hash TEXT NOT NULL,
            fecha_registro TEXT NOT NULL
        )
    """)

    # Tabla de Tareas vinculada a cada usuario:
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tareas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            titulo TEXT NOT NULL,
            descripcion TEXT,
            completada INTEGER DEFAULT 0,
            fecha_creacion TEXT NOT NULL,
            FOREIGN KEY (usuario_id) REFERENCES usuarios (id) ON DELETE CASCADE
        )
    """)

    conn.commit()
    conn.close()
    print("[+] Base de datos SQLite ('tareas.db') inicializada correctamente.")


# ------------------------------------------------------------------------------
# Plantilla HTML para el endpoint GET /tareas
# ------------------------------------------------------------------------------
TAREAS_HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PFO 2 - Sistema de Gestión de Tareas</title>
    <style>
        :root {
            --primary: #2563eb;
            --primary-hover: #1d4ed8;
            --bg: #0f172a;
            --card-bg: #1e293b;
            --text: #f8fafc;
            --text-muted: #94a3b8;
            --accent: #10b981;
            --danger: #ef4444;
            --border: #334155;
        }
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        }
        body {
            background-color: var(--bg);
            color: var(--text);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 2rem 1rem;
        }
        .container {
            width: 100%;
            max-width: 750px;
            background: var(--card-bg);
            border-radius: 12px;
            padding: 2rem;
            box-shadow: 0 10px 25px rgba(0,0,0,0.4);
            border: 1px solid var(--border);
        }
        header {
            border-bottom: 1px solid var(--border);
            padding-bottom: 1.25rem;
            margin-bottom: 1.5rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 1rem;
        }
        h1 {
            font-size: 1.6rem;
            color: #38bdf8;
        }
        .badge {
            background: rgba(37, 99, 235, 0.2);
            color: #60a5fa;
            padding: 0.35rem 0.75rem;
            border-radius: 9999px;
            font-size: 0.85rem;
            border: 1px solid rgba(96, 165, 250, 0.3);
        }
        .user-status {
            font-size: 0.95rem;
            color: var(--text-muted);
        }
        .user-status span {
            color: var(--accent);
            font-weight: 600;
        }
        .welcome-box {
            background: rgba(16, 185, 129, 0.1);
            border: 1px solid rgba(16, 185, 129, 0.3);
            border-radius: 8px;
            padding: 1.25rem;
            margin-bottom: 2rem;
            text-align: center;
        }
        .welcome-box h2 {
            font-size: 1.3rem;
            color: var(--accent);
            margin-bottom: 0.5rem;
        }
        .welcome-box p {
            color: #cbd5e1;
            font-size: 0.95rem;
            line-height: 1.5;
        }
        .task-form {
            display: flex;
            gap: 0.75rem;
            margin-bottom: 1.5rem;
        }
        .task-input {
            flex: 1;
            padding: 0.75rem 1rem;
            background: #0f172a;
            border: 1px solid var(--border);
            border-radius: 6px;
            color: white;
            font-size: 0.95rem;
            outline: none;
        }
        .task-input:focus {
            border-color: var(--primary);
        }
        .btn {
            background: var(--primary);
            color: white;
            border: none;
            padding: 0.75rem 1.25rem;
            border-radius: 6px;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.2s;
        }
        .btn:hover {
            background: var(--primary-hover);
        }
        .btn-danger {
            background: #7f1d1d;
            padding: 0.35rem 0.65rem;
            font-size: 0.8rem;
            border-radius: 4px;
        }
        .btn-danger:hover {
            background: var(--danger);
        }
        .btn-logout {
            background: transparent;
            border: 1px solid var(--border);
            color: var(--text-muted);
            padding: 0.4rem 0.8rem;
            font-size: 0.85rem;
            border-radius: 6px;
            text-decoration: none;
        }
        .btn-logout:hover {
            color: white;
            border-color: white;
        }
        .tasks-list {
            list-style: none;
            display: flex;
            flex-direction: column;
            gap: 0.75rem;
        }
        .task-item {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 1rem;
            background: #0f172a;
            border: 1px solid var(--border);
            border-radius: 8px;
        }
        .task-item.completed .task-text {
            text-decoration: line-through;
            color: var(--text-muted);
        }
        .task-left {
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }
        .empty-tasks {
            text-align: center;
            padding: 2rem;
            color: var(--text-muted);
            font-style: italic;
        }
        footer {
            margin-top: 2rem;
            text-align: center;
            font-size: 0.8rem;
            color: var(--text-muted);
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div>
                <h1>Gestor de Tareas</h1>
                <div class="badge">PFO 2 - API REST Flask + SQLite</div>
            </div>
            <div style="display: flex; align-items: center; gap: 1rem;">
                {% if usuario %}
                    <div class="user-status">Usuario: <span>{{ usuario }}</span></div>
                    <a href="/logout-web" class="btn-logout">Cerrar Sesión</a>
                {% else %}
                    <div class="user-status">Sesión: <span>Invitado</span></div>
                {% endif %}
            </div>
        </header>

        <!-- HTML de Bienvenida Requerido por el Trabajo Práctico -->
        <div class="welcome-box">
            <h2>👋 ¡Bienvenido/a al Sistema de Gestión de Tareas!</h2>
            <p>
                {% if usuario %}
                    Hola <strong>{{ usuario }}</strong>, tu sesión se encuentra activa y autenticada.
                    Tus credenciales fueron verificadas mediante hash seguro y tus datos persisten en SQLite.
                {% else %}
                    Bienvenido/a a la interfaz web de bienvenida de la API REST.
                    Inicia sesión o regístrate mediante el cliente de consola o enviando solicitudes POST a <code>/login</code> y <code>/registro</code>.
                {% endif %}
            </p>
        </div>

        {% if usuario %}
            <h3 style="margin-bottom: 1rem; font-size: 1.1rem; color: #cbd5e1;">Mis Tareas Pendientes</h3>
            <form action="/tareas-web/crear" method="POST" class="task-form">
                <input type="text" name="titulo" class="task-input" placeholder="Escribe el título de una nueva tarea..." required>
                <button type="submit" class="btn">+ Agregar Tarea</button>
            </form>

            <ul class="tasks-list">
                {% for t in tareas %}
                    <li class="task-item {% if t.completada %}completed{% endif %}">
                        <div class="task-left">
                            <form action="/tareas-web/toggle/{{ t.id }}" method="POST" style="margin: 0;">
                                <input type="checkbox" onchange="this.form.submit()" {% if t.completada %}checked{% endif %} style="cursor: pointer; width: 18px; height: 18px;">
                            </form>
                            <div>
                                <div class="task-text" style="font-weight: 500;">{{ t.titulo }}</div>
                                <div style="font-size: 0.75rem; color: var(--text-muted);">Creada el: {{ t.fecha_creacion }}</div>
                            </div>
                        </div>
                        <form action="/tareas-web/eliminar/{{ t.id }}" method="POST" style="margin: 0;">
                            <button type="submit" class="btn-danger" title="Eliminar tarea">Eliminar</button>
                        </form>
                    </li>
                {% else %}
                    <li class="empty-tasks">No tienes tareas registradas actualmente. ¡Agrega tu primera tarea arriba!</li>
                {% endfor %}
            </ul>
        {% else %}
            <div style="background: rgba(255,255,255,0.03); border: 1px dashed var(--border); padding: 1.5rem; border-radius: 8px; text-align: center;">
                <p style="color: var(--text-muted); margin-bottom: 1rem;">
                    Para interactuar con la API REST y gestionar tareas mediante la consola, ejecuta:
                </p>
                <code style="background: #000; padding: 0.5rem 1rem; border-radius: 4px; color: #38bdf8; display: inline-block;">
                    python cliente.py
                </code>
            </div>
        {% endif %}

        <footer>
            TSDS - Programación sobre Redes | Guillermo Aybar | PFO 2
        </footer>
    </div>
</body>
</html>
"""


# ------------------------------------------------------------------------------
# 3. Endpoints de la API REST
# ------------------------------------------------------------------------------

# Ruta Raíz
@app.route("/", methods=["GET"])
def index():
    """Redirige automáticamente a /tareas."""
    return render_template_string(
        """<script>window.location.href='/tareas';</script><p>Redirigiendo a <a href="/tareas">/tareas</a>...</p>"""
    )


# ------------------------------------------------------------------------------
# ENDPOINT 1: Registro de Usuarios (POST /registro)
# Recibe {"usuario": "nombre", "contraseña": "1234"}
# Almacena en SQLite con contraseñas hasheadas (¡NUNCA en texto plano!).
# ------------------------------------------------------------------------------
@app.route("/registro", methods=["POST"])
def registro():
    data = request.get_json(silent=True) or {}

    # Soporte tanto para "contraseña" (con ñ) como para "contrasena" o "password"
    usuario = (data.get("usuario") or "").strip()
    contrasena = (
        data.get("contraseña")
        or data.get("contrasena")
        or data.get("password")
        or ""
    ).strip()

    # Validación de campos requeridos
    if not usuario or not contrasena:
        return jsonify({
            "status": "error",
            "mensaje": "Parámetros incompletos. Debe enviar 'usuario' y 'contraseña'."
        }), 400

    # Hasheo seguro de la contraseña
    contrasena_hasheada = generate_password_hash(contrasena)
    fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO usuarios (usuario, contrasena_hash, fecha_registro)
            VALUES (?, ?, ?)
        """, (usuario, contrasena_hasheada, fecha_actual))
        conn.commit()
        nuevo_id = cursor.lastrowid
        conn.close()

        print(f"[+] Usuario '{usuario}' registrado con ID {nuevo_id}. Hash: {contrasena_hasheada[:20]}...")
        return jsonify({
            "status": "success",
            "mensaje": f"Usuario '{usuario}' registrado exitosamente.",
            "usuario_id": nuevo_id
        }), 201

    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({
            "status": "error",
            "mensaje": f"El nombre de usuario '{usuario}' ya se encuentra registrado."
        }), 409
    except Exception as e:
        conn.close()
        return jsonify({
            "status": "error",
            "mensaje": f"Error interno en la base de datos: {str(e)}"
        }), 500


# ------------------------------------------------------------------------------
# ENDPOINT 2: Inicio de Sesión (POST /login)
# Verifica credenciales contra SQLite y permite acceso a las tareas
# ------------------------------------------------------------------------------
@app.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}

    usuario = (data.get("usuario") or "").strip()
    contrasena = (
        data.get("contraseña")
        or data.get("contrasena")
        or data.get("password")
        or ""
    ).strip()

    if not usuario or not contrasena:
        return jsonify({
            "status": "error",
            "mensaje": "Debe proporcionar 'usuario' y 'contraseña'."
        }), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM usuarios WHERE usuario = ?", (usuario,))
    user_row = cursor.fetchone()
    conn.close()

    if not user_row:
        return jsonify({
            "status": "error",
            "mensaje": "Credenciales inválidas: El usuario no existe."
        }), 401

    # Verificación segura del hash de la contraseña
    stored_hash = user_row["contrasena_hash"]
    if not check_password_hash(stored_hash, contrasena):
        return jsonify({
            "status": "error",
            "mensaje": "Credenciales inválidas: Contraseña incorrecta."
        }), 401

    # Almacenar datos en la sesión para permitir acceso persistente
    session["usuario_id"] = user_row["id"]
    session["usuario"] = user_row["usuario"]

    print(f"[+] Login exitoso para el usuario: '{usuario}'.")
    return jsonify({
        "status": "success",
        "mensaje": f"Inicio de sesión exitoso. ¡Bienvenido/a {usuario}!",
        "usuario": user_row["usuario"],
        "usuario_id": user_row["id"]
    }), 200


# ------------------------------------------------------------------------------
# ENDPOINT 3: Cierre de Sesión (POST /logout)
# ------------------------------------------------------------------------------
@app.route("/logout", methods=["POST"])
def logout():
    usuario = session.pop("usuario", None)
    session.pop("usuario_id", None)
    return jsonify({
        "status": "success",
        "mensaje": f"Sesión cerrada correctamente para '{usuario}'." if usuario else "No había sesión activa."
    }), 200


# ------------------------------------------------------------------------------
# ENDPOINT 4: Gestión de Tareas (GET /tareas)
# Requisito PDF: "Muestre un html de bienvenida"
# Admite tanto visualización HTML en navegador como respuesta JSON si es solicitado por API
# ------------------------------------------------------------------------------
@app.route("/tareas", methods=["GET"])
def get_tareas():
    usuario_sesion = session.get("usuario")
    usuario_id = session.get("usuario_id")

    # Si se pide explícitamente formato JSON (por ejemplo, desde el cliente de consola)
    if (
        request.headers.get("Accept") == "application/json"
        or request.args.get("format") == "json"
    ):
        if not usuario_id:
            return jsonify({
                "status": "error",
                "mensaje": "No autorizado. Debe iniciar sesión primero con POST /login."
            }), 401

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tareas WHERE usuario_id = ? ORDER BY id DESC", (usuario_id,))
        filas = cursor.fetchall()
        conn.close()

        lista_tareas = [
            {
                "id": f["id"],
                "titulo": f["titulo"],
                "descripcion": f["descripcion"],
                "completada": bool(f["completada"]),
                "fecha_creacion": f["fecha_creacion"]
            }
            for f in filas
        ]
        return jsonify({
            "status": "success",
            "usuario": usuario_sesion,
            "total_tareas": len(lista_tareas),
            "tareas": lista_tareas
        }), 200

    # Por defecto para navegadores: Renderiza la página HTML de bienvenida
    tareas = []
    if usuario_id:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tareas WHERE usuario_id = ? ORDER BY id DESC", (usuario_id,))
        tareas = cursor.fetchall()
        conn.close()

    return render_template_string(
        TAREAS_HTML_TEMPLATE,
        usuario=usuario_sesion,
        tareas=tareas
    )


# ------------------------------------------------------------------------------
# ENDPOINT 5: Crear Tarea (POST /tareas)
# ------------------------------------------------------------------------------
@app.route("/tareas", methods=["POST"])
def crear_tarea():
    usuario_id = session.get("usuario_id")
    if not usuario_id:
        return jsonify({
            "status": "error",
            "mensaje": "No autorizado. Debe iniciar sesión con POST /login."
        }), 401

    data = request.get_json(silent=True) or {}
    titulo = (data.get("titulo") or "").strip()
    descripcion = (data.get("descripcion") or "").strip()

    if not titulo:
        return jsonify({
            "status": "error",
            "mensaje": "El campo 'titulo' de la tarea es obligatorio."
        }), 400

    fecha_creacion = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO tareas (usuario_id, titulo, descripcion, completada, fecha_creacion)
        VALUES (?, ?, ?, 0, ?)
    """, (usuario_id, titulo, descripcion, fecha_creacion))
    conn.commit()
    tarea_id = cursor.lastrowid
    conn.close()

    return jsonify({
        "status": "success",
        "mensaje": "Tarea creada exitosamente.",
        "tarea": {
            "id": tarea_id,
            "titulo": titulo,
            "descripcion": descripcion,
            "completada": False,
            "fecha_creacion": fecha_creacion
        }
    }), 201


# ------------------------------------------------------------------------------
# ENDPOINT 6: Modificar/Completar Tarea (PUT /tareas/<int:tarea_id>)
# ------------------------------------------------------------------------------
@app.route("/tareas/<int:tarea_id>", methods=["PUT"])
def actualizar_tarea(tarea_id):
    usuario_id = session.get("usuario_id")
    if not usuario_id:
        return jsonify({
            "status": "error",
            "mensaje": "No autorizado. Inicie sesión primero."
        }), 401

    data = request.get_json(silent=True) or {}
    conn = get_db_connection()
    cursor = conn.cursor()

    # Verificar que la tarea exista y pertenezca al usuario
    cursor.execute("SELECT * FROM tareas WHERE id = ? AND usuario_id = ?", (tarea_id, usuario_id))
    tarea = cursor.fetchone()
    if not tarea:
        conn.close()
        return jsonify({
            "status": "error",
            "mensaje": "Tarea no encontrada o no pertenece al usuario actual."
        }), 404

    # Determinar si cambia de estado completada
    if "completada" in data:
        nuevo_estado = 1 if data["completada"] else 0
        cursor.execute("UPDATE tareas SET completada = ? WHERE id = ?", (nuevo_estado, tarea_id))
    if "titulo" in data and data["titulo"]:
        cursor.execute("UPDATE tareas SET titulo = ? WHERE id = ?", (data["titulo"], tarea_id))

    conn.commit()
    conn.close()

    return jsonify({
        "status": "success",
        "mensaje": f"Tarea #{tarea_id} actualizada correctamente."
    }), 200


# ------------------------------------------------------------------------------
# ENDPOINT 7: Eliminar Tarea (DELETE /tareas/<int:tarea_id>)
# ------------------------------------------------------------------------------
@app.route("/tareas/<int:tarea_id>", methods=["DELETE"])
def eliminar_tarea(tarea_id):
    usuario_id = session.get("usuario_id")
    if not usuario_id:
        return jsonify({
            "status": "error",
            "mensaje": "No autorizado. Inicie sesión primero."
        }), 401

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM tareas WHERE id = ? AND usuario_id = ?", (tarea_id, usuario_id))
    tarea = cursor.fetchone()
    if not tarea:
        conn.close()
        return jsonify({
            "status": "error",
            "mensaje": "Tarea no encontrada o no pertenece al usuario actual."
        }), 404

    cursor.execute("DELETE FROM tareas WHERE id = ?", (tarea_id,))
    conn.commit()
    conn.close()

    return jsonify({
        "status": "success",
        "mensaje": f"Tarea #{tarea_id} eliminada correctamente."
    }), 200


# ------------------------------------------------------------------------------
# Rutas de Asistencia para la Interfaz Web (Navegador)
# ------------------------------------------------------------------------------
@app.route("/tareas-web/crear", methods=["POST"])
def web_crear_tarea():
    usuario_id = session.get("usuario_id")
    if usuario_id:
        titulo = request.form.get("titulo", "").strip()
        if titulo:
            fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO tareas (usuario_id, titulo, descripcion, completada, fecha_creacion)
                VALUES (?, ?, '', 0, ?)
            """, (usuario_id, titulo, fecha))
            conn.commit()
            conn.close()
    return render_template_string("""<script>window.location.href='/tareas';</script>""")


@app.route("/tareas-web/toggle/<int:tarea_id>", methods=["POST"])
def web_toggle_tarea(tarea_id):
    usuario_id = session.get("usuario_id")
    if usuario_id:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT completada FROM tareas WHERE id = ? AND usuario_id = ?", (tarea_id, usuario_id))
        row = cursor.fetchone()
        if row:
            nuevo_estado = 0 if row["completada"] else 1
            cursor.execute("UPDATE tareas SET completada = ? WHERE id = ?", (nuevo_estado, tarea_id))
            conn.commit()
        conn.close()
    return render_template_string("""<script>window.location.href='/tareas';</script>""")


@app.route("/tareas-web/eliminar/<int:tarea_id>", methods=["POST"])
def web_eliminar_tarea(tarea_id):
    usuario_id = session.get("usuario_id")
    if usuario_id:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tareas WHERE id = ? AND usuario_id = ?", (tarea_id, usuario_id))
        conn.commit()
        conn.close()
    return render_template_string("""<script>window.location.href='/tareas';</script>""")


@app.route("/logout-web", methods=["GET"])
def web_logout():
    session.clear()
    return render_template_string("""<script>window.location.href='/tareas';</script>""")


# ------------------------------------------------------------------------------
# Punto de Entrada Principal
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    inicializar_db()
    print("=================================================================")
    print("  SERVIDOR API FLASK - GESTOR DE TAREAS (PFO 2)                 ")
    print("  Escuchando en: http://127.0.0.1:5000                           ")
    print("  Endpoints disponibles:                                         ")
    print("    - POST /registro    (Crear usuario con hash seguro)          ")
    print("    - POST /login       (Validar credenciales y autorizar)       ")
    print("    - GET  /tareas      (HTML de bienvenida y lista JSON)        ")
    print("    - POST /tareas      (Crear nueva tarea)                      ")
    print("    - PUT  /tareas/<id> (Marcar completada)                      ")
    print("    - DELETE /tareas/<id> (Eliminar tarea)                       ")
    print("    - POST /logout      (Cerrar sesión)                          ")
    print("=================================================================")
    app.run(host="127.0.0.1", port=5000, debug=True)

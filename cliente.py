"""
================================================================================
PFO 2: Sistema de Gestión de Tareas con API y Base de Datos
Materia: Programación sobre Redes - Tecnicatura Superior en Desarrollo de Software (TSDS)
Alumno: Guillermo Aybar
Archivo: cliente.py (Cliente de Consola Interactivo)
================================================================================
"""

import sys
import webbrowser
import requests

# Asegurar codificación utf-8 en consola de Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# URL base del servidor Flask
BASE_URL = "http://127.0.0.1:5000"

# Usamos Session de requests para persistir las cookies de sesión automáticamente
session = requests.Session()
usuario_actual = None


def imprimir_encabezado():
    print("\n" + "=" * 60)
    print("      SISTEMA DE GESTIÓN DE TAREAS - CLIENTE DE CONSOLA      ")
    print("      Materia: Programación sobre Redes (PFO 2)             ")
    print("=" * 60)
    if usuario_actual:
        print(f" [*] Sesión iniciada como: \033[92m{usuario_actual}\033[0m")
    else:
        print(" [*] Estado: \033[93mNo autenticado\033[0m (Inicia sesión o regístrate)")
    print("-" * 60)


def registrar_usuario():
    """Consume el endpoint POST /registro enviando usuario y contraseña."""
    print("\n--- REGISTRO DE NUEVO USUARIO ---")
    usuario = input("Ingrese nombre de usuario deseado: ").strip()
    contrasena = input("Ingrese su contraseña: ").strip()

    if not usuario or not contrasena:
        print("[-] Error: El usuario y la contraseña no pueden estar vacíos.")
        return

    # Payload según consigna del PFO 2: {"usuario": "nombre", "contraseña": "..."}
    payload = {
        "usuario": usuario,
        "contraseña": contrasena
    }

    try:
        response = session.post(f"{BASE_URL}/registro", json=payload, timeout=5)
        data = response.json()

        if response.status_code == 201:
            print(f"[+] ÉXITO: {data.get('mensaje')}")
            print(f"[+] ID de usuario asignado: {data.get('usuario_id')}")
            print("[*] Ahora puedes iniciar sesión con tu cuenta.")
        else:
            print(f"[-] ERROR ({response.status_code}): {data.get('mensaje')}")

    except requests.exceptions.ConnectionError:
        print("[-] Error de red: No se pudo conectar con el servidor. ¿Está encendido servidor.py?")
    except Exception as e:
        print(f"[-] Ocurrió un error inesperado: {e}")


def iniciar_sesion():
    """Consume el endpoint POST /login y almacena la sesión."""
    global usuario_actual
    print("\n--- INICIO DE SESIÓN ---")
    usuario = input("Usuario: ").strip()
    contrasena = input("Contraseña: ").strip()

    if not usuario or not contrasena:
        print("[-] Error: Ambos campos son requeridos.")
        return

    payload = {
        "usuario": usuario,
        "contraseña": contrasena
    }

    try:
        response = session.post(f"{BASE_URL}/login", json=payload, timeout=5)
        data = response.json()

        if response.status_code == 200:
            usuario_actual = data.get("usuario", usuario)
            print(f"[+] ÉXITO: {data.get('mensaje')}")
            print(f"[+] Sesión autorizada para '{usuario_actual}'.")
        else:
            print(f"[-] ERROR ({response.status_code}): {data.get('mensaje')}")

    except requests.exceptions.ConnectionError:
        print("[-] Error de red: No se pudo conectar con el servidor. ¿Está encendido servidor.py?")
    except Exception as e:
        print(f"[-] Ocurrió un error inesperado: {e}")


def ver_tareas():
    """Consume el endpoint GET /tareas solicitando JSON."""
    if not usuario_actual:
        print("[-] Debe iniciar sesión primero (Opción 2).")
        return

    try:
        # Solicitamos formato JSON a través del header Accept
        headers = {"Accept": "application/json"}
        response = session.get(f"{BASE_URL}/tareas", headers=headers, timeout=5)

        if response.status_code == 200:
            data = response.json()
            tareas = data.get("tareas", [])
            print(f"\n--- LISTA DE TAREAS ({len(tareas)} encontradas) ---")
            if not tareas:
                print(" (No tienes tareas registradas actualmente)")
            else:
                for t in tareas:
                    estado = "[✓] COMPLETADA" if t["completada"] else "[ ] PENDIENTE"
                    print(f"  ID #{t['id']} | {estado} | {t['titulo']}")
                    if t.get("descripcion"):
                        print(f"       Detalle: {t['descripcion']}")
                    print(f"       Fecha: {t['fecha_creacion']}")
            print("-" * 50)
        else:
            print(f"[-] Error ({response.status_code}): {response.text}")

    except requests.exceptions.ConnectionError:
        print("[-] Error de red: No se pudo conectar con el servidor.")
    except Exception as e:
        print(f"[-] Error: {e}")


def agregar_tarea():
    """Consume el endpoint POST /tareas para dar de alta una tarea."""
    if not usuario_actual:
        print("[-] Debe iniciar sesión primero (Opción 2).")
        return

    print("\n--- AGREGAR NUEVA TAREA ---")
    titulo = input("Título de la tarea: ").strip()
    descripcion = input("Descripción (opcional): ").strip()

    if not titulo:
        print("[-] El título es obligatorio.")
        return

    payload = {
        "titulo": titulo,
        "descripcion": descripcion
    }

    try:
        response = session.post(f"{BASE_URL}/tareas", json=payload, timeout=5)
        data = response.json()

        if response.status_code == 201:
            print(f"[+] ÉXITO: {data.get('mensaje')}")
            t = data.get("tarea", {})
            print(f"[+] Tarea creada con ID #{t.get('id')} - '{t.get('titulo')}'")
        else:
            print(f"[-] Error ({response.status_code}): {data.get('mensaje')}")

    except requests.exceptions.ConnectionError:
        print("[-] Error de red: Servidor inaccesible.")
    except Exception as e:
        print(f"[-] Error: {e}")


def cambiar_estado_tarea():
    """Consume PUT /tareas/<id> para marcar como completada."""
    if not usuario_actual:
        print("[-] Debe iniciar sesión primero (Opción 2).")
        return

    try:
        tarea_id = input("Ingrese el ID de la tarea a marcar como completada: ").strip()
        if not tarea_id.isdigit():
            print("[-] Debe ingresar un número entero válido.")
            return

        payload = {"completada": True}
        response = session.put(f"{BASE_URL}/tareas/{tarea_id}", json=payload, timeout=5)
        data = response.json()

        if response.status_code == 200:
            print(f"[+] ÉXITO: {data.get('mensaje')}")
        else:
            print(f"[-] Error ({response.status_code}): {data.get('mensaje')}")

    except requests.exceptions.ConnectionError:
        print("[-] Error de red: Servidor inaccesible.")
    except Exception as e:
        print(f"[-] Error: {e}")


def eliminar_tarea():
    """Consume DELETE /tareas/<id>."""
    if not usuario_actual:
        print("[-] Debe iniciar sesión primero (Opción 2).")
        return

    try:
        tarea_id = input("Ingrese el ID de la tarea a eliminar: ").strip()
        if not tarea_id.isdigit():
            print("[-] Debe ingresar un número entero válido.")
            return

        confirm = input(f"¿Seguro que desea eliminar la tarea #{tarea_id}? (s/n): ").strip().lower()
        if confirm != 's':
            print("[*] Operación cancelada.")
            return

        response = session.delete(f"{BASE_URL}/tareas/{tarea_id}", timeout=5)
        data = response.json()

        if response.status_code == 200:
            print(f"[+] ÉXITO: {data.get('mensaje')}")
        else:
            print(f"[-] Error ({response.status_code}): {data.get('mensaje')}")

    except requests.exceptions.ConnectionError:
        print("[-] Error de red: Servidor inaccesible.")
    except Exception as e:
        print(f"[-] Error: {e}")


def ver_html_bienvenida():
    """Abre el endpoint GET /tareas en el navegador predeterminado para ver el HTML de bienvenida."""
    url = f"{BASE_URL}/tareas"
    print(f"\n[*] Abriendo en tu navegador web: {url}")
    print("[*] Consigna PFO 2: 'GET /tareas: Muestre un html de bienvenida'")
    webbrowser.open(url)


def cerrar_sesion():
    global usuario_actual
    if not usuario_actual:
        print("[-] No hay ninguna sesión activa para cerrar.")
        return

    try:
        response = session.post(f"{BASE_URL}/logout", timeout=5)
        data = response.json()
        print(f"[+] {data.get('mensaje', 'Sesión cerrada.')}")
    except Exception:
        print("[*] Sesión local limpiada.")
    finally:
        usuario_actual = None


def main():
    while True:
        imprimir_encabezado()
        print(" 1. Registrar nuevo usuario    (POST /registro)")
        print(" 2. Iniciar sesión             (POST /login)")
        print(" 3. Ver mis tareas             (GET /tareas - JSON)")
        print(" 4. Agregar nueva tarea        (POST /tareas)")
        print(" 5. Marcar tarea completada    (PUT /tareas/<id>)")
        print(" 6. Eliminar tarea             (DELETE /tareas/<id>)")
        print(" 7. Ver HTML de Bienvenida     (GET /tareas en Navegador)")
        print(" 8. Cerrar sesión              (POST /logout)")
        print(" 9. Salir")
        print("-" * 60)

        opcion = input("Seleccione una opción (1-9): ").strip()

        if opcion == "1":
            registrar_usuario()
        elif opcion == "2":
            iniciar_sesion()
        elif opcion == "3":
            ver_tareas()
        elif opcion == "4":
            agregar_tarea()
        elif opcion == "5":
            cambiar_estado_tarea()
        elif opcion == "6":
            eliminar_tarea()
        elif opcion == "7":
            ver_html_bienvenida()
        elif opcion == "8":
            cerrar_sesion()
        elif opcion == "9":
            print("\n[*] ¡Gracias por utilizar el Gestor de Tareas! Hasta luego.")
            cerrar_sesion()
            sys.exit(0)
        else:
            print("[-] Opción no válida. Intente nuevamente.")

        input("\nPresione [Enter] para continuar...")


if __name__ == "__main__":
    main()

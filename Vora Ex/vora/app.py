from flask import (
    Flask, render_template, request, redirect, url_for,
    session, jsonify, flash, send_file
)
from werkzeug.security import generate_password_hash, check_password_hash
from db import get_connection, create_tables
from gemini import ask_gemini
from datetime import datetime
import cv2, os, numpy as np
import mysql.connector
import io
import csv
import subprocess
from functools import wraps


# ==================================================
#                DECORADOR LOGIN REQUIRED
# ==================================================
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user" not in session:
            flash("Debes iniciar sesión para acceder.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


app = Flask(__name__, template_folder="plantillas")
app.secret_key = os.environ.get("PAPAYA", "123456")

create_tables()  # Crea todas las tablas necesarias


# ==================================================
#                         INDEX
# ==================================================
@app.route("/")
def index():
    user = session.get("user")
    return render_template("index.html", user=user)


# ==================================================
#                REGISTRO DE USUARIO
# ==================================================
@app.route("/registro", methods=["GET", "POST"])
def registro():
    if request.method == "POST":
        nombre = request.form.get("nombre")
        email = request.form.get("email")
        password = request.form.get("password")

        if not nombre or not email or not password:
            flash("Completa todos los campos.", "danger")
            return redirect(url_for("registro"))

        password_hash = generate_password_hash(password)

        try:
            conn = get_connection()
            cur = conn.cursor()

            cur.execute("""
                INSERT INTO usuarios (nombre, email, password_hash)
                VALUES (%s, %s, %s)
            """, (nombre, email, password_hash))
            conn.commit()

            cur.execute("SELECT LAST_INSERT_ID()")
            user_id = cur.fetchone()[0]

            cur.close()
            conn.close()

            session["temp_user_id"] = user_id

            flash("Usuario creado. Ahora registra tu rostro.", "success")
            return redirect(url_for("registrar_rostro"))

        except Exception as e:
            flash(f"Error: {e}", "danger")
            return redirect(url_for("registro"))

    return render_template("registro.html")


# ==================================================
#              VISTA PÁGINA REGISTRAR ROSTRO
# ==================================================
@app.route("/registrar_rostro")
def registrar_rostro():
    if "temp_user_id" not in session:
        flash("Primero crea una cuenta.", "warning")
        return redirect(url_for("registro"))

    return render_template("registrar_rostro.html")


# ==================================================
#                  CAPTURAR ROSTRO
# ==================================================
@app.route("/capturar_rostro")
def capturar_rostro():
    try:
        user_id = session.get("temp_user_id")
        if not user_id:
            flash("Primero crea una cuenta para registrar rostro.", "warning")
            return redirect(url_for("registro"))

        if not os.path.exists("modelos"):
            os.makedirs("modelos")

        cascade_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "haarcascade",
            "haarcascade_frontalface_default.xml"
        )

        if not os.path.exists(cascade_path):
            return "ERROR: No se encontró el archivo del modelo Haarcascade."

        face_cascade = cv2.CascadeClassifier(cascade_path)

        if face_cascade.empty():
            return "ERROR: El archivo Haarcascade está dañado."

        cap = cv2.VideoCapture(0)

        if not cap.isOpened():
            return "ERROR: No se pudo acceder a la cámara."

        fotos = []
        total_fotos = 50

        flash("Mira a la cámara. Se tomarán 50 fotos automáticamente.", "info")

        while len(fotos) < total_fotos:
            ret, frame = cap.read()
            if not ret:
                continue

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.3, 5)

            for (x, y, w, h) in faces:
                rostro = gray[y:y+h, x:x+w]
                fotos.append(rostro)

            cv2.imshow("Registrando rostro (Q para cancelar)", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                cap.release()
                cv2.destroyAllWindows()
                flash("Registro facial cancelado.", "warning")
                return redirect(url_for("registro"))

        cap.release()
        cv2.destroyAllWindows()

        recognizer = cv2.face.LBPHFaceRecognizer_create()
        labels = np.array([user_id] * len(fotos))
        recognizer.train(fotos, labels)

        modelo_path = f"models_facial/modelo_user_{user_id}.xml"
        recognizer.write(modelo_path)

        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO usuarios_facial (usuario_id, ruta_modelo, fecha_registro)
            VALUES (%s, %s, NOW())
        """, (user_id, modelo_path))

        conn.commit()
        cur.close()
        conn.close()

        session.pop("temp_user_id", None)

        flash("Rostro registrado exitosamente.", "success")
        return redirect(url_for("login"))

    except Exception as e:
        return f"Error al registrar rostro: {e}"


# ==================================================
#                       LOGIN NORMAL
# ==================================================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":

        email = request.form.get("email")
        password = request.form.get("password")

        conn = get_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM usuarios WHERE email = %s", (email,))
        user = cur.fetchone()
        cur.close()
        conn.close()

        if user and check_password_hash(user["password_hash"], password):
            session["user"] = {
                "id": user["id"],
                "nombre": user["nombre"],
                "email": user["email"],
            }

           # flash(f"Bienvenido {user['nombre']}!", "success")#
            return redirect(url_for("chat"))

        flash("Credenciales incorrectas.", "danger")
        return redirect(url_for("login"))

    return render_template("login.html")


# ==================================================
#                     LOGIN FACIAL
# ==================================================
@app.route("/login_facial")
def login_facial():

    cascade_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "haarcascade",
        "haarcascade_frontalface_default.xml"
    )
    FACE_CASCADE = cv2.CascadeClassifier(cascade_path)

    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM usuarios_facial")
    modelos = cur.fetchall()
    cur.close()
    conn.close()

    if not modelos:
        flash("No hay modelos faciales registrados.", "warning")
        return redirect(url_for("login"))

    reconocedores = {}
    for m in modelos:
        model = cv2.face.LBPHFaceRecognizer_create()
        model.read(m["ruta_modelo"])
        reconocedores[m["usuario_id"]] = model

    cam = cv2.VideoCapture(0)

    while True:
        ret, frame = cam.read()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = FACE_CASCADE.detectMultiScale(gray, 1.3, 5)

        for (x, y, w, h) in faces:
            rostro = gray[y:y+h, x:x+w]

            for usuario_id, model in reconocedores.items():
                pred, conf = model.predict(rostro)

                if conf < 60:
                    cam.release()
                    cv2.destroyAllWindows()

                    conn = get_connection()
                    cur = conn.cursor(dictionary=True)
                    cur.execute("SELECT * FROM usuarios WHERE id = %s", (usuario_id,))
                    user = cur.fetchone()
                    cur.close()
                    conn.close()

                    session["user"] = {
                        "id": user["id"],
                        "nombre": user["nombre"],
                        "email": user["email"],
                    }

                    flash("Inicio facial exitoso", "success")
                    return redirect(url_for("chat"))

        cv2.imshow("Iniciar sesión con rostro (Q para salir)", frame)
        if cv2.waitKey(1) == ord("q"):
            break

    cam.release()
    cv2.destroyAllWindows()
    flash("No se reconoció ningún rostro.", "danger")
    return redirect(url_for("login"))


# ==================================================
#                   CHAT UNIFICADO
# ==================================================
@app.route("/chat", methods=["GET", "POST"])
@login_required
def chat():
    user = session["user"]
    respuesta = None
    pregunta = None

    if request.method == "POST":
        pregunta = request.form.get("mensaje")
        respuesta = ask_gemini(pregunta)

        # Guardar historial
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO Historial (user_id, mensaje, respuesta, fecha)
            VALUES (%s, %s, %s, NOW())
        """, (user["id"], pregunta, respuesta))
        conn.commit()
        cur.close()
        conn.close()

    # Obtener historial
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    
    cur.execute("""
        SELECT mensaje, respuesta 
        FROM Historial 
        WHERE user_id = %s 
        ORDER BY id DESC 
        LIMIT 50
    """, (user["id"],))
    historial = list(reversed(cur.fetchall()))
    
    # Obtener lista de chats anteriores
    cur.execute("""
        SELECT id, mensaje as titulo, fecha
        FROM Historial
        WHERE user_id = %s
        GROUP BY DATE(fecha)
        ORDER BY fecha DESC
        LIMIT 10
    """, (user["id"],))
    chats_anteriores = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return render_template(
        "chat.html",
        historial=historial,
        chats_anteriores=chats_anteriores,
        pregunta=pregunta,
        respuesta=respuesta,
        user=user
    )


# ==================================================
#                   NUEVO CHAT
# ==================================================
@app.route("/nuevo_chat")
@login_required
def nuevo_chat():
    return redirect(url_for("chat_vacio"))


# ==================================================
#                   CHAT VACÍO
# ==================================================
@app.route("/chat_vacio")
@login_required
def chat_vacio():
    user = session["user"]
    
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    
    cur.execute("""
        SELECT id, mensaje as titulo, fecha
        FROM Historial
        WHERE user_id = %s
        GROUP BY DATE(fecha)
        ORDER BY fecha DESC
        LIMIT 10
    """, (user["id"],))
    chats_anteriores = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return render_template(
        "chat.html",
        historial=[],
        chats_anteriores=chats_anteriores,
        user=user
    )


# ==================================================
#                   CARGAR CHAT
# ==================================================
@app.route("/cargar_chat/<int:chat_id>")
@login_required  
def cargar_chat(chat_id):
    user = session["user"]
    
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    
    cur.execute("""
        SELECT * FROM Historial 
        WHERE id = %s AND user_id = %s
    """, (chat_id, user["id"]))
    
    chat = cur.fetchone()
    cur.close()
    conn.close()
    
    if not chat:
        return redirect(url_for("chat"))
    
    return redirect(url_for("chat"))
# ==================================================
#                   DESCARGAR HISTORIAL
# ==================================================
@app.route("/descargar_historial")
def descargar_historial():
    user = session.get("user")
    if not user:
        flash("Debes iniciar sesión para descargar el historial.", "warning")
        return redirect(url_for("login"))  # o la ruta que uses

    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM Historial WHERE user_id = %s", (user["id"],))
        registros = cur.fetchall()
        
        columnas = [desc[0] for desc in cur.description]

        cur.close()
        conn.close()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(columnas)  
        for fila in registros:
            writer.writerow(fila)

        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode("utf-8")),
            mimetype="text/plain",
            as_attachment=True,
            download_name="historial_chat.txt"
        )

    except Exception as e:
        flash(f"Error al descargar historial: {e}", "danger")
        return redirect(url_for("chat"))


# ==================================================
#                   BORRAR HISTORIAL (AGREGADO)
# ==================================================
@app.context_processor
def inject_now():
    return {'current_year': datetime.now().year}

@app.route("/borrar_historial", methods=["POST"])
@login_required
def borrar_historial():
    user = session["user"]
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM Historial WHERE user_id = %s", (user["id"],))
        conn.commit()
        cur.close()
        conn.close()
        flash("Historial borrado con éxito.", "success")
    except Exception as e:
        flash(f"Error al borrar historial: {e}", "danger")

    return redirect(url_for("chat"))
# ==================================================
#                        APICHAT
# ==================================================
@app.route("/api/chat", methods=["POST"])
@login_required
def api_chat():
    user = session["user"]
    data = request.get_json()
    prompt = data.get("mensaje")
    respuesta = ask_gemini(prompt)
   
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO Historial (user_id,mensaje,respuesta) VALUES (%s,%s,%s)",
                (user["id"],prompt,respuesta))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"respuesta": respuesta})

# ==================================================
#                        LOGOUT
# ==================================================
@app.route("/logout")
def logout():
    session.pop("user", None)
    flash("Sesión cerrada.", "info")
    return redirect(url_for("index"))

# _________________________________________________
@app.route("/formulario", methods=["GET", "POST"])
def formulario():
    if request.method == "POST":
        nombre = request.form.get("nombre")
        apellido = request.form.get("apellido")
        telefono = request.form.get("telefono")
        mensaje = request.form.get("mensaje")

        if not nombre or not apellido or not mensaje:
            flash("Completa los campos obligatorios.", "danger")
            return redirect(url_for("formulario"))

        # Aquí puedes guardar en BD si lo deseas.
        flash("Gracias — tu mensaje fue recibido.", "success")
        return redirect(url_for("index"))

    return render_template("formulario.html", user=session.get("user"))

# ==================================================
#                  VARIABLES GLOBALES
# ==================================================
@app.context_processor
def inject_now():
    return {'current_year': datetime.now().year}


# ==================================================
#                  RUN SERVER
# ==================================================
if __name__ == "__main__":
    app.run(debug=True)

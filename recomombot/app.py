from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from werkzeug.security import generate_password_hash, check_password_hash
from db import get_connection, create_tables
from gemini import ask_gemini
from datetime import datetime

import os
import subprocess

app = Flask(__name__, template_folder="plantillas")
app.secret_key = os.environ.get("PAPAYA", "123456") 

create_tables()

@app.route("/")
def index():
    user = session.get("user")
    return render_template("index.html", user=user)

@app.route("/registro", methods=["GET", "POST"])
def registro():
    if request.method == "POST":
        nombre = request.form.get("nombre")
        email = request.form.get("email")
        password = request.form.get("password")
        if not nombre or not email or not password:
            flash("Completa todos los campos.", "danger")
            return redirect(url_for("registro", "danger"))

        password_hash = generate_password_hash(password)
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("INSERT INTO usuarios (nombre, email, password_hash) VALUES (%s, %s, %s)",
                        (nombre, email, password_hash))
            conn.commit()
            cur.close()
            conn.close()
            flash("Registro exitoso. Inicia sesión.", "success")
            return redirect(url_for("login"))
        except Exception as e:
            flash(f"Error registrando: {e}")
            return redirect(url_for("registro"))

    return render_template("registro.html")

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
          
            session["user"] = {"id": user["id"], "nombre": user["nombre"], "email": user["email"]}
            flash(f"Bienvenido {user['nombre']}!", "success")
            return redirect(url_for("chat"))
        else:
            flash("Email o contraseña incorrectos.", "danger")
            return redirect(url_for("login"))
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("user", None)
    flash("Sesión cerrada.", "info")
    return redirect(url_for("index"))

def login_required(fn):
    from functools import wraps
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user"):
            flash("Debes iniciar sesión para acceder.", "warning")
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

@app.route("/chat", methods=["GET", "POST"])
@login_required
def chat():
    respuesta = None
    pregunta = None
    if request.method == "POST":
        pregunta = request.form.get("mensaje")
        respuesta = ask_gemini(pregunta)
    return render_template("chat.html", pregunta=pregunta, respuesta=respuesta, user=session.get("user"))


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

@app.context_processor
def inject_now():
    return {'current_year': datetime.now().year}

@app.route("/facial1")
def facial1():
    try:
        ruta = os.path.join(os.path.dirname(__file__), "facial.py")
        subprocess.Popen(["python", ruta])
        flash("Se abrió el detector facial en una nueva ventana.", "success")
    except Exception as e:
        flash(f"Error al ejecutar el detector facial: {e}", "danger")
    return redirect(url_for("index"))



if __name__ == "__main__":
    app.run(debug=True)


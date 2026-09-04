from flask import Flask, redirect, url_for, render_template, request, flash, session, jsonify
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from psycopg2.extras import RealDictCursor
import psycopg2
import os

app = Flask(__name__, template_folder='templates')

# --- Config ---------------------------------------------------------------
# SECRET_KEY must be a fixed value in production (env var), not os.urandom(),
# otherwise every restart/redeploy on Railway invalidates all logged-in sessions.
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-change-me")

UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", "/tmp/uploads")
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Admin credentials come from environment variables instead of being
# hardcoded in source. Set ADMIN_USERNAME / ADMIN_PASSWORD in Railway's
# "Variables" tab.
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "change-me")


def get_db_connection():
    """Single Postgres connection helper (Railway injects DATABASE_URL)."""
    return psycopg2.connect(
        os.environ["DATABASE_URL"],
        cursor_factory=RealDictCursor
    )


def is_admin():
    return session.get("is_admin") is True


# --- Public / core routes --------------------------------------------------

@app.route('/')
def index():
    return redirect(url_for('web'))


@app.route('/Home')
def web():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pets")
    pets = cursor.fetchall()
    conn.close()
    return render_template("web.html", pets=pets)


@app.route("/pets")
def show_pets():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pets")
    pets = cursor.fetchall()
    conn.close()
    return render_template("pets_list.html", pets=pets)


# --- Auth --------------------------------------------------------------

@app.route("/register", methods=["GET", "POST"])
def register():
    msg = ''
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        email = request.form.get("email")
        password_hash = generate_password_hash(password)

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO users (username, password, email) VALUES (%s, %s, %s)",
                (username, password_hash, email)
            )
            conn.commit()
            msg = "✅ Successfully registered!"
        except psycopg2.IntegrityError:
            conn.rollback()
            msg = "❌ Username or Email already exists!"
        finally:
            conn.close()

    return render_template('register.html', msg=msg)


@app.route("/loging", methods=["GET", "POST"])
def loging():
    msg = ''

    if "user_id" in session:
        msg = "⚠️ You are already logged in."
        return render_template("loging.html", msg=msg)

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            # Admin status is derived from an env-configured username, never
            # stored in a guessable/forgeable way in the session.
            session["is_admin"] = (username == ADMIN_USERNAME and password == ADMIN_PASSWORD)
            msg = "✅ Login successful!"
            return redirect(url_for("web"))
        else:
            msg = "❌ Incorrect username or password."

    return render_template("loging.html", msg=msg)


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.")
    return redirect(url_for("loging"))


# --- Adoption flow -------------------------------------------------------

@app.route("/adoption_status")
def adoption_status():
    if "user_id" not in session:
        return redirect(url_for("loging"))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM adoptions WHERE user_id = %s", (session["user_id"],))
    adoptions = cursor.fetchall()
    conn.close()

    return render_template("adoption_status.html", adoptions=adoptions)


@app.route('/AdoptShelf')
def adopt_shelf():
    if "user_id" not in session:
        flash("⚠️ Please log in first to adopt a pet.")
        return redirect(url_for("loging"))

    shelf = session.get("adopt_shelf", [])
    return render_template("adoptshelf.html", shelf=shelf)


@app.route("/add_to_shelf", methods=["POST"])
def add_to_shelf():
    if "user_id" not in session:
        return jsonify({"message": "⚠️ Please log in first."})

    data = request.get_json()
    title = data.get("title")
    img = data.get("img")

    if not title or not img:
        return jsonify({"message": "❌ Missing pet data."})

    shelf = session.get("adopt_shelf", [])
    shelf.append({"title": title, "img": img})
    session["adopt_shelf"] = shelf

    return jsonify({"message": f"✅ {title} added to your Adopt Shelf!"})


@app.route("/cancel_adoption", methods=["POST"])
def cancel_adoption():
    session.pop("adopt_shelf", None)
    session.pop("pending_adoption", None)
    flash("❌ Adoption process cancelled.")
    return redirect(url_for("adopt_shelf"))


@app.route("/confirm_adoption", methods=["POST"])
def confirm_adoption():
    if "user_id" not in session:
        flash("⚠️ Please log in first to confirm adoption.")
        return redirect(url_for("loging"))

    shelf = session.get("adopt_shelf", [])
    if not shelf:
        flash("No pets in your shelf.")
        return redirect(url_for("adopt_shelf"))

    session["pending_adoption"] = shelf
    return redirect(url_for("confirm_info"))


@app.route("/confirm_info", methods=["GET", "POST"])
def confirm_info():
    if "pending_adoption" not in session:
        flash("No pending adoption to confirm.")
        return redirect(url_for("adopt_shelf"))

    if request.method == "POST":
        contact = request.form["contact"]
        birthdate = request.form["birthdate"]
        email_address = request.form["email"]
        valid_id_type = request.form["valid_id_type"]

        pets = session["pending_adoption"]

        conn = get_db_connection()
        cursor = conn.cursor()

        for pet in pets:
            cursor.execute(
                """
                INSERT INTO adoptions (user_id, pet_name, pet_img, status)
                VALUES (%s, %s, %s, %s)
                """,
                (session["user_id"], pet["title"], pet["img"], "Pending Evaluation")
            )

        cursor.execute(
            """
            UPDATE users SET contact = %s, birthdate = %s, address = %s, valid_id_type = %s
            WHERE id = %s
            """,
            (contact, birthdate, email_address, valid_id_type, session["user_id"])
        )

        conn.commit()
        conn.close()

        session["adopt_shelf"] = []
        session.pop("pending_adoption", None)

        flash("✅ Adoption has been set for evaluation. Please wait for updates.")
        return redirect(url_for("adopt_shelf"))

    return render_template("confirm_info.html")


# --- Admin routes ----------------------------------------------------------

@app.route("/view_orders")
def view_orders():
    if not is_admin():
        return "Unauthorized Access", 403

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM adoptions")
    adoptions = cursor.fetchall()
    conn.close()

    return render_template("view_orders.html", adoptions=adoptions)


@app.route("/update_status/<int:adoption_id>", methods=["POST"])
def update_status(adoption_id):
    if not is_admin():
        return "Unauthorized Access", 403

    new_status = request.form.get("status")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE adoptions SET status = %s WHERE id = %s",
        (new_status, adoption_id)
    )
    conn.commit()
    conn.close()

    flash(f"✅ Updated adoption #{adoption_id} to '{new_status}'.")
    return redirect(url_for("view_orders"))


@app.route("/delete_adoption/<int:adoption_id>", methods=["POST"])
def delete_adoption(adoption_id):
    if not is_admin():
        return "Unauthorized Access", 403

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM adoptions WHERE id = %s", (adoption_id,))
    conn.commit()
    conn.close()

    flash("🗑️ Adoption record removed.")
    return redirect(url_for("view_orders"))


@app.route('/add_pet', methods=['GET', 'POST'])
def add_pet():
    if not is_admin():
        flash("⚠️ Unauthorized Access. Only admins can add pets.")
        return redirect(url_for('web'))

    if request.method == 'POST':
        name = request.form['Name']
        age = request.form['Age']
        date_found = request.form['Date_Found']
        characteristics = request.form['Characteristics']
        information = request.form.get('Information', '')

        img_file = request.files.get('img')
        if img_file and img_file.filename:
            filename = secure_filename(img_file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            img_file.save(file_path)
            img_path = f'uploads/{filename}'
        else:
            img_path = ''

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO pets (Name, Age, Date_Found, Characteristics, Information, img)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (name, age, date_found, characteristics, information, img_path)
        )
        conn.commit()
        conn.close()

        flash("✅ Pet added successfully!")
        return redirect(url_for('web'))

    return render_template("add_pet.html")


@app.route("/delete_pet/<int:pet_id>", methods=["POST"])
def delete_pet(pet_id):
    if not is_admin():
        return "Unauthorized Access", 403

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM pets WHERE id = %s", (pet_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("show_pets"))


@app.route('/authorized')
def view_users():
    if not is_admin():
        return "Unauthorized Access", 403

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()
    conn.close()

    # Rendered through a real template (with autoescaping) instead of raw
    # string concatenation, which was vulnerable to XSS via user fields
    # and also couldn't render {{ url_for(...) }} at all.
    return render_template("authorized.html", users=users)


@app.route('/remove_user/<int:user_id>')
def remove_user(user_id):
    if not is_admin():
        return "Unauthorized Access", 403

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('view_users'))


@app.route('/clear_users', methods=['POST'])
def clear_users():
    if not is_admin():
        return "Unauthorized Access", 403

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users")
    conn.commit()
    conn.close()
    return redirect(url_for('view_users'))


if __name__ == '__main__':
    # Local dev only. On Railway, gunicorn runs the app (see Procfile).
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)

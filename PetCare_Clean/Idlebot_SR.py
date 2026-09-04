import os
from flask import Flask, redirect, url_for, render_template, request, flash, session, jsonify
from werkzeug.utils import secure_filename
import psycopg2
from psycopg2.extras import RealDictCursor

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = Flask(__name__, template_folder='templates')
app.secret_key = os.environ.get("SECRET_KEY", os.urandom(24))

# NOTE: Railway's filesystem is ephemeral - anything written to /tmp (or any
# local folder) is wiped on every redeploy/restart. This is fine for a demo
# but uploaded pet photos / ID images will NOT persist. For real persistence
# use a service like AWS S3, Cloudinary, or Railway's Volumes feature.
UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", "/tmp/uploads")
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Simple admin credentials - configurable via environment variables instead
# of being hardcoded in source. Still plaintext comparison; see note at the
# bottom of this file about hashing passwords properly.
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")


def is_admin():
    return session.get("username") == ADMIN_USERNAME and session.get("password") == ADMIN_PASSWORD


def get_db_connection():
    """Single source of truth for DB connections - Postgres via DATABASE_URL.
    Railway injects DATABASE_URL automatically when you attach a Postgres
    plugin to your project."""
    return psycopg2.connect(
        os.environ["DATABASE_URL"],
        cursor_factory=RealDictCursor
    )


def init_db():
    """Create tables if they don't already exist. Safe to call on every boot."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            contact TEXT,
            birthdate TEXT,
            address TEXT,
            age TEXT,
            valid_id_type TEXT,
            valid_id_path TEXT
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pets (
            id SERIAL PRIMARY KEY,
            "Name" TEXT,
            "Age" TEXT,
            "Date_Found" TEXT,
            "Characteristics" TEXT,
            "Information" TEXT,
            img TEXT
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS adoptions (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            pet_name TEXT,
            pet_img TEXT,
            status TEXT DEFAULT 'Pending Evaluation'
        );
    """)
    conn.commit()
    cur.close()
    conn.close()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route('/')
def index():
    return redirect(url_for('web'))


@app.route('/Home')
def web():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pets")
    pets = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("web.html", pets=pets)


# ---- Auth ------------------------------------------------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    msg = ''
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        email = request.form.get("email")

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO users (username, password, email) VALUES (%s, %s, %s)",
                (username, password, email)
            )
            conn.commit()
            msg = "✅ Successfully registered!"
        except psycopg2.errors.UniqueViolation:
            conn.rollback()
            msg = "❌ Username or Email already exists!"
        finally:
            cursor.close()
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
        cursor.close()
        conn.close()

        if user:
            if user["password"] == password:
                session["user_id"] = user["id"]
                session["username"] = user["username"]
                session["password"] = user["password"]

                msg = "✅ Login successful!"
                return redirect(url_for("web"))
            else:
                msg = "❌ Incorrect password."
        else:
            msg = "❌ Username not found."

    return render_template("loging.html", msg=msg)


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.")
    return redirect(url_for("loging"))


# ---- Pets --------------------------------------------------------------
@app.route("/pets")
def show_pets():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pets")
    pets = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("pets_list.html", pets=pets)


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
            '''INSERT INTO pets ("Name", "Age", "Date_Found", "Characteristics", "Information", img)
               VALUES (%s, %s, %s, %s, %s, %s)''',
            (name, age, date_found, characteristics, information, img_path)
        )
        conn.commit()
        cursor.close()
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
    cursor.close()
    conn.close()
    return redirect(url_for("show_pets"))


# ---- Adopt shelf (session-based cart) ---------------------------------
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


@app.route('/AdoptShelf')
def adopt_shelf():
    if "user_id" not in session:
        flash("⚠️ Please log in first to adopt a pet.")
        return redirect(url_for("loging"))

    shelf = session.get("adopt_shelf", [])
    return render_template("adoptshelf.html", shelf=shelf)


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
        email_address = request.form["email"]
        contact = request.form["contact"]
        birthdate = request.form["birthdate"]
        valid_id_type = request.form["valid_id_type"]

        pets = session["pending_adoption"]

        conn = get_db_connection()
        cursor = conn.cursor()

        for pet in pets:
            cursor.execute(
                """INSERT INTO adoptions (user_id, pet_name, pet_img, status)
                   VALUES (%s, %s, %s, %s)""",
                (session["user_id"], pet["title"], pet["img"], "Pending Evaluation")
            )

        # NOTE: kept original behavior of storing the submitted "email" value
        # into the "address" column - this looked like a bug in the source
        # (the form field is called email but there's no separate address
        # field being collected). Double check this matches what you intend.
        cursor.execute(
            """UPDATE users SET
                   contact = %s, birthdate = %s, address = %s, valid_id_type = %s
               WHERE id = %s""",
            (contact, birthdate, email_address, valid_id_type, session["user_id"])
        )

        conn.commit()
        cursor.close()
        conn.close()

        session["adopt_shelf"] = []
        session.pop("pending_adoption", None)

        flash("✅ Adoption has been set for evaluation. Please wait for updates.")
        return redirect(url_for("adopt_shelf"))

    return render_template("confirm_info.html")


@app.route("/adoption_status")
def adoption_status():
    if "user_id" not in session:
        return redirect(url_for("loging"))

    user_id = session["user_id"]

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM adoptions WHERE user_id = %s", (user_id,))
    adoptions = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template("adoption_status.html", adoptions=adoptions)


# ---- Admin ---------------------------------------------------------------
@app.route("/view_orders")
def view_orders():
    if not is_admin():
        return "Unauthorized Access", 403

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM adoptions")
    adoptions = cursor.fetchall()
    cursor.close()
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
    cursor.close()
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
    cursor.close()
    conn.close()

    flash("🗑️ Adoption record removed.")
    return redirect(url_for("view_orders"))


@app.route('/remove_user/<int:user_id>')
def remove_user(user_id):
    if not is_admin():
        return "Unauthorized Access", 403

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect('/authorized')


@app.route('/clear_users', methods=['POST'])
def clear_users():
    if not is_admin():
        return "Unauthorized Access", 403

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users")
    conn.commit()
    cursor.close()
    conn.close()
    return redirect('/authorized')


@app.route('/authorized')
def view_users():
    if not is_admin():
        return "Unauthorized Access", 403

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template("authorized.html", users=users)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    init_db()
    # Railway sets PORT for you; default to 5000 for local runs.
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=os.environ.get("FLASK_DEBUG", "0") == "1")
else:
    # Also run when imported by gunicorn (production on Railway)
    init_db()

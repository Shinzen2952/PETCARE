```python
from flask import Flask, redirect, url_for, render_template, request, flash, session, jsonify
from werkzeug.utils import secure_filename
from psycopg2.extras import RealDictCursor
import psycopg2
import os


# =========================================================
# DATABASE CONNECTION - RAILWAY POSTGRESQL
# =========================================================

def get_db_connection():
    return psycopg2.connect(
        os.environ["DATABASE_URL"],
        cursor_factory=RealDictCursor
    )


# =========================================================
# FLASK CONFIGURATION
# =========================================================

app = Flask(__name__, template_folder="templates")

app.config["UPLOAD_FOLDER"] = "/tmp/uploads"
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# Set SECRET_KEY in Railway Variables
app.secret_key = os.environ.get("SECRET_KEY", "development-secret-key")


# =========================================================
# HOME
# =========================================================

@app.route("/")
def index():
    return redirect(url_for("web"))


# =========================================================
# ADOPTION STATUS
# =========================================================

@app.route("/adoption_status")
def adoption_status():

    if "user_id" not in session:
        return redirect(url_for("loging"))

    user_id = session["user_id"]

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM adoptions WHERE user_id = %s",
        (user_id,)
    )

    adoptions = cursor.fetchall()

    conn.close()

    return render_template(
        "adoption_status.html",
        adoptions=adoptions
    )


# =========================================================
# UPDATE ADOPTION STATUS
# =========================================================

@app.route("/update_status/<int:adoption_id>", methods=["POST"])
def update_status(adoption_id):

    if (
        session.get("username") != "admin"
        or session.get("password") != "admin123"
    ):
        return "Unauthorized Access", 403

    new_status = request.form.get("status")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE adoptions
        SET status = %s
        WHERE id = %s
        """,
        (new_status, adoption_id)
    )

    conn.commit()
    conn.close()

    flash(
        f"✅ Updated adoption #{adoption_id} to '{new_status}'."
    )

    return redirect(url_for("view_orders"))


# =========================================================
# DELETE ADOPTION
# =========================================================

@app.route("/delete_adoption/<int:adoption_id>", methods=["POST"])
def delete_adoption(adoption_id):

    if (
        session.get("username") != "admin"
        or session.get("password") != "admin123"
    ):
        return "Unauthorized Access", 403

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM adoptions WHERE id = %s",
        (adoption_id,)
    )

    conn.commit()
    conn.close()

    flash("🗑️ Adoption record removed.")

    return redirect(url_for("view_orders"))


# =========================================================
# VIEW ALL ADOPTIONS - ADMIN
# =========================================================

@app.route("/view_orders")
def view_orders():

    if (
        session.get("username") != "admin"
        or session.get("password") != "admin123"
    ):
        return "Unauthorized Access", 403

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM adoptions")

    adoptions = cursor.fetchall()

    conn.close()

    return render_template(
        "view_orders.html",
        adoptions=adoptions
    )


# =========================================================
# CANCEL ADOPTION
# =========================================================

@app.route("/cancel_adoption", methods=["POST"])
def cancel_adoption():

    session.pop("adopt_shelf", None)
    session.pop("pending_adoption", None)

    flash("❌ Adoption process cancelled.")

    return redirect(url_for("adopt_shelf"))


# =========================================================
# CONFIRM ADOPTION
# =========================================================

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


# =========================================================
# CONFIRM ADOPTION INFORMATION
# =========================================================

@app.route("/confirm_info", methods=["GET", "POST"])
def confirm_info():

    if "pending_adoption" not in session:
        flash("No pending adoption to confirm.")
        return redirect(url_for("adopt_shelf"))

    if request.method == "POST":

        name = request.form["name"]
        email_address = request.form["email"]
        contact = request.form["contact"]
        birthdate = request.form["birthdate"]
        valid_id_type = request.form["valid_id_type"]

        pets = session["pending_adoption"]

        conn = get_db_connection()
        cursor = conn.cursor()

        try:

            # -------------------------------------------------
            # INSERT ADOPTION RECORDS
            # -------------------------------------------------

            for pet in pets:

                cursor.execute(
                    """
                    INSERT INTO adoptions
                    (
                        user_id,
                        pet_name,
                        pet_img,
                        status
                    )
                    VALUES (%s, %s, %s, %s)
                    """,
                    (
                        session["user_id"],
                        pet["title"],
                        pet["img"],
                        "Pending Evaluation"
                    )
                )

            # -------------------------------------------------
            # UPDATE USER INFORMATION
            # -------------------------------------------------

            cursor.execute(
                """
                UPDATE users
                SET
                    contact = %s,
                    birthdate = %s,
                    address = %s,
                    valid_id_type = %s
                WHERE id = %s
                """,
                (
                    contact,
                    birthdate,
                    email_address,
                    valid_id_type,
                    session["user_id"]
                )
            )

            conn.commit()

        except Exception:
            conn.rollback()
            conn.close()

            flash("❌ Something went wrong while confirming adoption.")
            return redirect(url_for("confirm_info"))

        conn.close()

        # -------------------------------------------------
        # CLEAR ADOPTION SHELF
        # -------------------------------------------------

        session["adopt_shelf"] = []
        session.pop("pending_adoption", None)

        flash(
            "✅ Adoption has been set for evaluation. "
            "Please wait for updates."
        )

        return redirect(url_for("adopt_shelf"))

    return render_template("confirm_info.html")


# =========================================================
# ADOPTION SHELF
# =========================================================

@app.route("/AdoptShelf")
def adopt_shelf():

    if "user_id" not in session:
        flash("⚠️ Please log in first to adopt a pet.")
        return redirect(url_for("loging"))

    shelf = session.get("adopt_shelf", [])

    return render_template(
        "adoptshelf.html",
        shelf=shelf
    )


# =========================================================
# ADD PET TO ADOPTION SHELF
# =========================================================

@app.route("/add_to_shelf", methods=["POST"])
def add_to_shelf():

    if "user_id" not in session:
        return jsonify({
            "message": "⚠️ Please log in first."
        })

    data = request.get_json()

    title = data.get("title")
    img = data.get("img")

    if not title or not img:
        return jsonify({
            "message": "❌ Missing pet data."
        })

    shelf = session.get("adopt_shelf", [])

    shelf.append({
        "title": title,
        "img": img
    })

    session["adopt_shelf"] = shelf

    return jsonify({
        "message": f"✅ {title} added to your Adopt Shelf!"
    })


# =========================================================
# SHOW PETS
# =========================================================

@app.route("/pets")
def show_pets():

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM pets")

    pets = cursor.fetchall()

    conn.close()

    return render_template(
        "pets_list.html",
        pets=pets
    )


# =========================================================
# DELETE PET
# =========================================================

@app.route("/delete_pet/<int:pet_id>", methods=["POST"])
def delete_pet(pet_id):

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM pets WHERE id = %s",
        (pet_id,)
    )

    conn.commit()
    conn.close()

    return redirect(url_for("show_pets"))


# =========================================================
# REMOVE USER
# =========================================================

@app.route("/remove_user/<int:user_id>")
def remove_user(user_id):

    if (
        session.get("username") != "admin"
        or session.get("password") != "admin123"
    ):
        return "Unauthorized Access", 403

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM users WHERE id = %s",
        (user_id,)
    )

    conn.commit()
    conn.close()

    return redirect("/authorized")


# =========================================================
# ADD PET
# =========================================================

@app.route("/add_pet", methods=["GET", "POST"])
def add_pet():

    if (
        session.get("username") != "admin"
        or session.get("password") != "admin123"
    ):
        flash(
            "⚠️ Unauthorized Access. Only admins can add pets."
        )

        return redirect(url_for("web"))

    if request.method == "POST":

        Name = request.form["Name"]
        Age = request.form["Age"]
        Date_Found = request.form["Date_Found"]
        Characteristics = request.form["Characteristics"]
        Information = request.form.get("Information", "")

        img_file = request.files.get("img")

        if img_file and img_file.filename:

            filename = secure_filename(img_file.filename)

            file_path = os.path.join(
                app.config["UPLOAD_FOLDER"],
                filename
            )

            img_file.save(file_path)

            img_path = f"uploads/{filename}"

        else:
            img_path = ""

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO pets
            (
                Name,
                Age,
                Date_Found,
                Characteristics,
                Information,
                img
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                Name,
                Age,
                Date_Found,
                Characteristics,
                Information,
                img_path
            )
        )

        conn.commit()
        conn.close()

        flash("✅ Pet added successfully!")

        return redirect(url_for("web"))

    return render_template("add_pet.html")


# =========================================================
# HOME
# =========================================================

@app.route("/Home")
def web():

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM pets")

    pets = cursor.fetchall()

    conn.close()

    return render_template(
        "web.html",
        pets=pets
    )


# =========================================================
# LOGIN PAGE
# =========================================================

@app.route("/loging", methods=["GET", "POST"])
def loging():

    msg = ""

    if "user_id" in session:

        msg = "⚠️ You are already logged in."

        return render_template(
            "loging.html",
            msg=msg
        )

    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM users WHERE username = %s",
            (username,)
        )

        user = cursor.fetchone()

        conn.close()

        if user:

            if user["password"] == password:

                session["user_id"] = user["id"]
                session["username"] = user["username"]

                # Keeping this because your current admin
                # authorization system uses it.
                session["password"] = user["password"]

                msg = "✅ Login successful!"

                return redirect(url_for("web"))

            else:

                msg = "❌ Incorrect password."

        else:

            msg = "❌ Username not found."

    return render_template(
        "loging.html",
        msg=msg
    )


# =========================================================
# REGISTER
# =========================================================

@app.route("/register", methods=["GET", "POST"])
def register():

    msg = ""

    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")
        email = request.form.get("email")

        conn = get_db_connection()
        cursor = conn.cursor()

        try:

            cursor.execute(
                """
                INSERT INTO users
                (
                    username,
                    password,
                    email
                )
                VALUES (%s, %s, %s)
                """,
                (
                    username,
                    password,
                    email
                )
            )

            conn.commit()

            msg = "✅ Successfully registered!"

        except psycopg2.IntegrityError:

            conn.rollback()

            msg = "❌ Username or Email already exists!"

        finally:

            conn.close()

    return render_template(
        "register.html",
        msg=msg
    )


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    flash("You have been logged out.")

    return redirect(url_for("loging"))


# =========================================================
# AUTHORIZED PERSONNEL / REGISTERED USERS
# =========================================================

@app.route("/authorized")
def view_users():

    if (
        session.get("username") != "admin"
        or session.get("password") != "admin123"
    ):
        return "Unauthorized Access", 403

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users")

    users = cursor.fetchall()

    conn.close()

    output = """
<!DOCTYPE html>
<html lang="en">

<head>

<meta charset="UTF-8">

<title>Registered Users</title>

<meta name="viewport"
      content="width=device-width, initial-scale=1.0">

<style>

* {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
    font-family: "Poppins", Arial, Helvetica, sans-serif;
}

body {
    font-family: Arial, sans-serif;
    margin: 0;
    background-image: url('/static/dogcat1.jpg');
    background-size: cover;
    background-position: center;
    background-attachment: fixed;
}

.navbar {
    background-color: #333;
    overflow: hidden;
}

.navbar a {
    float: left;
    display: block;
    color: white;
    text-align: center;
    padding: 14px 20px;
    text-decoration: none;
}

.navbar a:hover {
    background-color: #ddd;
    color: black;
}

.navbar a.active {
    background-color: #04AA6D;
    color: white;
}

.container {
    width: 90%;
    margin: 100px auto 40px;
    background-color: rgba(255, 255, 255, 0.96);
    padding: 40px;
    border-radius: 10px;
    box-shadow: 0 0 15px rgba(0,0,0,0.3);
    overflow-x: auto;
}

h2 {
    text-align: center;
    margin-bottom: 30px;
    font-size: 28px;
    color: #333;
}

table {
    width: 100%;
    border-collapse: separate;
    border-spacing: 0;
    font-size: 16px;
}

th,
td {
    padding: 15px;
    text-align: center;
    border-bottom: 1px solid #ccc;
}

th {
    background-color: #f5f5f5;
    color: #333;
}

tr:nth-child(even) {
    background-color: #fafafa;
}

img {
    max-width: 100px;
    border-radius: 6px;
    border: 1px solid #ccc;
}

form {
    text-align: center;
    margin-top: 30px;
}

input[type="submit"] {
    padding: 12px 30px;
    background-color: #e60000;
    color: white;
    border: none;
    border-radius: 6px;
    font-size: 16px;
    cursor: pointer;
}

input[type="submit"]:hover {
    background-color: #cc0000;
}

a.remove {
    color: red;
    text-decoration: none;
    font-weight: bold;
}

a.remove:hover {
    text-decoration: underline;
}

</style>

</head>

<body>

<div class="navbar">

<a href="/Home">
Home
</a>

<a href="/authorized" class="active">
Authorized Personnel
</a>

<a href="/view_orders">
View Pet Adoption
</a>

<a href="/pets">
Manage Pets
</a>

<a href="/add_pet">
Add Pet
</a>

</div>

<div class="container">

<h2>Registered Users</h2>

<table>

<thead>

<tr>

<th>ID</th>
<th>Username</th>
<th>Password</th>
<th>Email</th>
<th>Contact</th>
<th>Birthdate</th>
<th>Age</th>
<th>Email Address</th>
<th>Valid ID type</th>
<th>Action</th>

</tr>

</thead>

<tbody>
"""

    for user in users:

        output += f"""
<tr>

<td>{user["id"]}</td>

<td>{user["username"]}</td>

<td>{user["password"]}</td>

<td>{user["email"]}</td>

<td>{user["contact"] or "None"}</td>

<td>{user["birthdate"] or "None"}</td>

<td>{user["age"] or "None"}</td>

<td>{user["address"] or "None"}</td>

<td>{user["valid_id_type"] or "None"}</td>

<td>
<a
    class="remove"
    href="/remove_user/{user['id']}"
    onclick="return confirm('Are you sure you want to remove this user?')"
>
Remove
</a>
</td>

</tr>
"""

    output += """
</tbody>

</table>

<form
    method="POST"
    action="/clear_users"
    onsubmit="return confirm('Clear all users?')"
>

<input
    type="submit"
    value="Clear All"
>

</form>

</div>

</body>

</html>
"""

    return output


# =========================================================
# CLEAR ALL USERS
# =========================================================

@app.route("/clear_users", methods=["POST"])
def clear_users():

    if (
        session.get("username") != "admin"
        or session.get("password") != "admin123"
    ):
        return "Unauthorized Access", 403

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM users")

    conn.commit()
    conn.close()

    return redirect("/authorized")


# =========================================================
# RUN APPLICATION
# =========================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=True
    )
```

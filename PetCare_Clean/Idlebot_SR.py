from flask import Flask, redirect, url_for, render_template, request, flash, session, jsonify
from werkzeug.utils import secure_filename
from psycopg2.extras import RealDictCursor
import psycopg2
import os

def get_db_connection():
    return psycopg2.connect(
        os.environ["DATABASE_URL"],
        cursor_factory=RealDictCursor
    )

app = Flask(__name__, template_folder='templates')

UPLOAD_FOLDER = '/tmp/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.secret_key = os.urandom(24)

from flask import session, jsonify, render_template
from datetime import datetime

@app.route('/')
def index():
    return redirect(url_for('web'))

@app.route("/adoption_status")
def adoption_status():
    if "user_id" not in session:
        return redirect(url_for("loging"))

    user_id = session["user_id"]

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM adoptions WHERE user_id = %s",
    (user_id,)
                  )

adoptions = cursor.fetchall()
conn.close()

    return render_template("adoption_status.html", adoptions=adoptions)


@app.route("/update_status/<int:adoption_id>", methods=["POST"])
def update_status(adoption_id):
    if session.get("username") != "admin" or session.get("password") != "admin123":
        return "Unauthorized Access", 403

    new_status = request.form.get("status")

    conn = sqlite3.connect("pets.db")
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
    if session.get("username") != "admin" or session.get("password") != "admin123":
        return "Unauthorized Access", 403

    conn = sqlite3.connect("pets.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM adoptions WHERE id = ?", (adoption_id,))
    conn.commit()
    conn.close()

    flash("🗑️ Adoption record removed.")
    return redirect(url_for("view_orders"))


@app.route("/view_orders")
def view_orders():
    if session.get("username") != "admin" or session.get("password") != "admin123":
        return "Unauthorized Access", 403

    conn = sqlite3.connect("pets.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM adoptions")
    adoptions = cursor.fetchall()
    conn.close()

    return render_template("view_orders.html", adoptions=adoptions)


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
        name = request.form["name"]
        email_address = request.form["email"]
        contact = request.form["contact"]
        birthdate = request.form["birthdate"]
        valid_id_type = request.form["valid_id_type"]
        

        pets = session["pending_adoption"]

        conn = sqlite3.connect("pets.db")
        cursor = conn.cursor()

        for pet in pets:
            cursor.execute("""
                INSERT INTO adoptions (user_id, pet_name, pet_img, status)
                VALUES (?, ?, ?, ?)
            """, (session["user_id"], pet["title"], pet["img"], "Pending Evaluation"))

        conn.commit()
        conn.close()

      
        conn = sqlite3.connect("users.db")
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE users SET
                contact = ?, birthdate = ?, address = ?, valid_id_type = ?
            WHERE id = ?
        """, (contact, birthdate, email_address, valid_id_type, session["user_id"]))
        conn.commit()
        conn.close()

       
        session["adopt_shelf"] = []
        session.pop("pending_adoption", None)

        flash("✅ Adoption has been set for evaluation. Please wait for updates.")
        return redirect(url_for("adopt_shelf"))

    return render_template("confirm_info.html")



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


@app.route("/pets") 
def show_pets():
    conn = sqlite3.connect("pets.db")
    conn.row_factory = sqlite3.Row 
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pets") 
    pets = cursor.fetchall() 
    conn.close() 
    return render_template("pets_list.html", pets=pets)

@app.route("/delete_pet/<int:pet_id>", methods=["POST"])
def delete_pet(pet_id):
    conn = sqlite3.connect("pets.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM pets WHERE id = ?", (pet_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("show_pets"))


@app.route('/remove_user/<int:user_id>')
def remove_user(user_id):
    if session.get("username") != "admin" or session.get("password") != "admin123":
        return "Unauthorized Access", 403

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    return redirect('/authorized')  




app.config['UPLOAD_FOLDER'] = '/tmp/uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@app.route('/add_pet', methods=['GET', 'POST'])
def add_pet():
    # Check if user is logged in as admin
    if session.get("username") != "admin" or session.get("password") != "admin123":
        flash("⚠️ Unauthorized Access. Only admins can add pets.")
        return redirect(url_for('web'))
    
    if request.method == 'POST':
        Name = request.form['Name']
        Age = request.form['Age']
        Date_Found = request.form['Date_Found']
        Characteristics = request.form['Characteristics']
        Information = request.form.get('Information', '')


        img_file = request.files['img']
        if img_file:
            filename = secure_filename(img_file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            img_file.save(file_path)
            img_path = f'uploads/{filename}'

        else:
            img_path = ''

        conn = sqlite3.connect('pets.db')
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO pets 
                          (Name, Age, Date_Found, Characteristics, Information, img)
                          VALUES (?, ?, ?, ?, ?, ?)''',
                       (Name, Age, Date_Found, Characteristics, Information, img_path))
        conn.commit()
        conn.close()

        flash("✅ Pet added successfully!")
        return redirect(url_for('web'))

    return render_template("add_pet.html")




@app.route('/Home')
def web():
    conn = sqlite3.connect("pets.db)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pets")
    pets = cursor.fetchall()
    conn.close()

    return render_template("web.html", pets=pets)




@app.route("/loging")
def logging():
    return render_template('loging.html')    



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
            cursor.execute("INSERT INTO users (username, password, email) VALUES (?, ?, ?)",
                           (username, password, email))
            conn.commit()
            msg = "✅ Successfully registered!"
        except sqlite3.IntegrityError:
            msg = "❌ Username or Email already exists!"
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

        if user:
            if user["password"] == password:
                session["user_id"] = user["id"]
                session["username"] = user["username"]
                session["password"] = user["password"]  # 

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

@app.route('/authorized')
def view_users():
    if session.get("username") != "admin" or session.get("password") != "admin123":
        return "Unauthorized Access", 403

    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()
    conn.close()

    output = """
<!DOCTYPE html>
<html lang="en">
<head>
<link rel="stylesheet" type="text/css" href="{{ url_for('static', filename='web.css') }}">
    <meta charset="UTF-8">
    <title>Registered Users</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>

    /* 🌟 Global Reset and Base Styles */
* {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
    font-family: "Poppins", Arial, Helvetica, sans-serif;
    scroll-behavior: smooth;
}

body {
    background: url('dogcat1.jpg') center/cover no-repeat fixed;
    color: #222;
    line-height: 1.6;
    overflow-x: hidden;
}

/* 🌟 Heading */
h1 {
    text-align: center;
    color: #fff;
    font-size: 4em;
    margin-top: 60px;
    font-weight: 700;
    letter-spacing: 2px;
    text-transform: uppercase;
    text-shadow: 0 6px 18px rgba(0, 0, 0, 0.5);
    animation: fadeInDown 1.2s ease;
    transition: text-shadow 0.4s ease, transform 0.3s ease;
}

h1:hover {
    transform: scale(1.05);
    text-shadow: 0 8px 20px rgba(0, 0, 0, 0.6);
}

/* 🌟 Navbar */
.navbar {
    background: rgba(0, 0, 0, 0.75);
    backdrop-filter: blur(10px);
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 75px;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 35px;
    z-index: 1000;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    animation: fadeInDown 1s ease;
}

.navbar a {
    color: #fff;
    text-decoration: none;
    font-size: 1.1rem;
    font-weight: 500;
    text-transform: uppercase;
    padding: 10px 18px;
    border-radius: 8px;
    transition: all 0.4s ease;
    position: relative;
}

.navbar a::after {
    content: "";
    position: absolute;
    left: 50%;
    bottom: 0;
    transform: translateX(-50%);
    width: 0%;
    height: 3px;
    background: #52cf67;
    transition: width 0.3s ease;
    border-radius: 5px;
}

.navbar a:hover::after {
    width: 100%;
}

.navbar a:hover,
.navbar a.active {
    color: #52cf67;
    transform: translateY(-2px);
}

/* 🌟 Book List Section */
.book-list {
    display: flex;
    flex-wrap: nowrap;
    overflow-x: auto;
    padding: 120px 60px 40px;
    gap: 25px;
    background: rgba(255, 255, 255, 0.15);
    border-radius: 20px;
    margin: 80px auto 40px;
    width: 90%;
    scroll-behavior: smooth;
    box-shadow: 0 6px 18px rgba(0, 0, 0, 0.25);
    backdrop-filter: blur(8px);
    animation: fadeInUp 1.5s ease;
}

.book {
    flex-shrink: 0;
    background: rgba(255, 255, 255, 0.95);
    border: 1px solid #ddd;
    border-radius: 15px;
    padding: 18px;
    width: 220px;
    text-align: center;
    transition: all 0.4s ease;
    cursor: pointer;
    box-shadow: 0 4px 10px rgba(0, 0, 0, 0.15);
    transform: perspective(800px) rotateY(0deg);
}

.book:hover {
    transform: perspective(800px) rotateY(6deg) translateY(-8px);
    box-shadow: 0 12px 20px rgba(0, 0, 0, 0.25);
    background: linear-gradient(145deg, #e9f3ff, #ffffff);
}

.book img {
    width: 100%;
    height: 260px;
    object-fit: cover;
    border-radius: 10px;
    transition: transform 0.4s ease;
}

.book:hover img {
    transform: scale(1.05);
}

/* 🌟 Add-to-Shelf Button */
.add-to-shelf {
    margin-top: 12px;
    padding: 10px 14px;
    background: linear-gradient(135deg, #007bff, #00d4ff);
    color: white;
    border: none;
    border-radius: 10px;
    font-size: 0.95rem;
    font-weight: 600;
    letter-spacing: 0.5px;
    cursor: pointer;
    transition: all 0.4s ease;
    box-shadow: 0 3px 8px rgba(0, 123, 255, 0.3);
}

.add-to-shelf:hover {
    background: linear-gradient(135deg, #0056b3, #00aaff);
    transform: translateY(-3px);
    box-shadow: 0 6px 15px rgba(0, 123, 255, 0.4);
}

/* 🌟 Modal Styles */
.modal {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0, 0, 0, 0.6);
    display: flex;
    justify-content: center;
    align-items: center;
    visibility: visible;
    opacity: 1;
    transition: all 0.3s ease-in-out;
    animation: fadeIn 0.8s ease;
}

#closeBtn {
    position: absolute;
    top: 15px;
    right: 15px;
    background: none;
    border: none;
    color: #555;
    font-size: 24px;
    cursor: pointer;
    transition: 0.3s ease;
}

#closeBtn:hover {
    color: #007bff;
    transform: scale(1.2);
}

.form-container {
    background: white;
    padding: 35px;
    border-radius: 15px;
    box-shadow: 0 10px 25px rgba(0, 0, 0, 0.25);
    width: 360px;
    max-width: 90%;
    animation: popUp 0.6s ease;
}

.form-container h3 {
    text-align: center;
    color: #007bff;
    margin-bottom: 20px;
    font-weight: 600;
}

.form-container input {
    width: 100%;
    padding: 12px;
    margin-bottom: 18px;
    border-radius: 8px;
    border: 1px solid #ccc;
    font-size: 1rem;
    transition: border 0.3s, box-shadow 0.3s;
}

.form-container input:focus {
    border-color: #007bff;
    outline: none;
    box-shadow: 0 0 6px rgba(0, 123, 255, 0.4);
}

.form-container button {
    width: 100%;
    padding: 12px;
    background: linear-gradient(135deg, #007bff, #00d4ff);
    color: white;
    border-radius: 8px;
    border: none;
    font-size: 1rem;
    cursor: pointer;
    font-weight: 600;
    transition: 0.4s ease;
}

.form-container button:hover {
    background: linear-gradient(135deg, #0056b3, #00aaff);
    transform: translateY(-3px);
}

/* 🌟 Activity Log */
.activity-log {
    width: 85%;
    margin: 50px auto;
    padding: 25px;
    background: rgba(255, 255, 255, 0.95);
    border-radius: 15px;
    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.15);
    max-height: 350px;
    overflow-y: auto;
    animation: fadeInUp 1.2s ease;
}

.activity-log h3 {
    color: #007bff;
    margin-bottom: 15px;
}

.activity-entry {
    padding: 10px;
    border-bottom: 1px solid #eee;
    transition: 0.3s ease;
}

.activity-entry:hover {
    background: #f7faff;
    transform: scale(1.01);
}

.activity-entry span {
    font-weight: bold;
    color: #333;
}

/* 🌟 Footer */
.footer {
    background: #0b0b0b;
    color: #ddd;
    text-align: center;
    padding: 25px;
    font-size: 1rem;
    letter-spacing: 1px;
    margin-top: 50px;
    animation: fadeInUp 1.2s ease;
}

.footer p {
    margin: 6px 0;
    transition: 0.3s ease;
}

.footer p:hover {
    color: #52cf67;
}

/* 🌟 Animations */
@keyframes fadeIn {
    from { opacity: 0; transform: scale(0.95); }
    to { opacity: 1; transform: scale(1); }
}

@keyframes fadeInUp {
    from { opacity: 0; transform: translateY(40px); }
    to { opacity: 1; transform: translateY(0); }
}

@keyframes fadeInDown {
    from { opacity: 0; transform: translateY(-40px); }
    to { opacity: 1; transform: translateY(0); }
}

@keyframes popUp {
    0% { transform: scale(0.8); opacity: 0; }
    100% { transform: scale(1); opacity: 1; }
}

/* 🌟 Responsive Design */
@media (max-width: 768px) {
    h1 {
        font-size: 2.5em;
    }

    .navbar {
        flex-wrap: wrap;
        height: auto;
        padding: 12px;
    }

    .book-list {
        flex-direction: column;
        align-items: center;
        width: 90%;
    }

    .book {
        width: 85%;
    }

    .form-container {
        width: 90%;
    }
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
            background:url_for('static', filename='black.jpg');
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
            margin: 40px auto;
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
        th, td {
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
    <a href="/Home">Home</a>
    <a href="/authorized" class="active">Authorized Personnel</a>
    <a href="/view_orders">View Pet Adoption</a>
    <a href="/pets">Manage Pets</a>
    <a href="/add_pet">Add Pet</a>
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
        valid_id_html = (
            f'<img src="/static/uploads/{user["valid_id_path"]}" alt="Valid ID">' 
            if user["valid_id_path"] else "No ID"
        )
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
                    <td>{user["valid_id_type"] or "None" }</td>
                    <td><a class="remove" href="/remove_user/{user['id']}" onclick="return confirm('Are you sure you want to remove this user?')">Remove</a></td>
                </tr>
        """

    output += """
            </tbody>
        </table>

        <form method="POST" action="/clear_users" onsubmit="return confirm('Clear all users?')">
            <input type="submit" value="Clear All">
        </form>
    </div>
</body>
</html>
    """

    return output



@app.route('/clear_users', methods=['POST'])
def clear_users():
    if session.get("username") != "admin" or session.get("password") != "admin123":
        return "Unauthorized Access", 403

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users")
    conn.commit()
    conn.close()
    return redirect('/authorized')

def get_db_connection():
    return psycopg2.connect(
        os.environ["DATABASE_URL"],
        cursor_factory=RealDictCursor
    )

if __name__ == '__main__':
    app.run(debug=True)



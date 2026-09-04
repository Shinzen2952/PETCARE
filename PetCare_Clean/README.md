# 🐾 PetCare Adoption Website

A Flask-based web application for pet adoption management with admin controls and user adoption tracking.

---

## 📁 Project Structure

```
PetCare_Clean/
├── Idlebot_SR.py          # Main Flask application
├── users_db.py            # User database initialization
├── pets_db.py             # Pets database initialization
├── adoptions_db.py        # Adoptions database initialization
├── adoption_db.py         # Additional adoption database setup
├── users.db               # User database (SQLite)
├── pets.db                # Pets database (SQLite)
├── templates/             # HTML templates
│   ├── web.html           # Home page
│   ├── loging.html        # Login page
│   ├── register.html      # Registration page
│   ├── add_pet.html       # Add pet form (admin)
│   ├── pets_list.html     # Manage pets list (admin)
│   ├── view_orders.html   # View adoptions (admin)
│   ├── adoptshelf.html    # User's adoption shelf
│   ├── confirm_info.html  # Adoption confirmation form
│   └── ...                # Other templates
└── static/                # Static files (CSS, images)
    ├── web.css            # Main stylesheet
    ├── style.css          # Additional styles
    ├── styles.css         # More styles
    ├── uploads/           # User-uploaded pet images
    └── *.jpg              # Pet and UI images
```

---

## 🚀 How to Run the Website

### **First Time Setup**

1. **Open the Project Folder**
   - Navigate to: `C:\Users\LENOVO THINKPAD L470\Desktop\Project PetCare\Idlebot-main new\Idlebot-main-20251004T022525Z-1-001\Idlebot-main\Idlebot-main\PetCare_Clean`

2. **Open Command Prompt or PowerShell**
   - Press `Windows + R`
   - Type `cmd` or `powershell` and press Enter
   - Navigate to the project folder:
     ```bash
     cd "C:\Users\LENOVO THINKPAD L470\Desktop\Project PetCare\Idlebot-main new\Idlebot-main-20251004T022525Z-1-001\Idlebot-main\Idlebot-main\PetCare_Clean"
     ```

3. **Install Python (if not installed)**
   - Download from: https://www.python.org/downloads/
   - During installation, check "Add Python to PATH"

4. **Install Required Packages**
   ```bash
   pip install flask
   ```

5. **Initialize Databases (First Time Only)**
   ```bash
   python users_db.py
   python pets_db.py
   python adoptions_db.py
   ```

6. **Run the Application**
   ```bash
   python Idlebot_SR.py
   ```

7. **Open in Browser**
   - Go to: `http://127.0.0.1:5000` or `http://localhost:5000`

---

## 🔄 How to Reopen After Closing

### **Method 1: Using Command Prompt/PowerShell**

1. Open Command Prompt or PowerShell
2. Navigate to project folder:
   ```bash
   cd "C:\Users\LENOVO THINKPAD L470\Desktop\Project PetCare\Idlebot-main new\Idlebot-main-20251004T022525Z-1-001\Idlebot-main\Idlebot-main\PetCare_Clean"
   ```
3. Run the application:
   ```bash
   python Idlebot_SR.py
   ```
4. Open browser and go to: `http://127.0.0.1:5000`

### **Method 2: Using VS Code**

1. Open VS Code
2. Click `File` → `Open Folder`
3. Navigate to and select the `PetCare_Clean` folder
4. Open the integrated terminal: `Terminal` → `New Terminal` (or press `` Ctrl + ` ``)
5. Run:
   ```bash
   python Idlebot_SR.py
   ```
6. Open browser and go to: `http://127.0.0.1:5000`

### **Method 3: Create a Shortcut (Easiest)**

1. Create a new text file named `start_petcare.bat` in the `PetCare_Clean` folder
2. Add this content:
   ```batch
   @echo off
   cd /d "%~dp0"
   python Idlebot_SR.py
   pause
   ```
3. Save and double-click `start_petcare.bat` to start the server
4. Open browser and go to: `http://127.0.0.1:5000`

---

## 👤 Admin Access

**Admin Login Credentials:**
- **Username:** `admin`
- **Password:** `admin123`

**Admin Features:**
- View Pet Adoption requests
- Manage Pets (view, edit, delete)
- Add new pets
- Update adoption status
- Access authorized personnel page

---

## 🛑 How to Stop the Server

- Press `Ctrl + C` in the terminal/command prompt where the server is running
- Or simply close the terminal window

---

## 📝 Important Notes

1. **Database Files:** The `.db` files contain all your data (users, pets, adoptions). Don't delete them!
2. **Uploads Folder:** Pet images uploaded by admin are stored in `static/uploads/`
3. **Port 5000:** Make sure no other application is using port 5000
4. **Python Version:** This project works with Python 3.7+

---

## 🐛 Troubleshooting

### **Problem: "python is not recognized"**
- **Solution:** Install Python and make sure "Add to PATH" is checked during installation

### **Problem: "No module named 'flask'"**
- **Solution:** Run `pip install flask`

### **Problem: "Address already in use"**
- **Solution:** Another application is using port 5000. Close it or change the port in `Idlebot_SR.py` (last line: `app.run(debug=True, port=5001)`)

### **Problem: "Database is locked"**
- **Solution:** Close all instances of the application and try again

---

## 📧 Contact

For issues or questions about the PetCare adoption system, contact the administrator.

---

**Made with ❤️ for Pet Adoption**

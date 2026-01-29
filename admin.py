import streamlit as st
import sqlite3
from datetime import datetime
import hashlib
from PIL import Image
import pandas as pd
import base64
import altair as alt
import google.generativeai as genai


# ------------------ Configuration ------------------
st.set_page_config(page_title="LifeLink Blood Bank", layout="wide")

# ------------------ Session State ------------------
for key, default in {
    "logged_in": False,
    "username": "",
    "show_profile": False,
    "is_admin": False
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ------------------ Database Functions ------------------
def connect_db():
    return sqlite3.connect("lifelink.db")

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def init_db():
    db = connect_db()
    cursor = db.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS Users (
                        UserID INTEGER PRIMARY KEY AUTOINCREMENT,
                        Username TEXT UNIQUE,
                        Password TEXT,
                        FullName TEXT,
                        Age INTEGER,
                        Gender TEXT,
                        Contact TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS Donors (
                        DonorID INTEGER PRIMARY KEY AUTOINCREMENT,
                        Name TEXT,
                        Age INTEGER,
                        Gender TEXT,
                        BloodGroup TEXT,
                        Contact TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS Stock (
                        BloodGroup TEXT PRIMARY KEY,
                        Units INTEGER DEFAULT 0)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS Transactions (
                        TransactionID INTEGER PRIMARY KEY AUTOINCREMENT,
                        DonorID INTEGER,
                        BloodGroup TEXT,
                        Units INTEGER,
                        Type TEXT,
                        Date TEXT)''')
    cursor.execute("SELECT COUNT(*) FROM Stock")
    if cursor.fetchone()[0] == 0:
        for group in ['A+','A-','B+','B-','O+','O-','AB+','AB-']:
            cursor.execute("INSERT INTO Stock (BloodGroup, Units) VALUES (?, ?)", (group, 0))
    db.commit()
    db.close()

init_db()

# ------------------ Gemini AI Setup ------------------
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
gemini_model = genai.GenerativeModel("gemini-pro")


# ------------------ Auth & User Functions ------------------
def signup(username, password, full_name, age, gender, contact):
    db = connect_db()
    cursor = db.cursor()
    try:
        cursor.execute("INSERT INTO Users (Username, Password, FullName, Age, Gender, Contact) VALUES (?, ?, ?, ?, ?, ?)",
                       (username, hash_password(password), full_name, age, gender, contact))
        db.commit()
        st.success("✅ Signup successful!")
    except sqlite3.IntegrityError:
        st.error("❌ Username already exists.")
    db.close()

def login(username, password):
    db = connect_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM Users WHERE Username=? AND Password=?",
                   (username, hash_password(password)))
    user = cursor.fetchone()
    db.close()
    return user

def get_user_profile(username):
    db = connect_db()
    cursor = db.cursor()
    cursor.execute("SELECT FullName, Age, Gender, Contact FROM Users WHERE Username=?", (username,))
    profile = cursor.fetchone()
    db.close()
    return profile

# ------------------ Donor and Stock Management ------------------
def add_donor(name, age, gender, blood_group, contact):
    db = connect_db()
    cursor = db.cursor()
    cursor.execute("INSERT INTO Donors (Name, Age, Gender, BloodGroup, Contact) VALUES (?, ?, ?, ?, ?)",
                   (name, age, gender, blood_group.upper(), contact))
    db.commit()
    db.close()
    st.success("✅ Donor added successfully!")

def search_donor(blood_group):
    db = connect_db()
    cursor = db.cursor()
    cursor.execute("SELECT DonorID, Name, Age, Gender, Contact FROM Donors WHERE BloodGroup=?", (blood_group.upper(),))
    donors = cursor.fetchall()
    db.close()
    return donors

def view_all_donors():
    db = connect_db()
    cursor = db.cursor()
    cursor.execute("SELECT DonorID, Name, Age, Gender, BloodGroup, Contact FROM Donors")
    donors = cursor.fetchall()
    db.close()
    return donors

def update_stock(blood_group, units, t_type, donor_id=None):
    db = connect_db()
    cursor = db.cursor()
    if t_type == "Donation":
        cursor.execute("UPDATE Stock SET Units = Units + ? WHERE BloodGroup=?", (units, blood_group.upper()))
    elif t_type == "Issue":
        cursor.execute("SELECT Units FROM Stock WHERE BloodGroup=?", (blood_group.upper(),))
        result = cursor.fetchone()
        if not result or result[0] < units:
            st.error("❌ Not enough stock!")
            db.close()
            return
        cursor.execute("UPDATE Stock SET Units = Units - ? WHERE BloodGroup=?", (units, blood_group.upper()))
    cursor.execute("INSERT INTO Transactions (DonorID, BloodGroup, Units, Type, Date) VALUES (?, ?, ?, ?, ?)",
                   (donor_id, blood_group.upper(), units, t_type, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    db.commit()
    db.close()
    st.success(f"✅ {t_type} recorded successfully!")

def view_stock():
    db = connect_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM Stock")
    stock = cursor.fetchall()
    db.close()
    return stock

# ------------------ UI Helpers ------------------
def render_centered_table(df):
    st.markdown(
        df.to_html(index=False, classes="table table-striped table-bordered", justify='center'),
        unsafe_allow_html=True
    )
    st.markdown("""
        <style>
        .dataframe {margin-left:auto; margin-right:auto; width:80%; text-align:center;}
        table, th, td {text-align:center;}
        </style>
    """, unsafe_allow_html=True)

def image_to_base64(img_path):
    with open(img_path, "rb") as f:
        return base64.b64encode(f.read()).decode()

def display_main_logo():
    try:
        logo = Image.open(r"C:\Users\ashis\OneDrive\Desktop\sanika\Lifelink\logo.jpeg")
        st.image(logo, width=300)
    except:
        st.warning("⚠️ Logo not found.")

def display_small_logo():
    try:
        b64 = image_to_base64(r"C:\Users\ashis\OneDrive\Desktop\sanika\Lifelink\logo.jpeg")
        st.markdown(
            f"<img src='data:image/png;base64,{b64}' style='position:fixed; top:80px; right:10px; width:60px; z-index:100;'>",
            unsafe_allow_html=True
        )
    except:
        pass
# ------------------ Admin Auth ------------------
def admin_login(username, password):
    return username == "admin" and password == "admin123"

# ------------------ Main App ------------------
if not st.session_state.logged_in:
    menu = ["Home", "Signup", "Login"]
    choice = st.sidebar.selectbox("Menu", menu)
    if choice == "Home":
        st.markdown("<div style='text-align:center;'>", unsafe_allow_html=True)
        display_main_logo()
        st.markdown("<h1 style='color:#E63946;'>Welcome to LifeLink!</h1>", unsafe_allow_html=True)
        st.markdown("<p style='font-size:22px;'>Manage donors and blood stock easily.</p>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    elif choice == "Signup":
        st.subheader("Create an Account")
        uname = st.text_input("Username")
        pw = st.text_input("Password", type='password')
        full_name = st.text_input("Full Name")
        age = st.number_input("Age", 0, 100)
        gender = st.selectbox("Gender", ["Male", "Female", "Other"])
        contact = st.text_input("Contact")
        if st.button("Signup"):
            signup(uname, pw, full_name, age, gender, contact)
    elif choice == "Login":
        st.subheader("Login")
        uname = st.text_input("Username")
        pw = st.text_input("Password", type='password')
        if st.button("Login"):

    # ---- ADMIN LOGIN ----
    if admin_login(uname, pw):
        st.session_state.logged_in = True
        st.session_state.is_admin = True
        st.session_state.username = "ADMIN"
        st.session_state.show_profile = False
        st.rerun()

    # ---- NORMAL USER LOGIN ----
    user = login(uname, pw)
    if user:
        st.session_state.logged_in = True
        st.session_state.is_admin = False
        st.session_state.username = uname
        st.session_state.show_profile = False
        st.rerun()

    else:
        st.error("❌ Invalid username or password")

else:
    display_small_logo()
    st.sidebar.success(f"Logged in as: {st.session_state.username}")

    st.sidebar.title("Navigation")
    if st.session_state.is_admin:
    action = st.sidebar.radio(
        "Admin Panel",
        ["Admin Dashboard", "AI Insights", "Predict Shortage"]
    )
else:
    action = st.sidebar.radio(
        "Menu",
        ["Home","Add Donor","Manage Donors","Search Donor","View Donors","Record Donation","Issue Blood","View Stock"]
    )

    st.sidebar.markdown("---")
    st.sidebar.markdown("**Account**")
    if st.sidebar.button("View Profile"):
        st.session_state.show_profile = True

    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.show_profile = False
        st.rerun()

    # ------------------ Main Content ------------------
    if st.session_state.show_profile:
        profile = get_user_profile(st.session_state.username)
        if profile:
            full_name, age, gender, contact = profile
            st.subheader("My Profile")
            st.write(f"**Full Name:** {full_name}")
            st.write(f"**Username:** {st.session_state.username}")
            st.write(f"**Age:** {age}")
            st.write(f"**Gender:** {gender}")
            st.write(f"**Contact:** {contact}")
            st.markdown("---")
            st.info("You can edit your details below.")

            # ---------- Editable Fields ----------
            new_full_name = st.text_input("Full Name", full_name)
            new_age = st.number_input("Age", 0, 100, age)
            new_gender = st.selectbox("Gender", ["Male","Female","Other"], ["Male","Female","Other"].index(gender))
            new_contact = st.text_input("Contact", contact)

            if st.button("Update Profile"):
                db = connect_db()
                cursor = db.cursor()
                cursor.execute(
                    "UPDATE Users SET FullName=?, Age=?, Gender=?, Contact=? WHERE Username=?",
                    (new_full_name, new_age, new_gender, new_contact, st.session_state.username)
                )
                db.commit()
                db.close()
                st.success("✅ Profile updated successfully!")
                st.rerun()

    else:
        # --------- Action Pages ---------
        if action == "Home":
            st.markdown("<h2 style='text-align:center;'>Welcome to LifeLink Dashboard</h2>", unsafe_allow_html=True)
            st.markdown("<p style='text-align:center;'>Use the sidebar to navigate through the system.</p>", unsafe_allow_html=True)
        elif action == "Add Donor":
            st.subheader("Add New Donor")
            n = st.text_input("Name")
            a = st.number_input("Age", 0, 100)
            g = st.selectbox("Gender", ["Male","Female","Other"])
            bg = st.selectbox("Blood Group", ['A+','A-','B+','B-','O+','O-','AB+','AB-'])
            ct = st.text_input("Contact")
            if st.button("Add Donor"):
                add_donor(n, a, g, bg, ct)

        elif action == "Manage Donors":
            st.subheader("Manage Donors")
            donors = view_all_donors()
            if donors:
                df = pd.DataFrame(donors, columns=["ID","Name","Age","Gender","Blood Group","Contact"])
                selected_id = st.selectbox("Select Donor to Edit/Delete", df["ID"])
                donor_row = df[df["ID"]==selected_id].iloc[0]

                name = st.text_input("Name", donor_row["Name"])
                age = st.number_input("Age", 0, 100, donor_row["Age"])
                gender = st.selectbox("Gender", ["Male","Female","Other"], ["Male","Female","Other"].index(donor_row["Gender"]))
                blood_group = st.selectbox("Blood Group", ['A+','A-','B+','B-','O+','O-','AB+','AB-'], 
                                           ['A+','A-','B+','B-','O+','O-','AB+','AB-'].index(donor_row["Blood Group"]))
                contact = st.text_input("Contact", donor_row["Contact"])

                if st.button("Update Donor"):
                    db = connect_db()
                    cursor = db.cursor()
                    cursor.execute("UPDATE Donors SET Name=?, Age=?, Gender=?, BloodGroup=?, Contact=? WHERE DonorID=?",
                                   (name, age, gender, blood_group, contact, selected_id))
                    db.commit()
                    db.close()
                    st.success("✅ Donor updated successfully!")
                    st.rerun()

                if st.button("Delete Donor"):
                    db = connect_db()
                    cursor = db.cursor()
                    cursor.execute("DELETE FROM Donors WHERE DonorID=?", (selected_id,))
                    db.commit()
                    db.close()
                    st.success("✅ Donor deleted successfully!")
                    st.rerun()
            else:
                st.info("No donors found.")

        elif action == "Search Donor":
            st.subheader("Search Donor by Blood Group")
            bg = st.selectbox("Blood Group", ['A+','A-','B+','B-','O+','O-','AB+','AB-'])
            if st.button("Search"):
                donors = search_donor(bg)
                if donors:
                    df = pd.DataFrame(donors, columns=["ID","Name","Age","Gender","Contact"])
                    render_centered_table(df)
                else:
                    st.info("No donors found for this blood group.")

        elif action == "View Donors":
            st.subheader("All Donors")
            donors = view_all_donors()
            if donors:
                df = pd.DataFrame(donors, columns=["ID","Name","Age","Gender","Blood Group","Contact"])
                render_centered_table(df)
            else:
                st.info("No donors found.")

        elif action == "Record Donation":
            st.subheader("Record Donation")
            did = st.number_input("Donor ID", min_value=0)
            bg = st.selectbox("Blood Group", ['A+','A-','B+','B-','O+','O-','AB+','AB-'])
            u = st.number_input("Units", min_value=1)
            if st.button("Record Donation"):
                update_stock(bg, u, "Donation", did)

        elif action == "Issue Blood":
            st.subheader("Issue Blood")
            bg = st.selectbox("Blood Group", ['A+','A-','B+','B-','O+','O-','AB+','AB-'])
            u = st.number_input("Units", min_value=1)
            if st.button("Issue Blood"):
                update_stock(bg, u, "Issue")

        elif action == "View Stock":
            st.subheader("Current Blood Stock")
            stock = view_stock()
            df_stock = pd.DataFrame(stock, columns=["Blood Group","Units"])
            render_centered_table(df_stock)

            st.markdown("---")
            st.write("### Blood Stock Levels")
            chart1 = alt.Chart(df_stock).mark_bar().encode(
                x='Blood Group',
                y='Units',
                color='Blood Group'
            )
            st.altair_chart(chart1, use_container_width=True)

        elif action == "AI Insights" and st.session_state.is_admin:
            st.subheader("🤖 Gemini AI Insights")
        
            stock = view_stock()
            df_stock = pd.DataFrame(stock, columns=["Blood Group", "Units"])
        
            st.write("### Current Stock Data")
            st.dataframe(df_stock)
        
            prompt = f"""
            You are an AI healthcare analyst.
            Below is the current blood stock data.
        
            {df_stock}
        
            1. Identify blood groups at risk
            2. Predict shortages
            3. Give clear, actionable advice for hospital admins
            """
        
            if st.button("Generate AI Insights"):
                response = gemini_model.generate_content(prompt)
                st.success("AI Analysis Complete")
                st.write(response.text)


            # Donations over time
            db = connect_db()
            cursor = db.cursor()
            cursor.execute("SELECT Date, Units FROM Transactions WHERE Type='Donation'")
            data = cursor.fetchall()
            db.close()
            if data:
                df_tx = pd.DataFrame(data, columns=["Date","Units"])
                df_tx['Date'] = pd.to_datetime(df_tx['Date'])
                df_grouped = df_tx.groupby(df_tx['Date'].dt.date)['Units'].sum().reset_index()
                st.write("### Donations Over Time")
                chart2 = alt.Chart(df_grouped).mark_line(point=True).encode(
                    x='Date',
                    y='Units'
                )
                st.altair_chart(chart2, use_container_width=True)

            # Donor gender pie chart
            donors = view_all_donors()
            if donors:
                df_d = pd.DataFrame(donors, columns=["ID","Name","Age","Gender","Blood Group","Contact"])
                st.write("### Donor Gender Distribution")
                chart3 = alt.Chart(df_d).mark_arc().encode(
                    theta=alt.Theta(field="Gender", type="quantitative", aggregate="count"),
                    color="Gender:N"
                )
                st.altair_chart(chart3, use_container_width=True)





# lifelink_user_app.py
import streamlit as st
import sqlite3
from datetime import datetime, date
import hashlib
from PIL import Image
import pandas as pd
from pathlib import Path
import altair as alt
import base64

# ------------------ CONFIG ------------------
st.set_page_config(page_title="LifeLink Blood Bank - User", layout="wide")

# Updated LOGO PATH
LOGO_PATH = Path(r"C:\Users\ashis\OneDrive\Desktop\sanika\Lifelink\logo.jpeg")

BASE_DIR = Path(__file__).parent if "__file__" in globals() else Path.cwd()
DB_PATH = BASE_DIR / "lifelink.db"

# ------------------ SESSION DEFAULTS ------------------
for key, default in {
    "logged_in": False,
    "username": "",
    "show_profile": False,
    "selected_action": "Home",
    "role": "User"
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ------------------ DATABASE HELPERS ------------------
def connect_db():
    return sqlite3.connect(str(DB_PATH), check_same_thread=False)

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def init_db():
    db = connect_db()
    cur = db.cursor()

    cur.execute('''CREATE TABLE IF NOT EXISTS Users (
                    UserID INTEGER PRIMARY KEY AUTOINCREMENT,
                    Username TEXT UNIQUE,
                    Password TEXT,
                    FullName TEXT,
                    Age INTEGER,
                    Gender TEXT,
                    Contact TEXT,
                    Role TEXT DEFAULT 'User'
                 )''')

    cur.execute('''CREATE TABLE IF NOT EXISTS Donors (
                    DonorID INTEGER PRIMARY KEY AUTOINCREMENT,
                    Name TEXT,
                    Age INTEGER,
                    Gender TEXT,
                    BloodGroup TEXT,
                    Contact TEXT
                 )''')

    cur.execute('''CREATE TABLE IF NOT EXISTS Stock (
                    BloodGroup TEXT PRIMARY KEY,
                    Units INTEGER DEFAULT 0
                 )''')

    cur.execute('''CREATE TABLE IF NOT EXISTS Transactions (
                    TransactionID INTEGER PRIMARY KEY AUTOINCREMENT,
                    DonorID INTEGER,
                    BloodGroup TEXT,
                    Units INTEGER,
                    Type TEXT,
                    Date TEXT
                 )''')

    cur.execute('''CREATE TABLE IF NOT EXISTS Bookings (
                    BookingID INTEGER PRIMARY KEY AUTOINCREMENT,
                    Username TEXT,
                    FullName TEXT,
                    Contact TEXT,
                    BloodGroup TEXT,
                    Center TEXT,
                    BookingDate TEXT,
                    BookingTime TEXT,
                    CreatedAt TEXT
                 )''')

    cur.execute("SELECT COUNT(*) FROM Stock")
    if cur.fetchone()[0] == 0:
        for bg in ['A+','A-','B+','B-','O+','O-','AB+','AB-']:
            cur.execute("INSERT INTO Stock (BloodGroup, Units) VALUES (?, ?)", (bg, 0))

    db.commit()
    db.close()

init_db()

# ------------------ USER / AUTH ------------------
def signup(username, password, full_name, age, gender, contact):
    if not all([username.strip(), password.strip(), full_name.strip(), contact.strip()]):
        st.error("⚠️ Please fill in all required fields.")
        return False

    db = connect_db()
    cur = db.cursor()
    try:
        cur.execute("""INSERT INTO Users (Username, Password, FullName, Age, Gender, Contact, Role)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (username.strip(), hash_password(password), full_name.strip(), age, gender, contact.strip(), "User"))
        db.commit()
        st.success("✅ Signup successful! You can now log in.")
        return True
    except sqlite3.IntegrityError:
        st.error("❌ Username already exists.")
        return False
    finally:
        db.close()

def login(username, password):
    db = connect_db()
    cur = db.cursor()
    cur.execute("SELECT Username, Role FROM Users WHERE Username=? AND Password=?", (username, hash_password(password)))
    user = cur.fetchone()
    db.close()
    return user

def get_user_profile(username):
    db = connect_db()
    cur = db.cursor()
    cur.execute("SELECT FullName, Age, Gender, Contact FROM Users WHERE Username=?", (username,))
    profile = cur.fetchone()
    db.close()
    return profile

def update_profile(username, full_name, age, gender, contact):
    db = connect_db()
    cur = db.cursor()
    cur.execute("""UPDATE Users SET FullName=?, Age=?, Gender=?, Contact=? WHERE Username=?""",
                (full_name, age, gender, contact, username))
    db.commit()
    db.close()
    st.success("✅ Profile updated.")

# ------------------ BOOKINGS ------------------
def create_booking(username, full_name, contact, blood_group, center, booking_date, booking_time):
    db = connect_db()
    cur = db.cursor()
    created_at = datetime.now().isoformat()
    cur.execute("""INSERT INTO Bookings
                   (Username, FullName, Contact, BloodGroup, Center, BookingDate, BookingTime, CreatedAt)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (username, full_name, contact, blood_group, center, booking_date, booking_time, created_at))
    db.commit()
    db.close()
    st.success(f"✅ Booking saved for {booking_date} at {booking_time} — {center}")

def get_user_bookings(username):
    db = connect_db()
    cur = db.cursor()
    cur.execute("""SELECT BookingID, FullName, Contact, BloodGroup, Center, BookingDate, BookingTime, CreatedAt
                   FROM Bookings WHERE Username=? ORDER BY BookingDate, BookingTime""", (username,))
    rows = cur.fetchall()
    db.close()
    return rows

def cancel_booking(booking_id, username):
    db = connect_db()
    cur = db.cursor()
    cur.execute("DELETE FROM Bookings WHERE BookingID=? AND Username=?", (booking_id, username))
    db.commit()
    db.close()
    st.success("🗑️ Booking cancelled.")

# ------------------ DONORS & STOCK ------------------
def view_all_donors():
    db = connect_db()
    cur = db.cursor()
    cur.execute("SELECT DonorID, Name, Age, Gender, BloodGroup, Contact FROM Donors")
    rows = cur.fetchall()
    db.close()
    return rows

def add_donor(name, age, gender, blood_group, contact):
    db = connect_db()
    cur = db.cursor()
    cur.execute("""INSERT INTO Donors (Name, Age, Gender, BloodGroup, Contact)
                   VALUES (?, ?, ?, ?, ?)""", (name, age, gender, blood_group, contact))
    db.commit()
    db.close()
    st.success("✅ Donor added.")

def view_stock():
    db = connect_db()
    cur = db.cursor()
    cur.execute("SELECT BloodGroup, Units FROM Stock ORDER BY BloodGroup")
    rows = cur.fetchall()
    db.close()
    return rows

# ------------------ UI HELPERS ------------------
def display_main_logo():
    try:
        st.image(str(LOGO_PATH), width=300)
    except:
        st.error("⚠️ Logo not found.")

def display_small_logo():
    try:
        b64 = base64.b64encode(open(LOGO_PATH, "rb").read()).decode()
        st.markdown(
            f"<img src='data:image/jpeg;base64,{b64}' style='position:fixed; top:80px; right:10px; width:56px; z-index:100;'>",
            unsafe_allow_html=True
        )
    except:
        pass

def render_centered_table(df: pd.DataFrame):
    st.markdown(
        df.to_html(index=False, classes="table table-striped table-bordered"),
        unsafe_allow_html=True
    )
    st.markdown("""
        <style>
        .dataframe {margin-left:auto; margin-right:auto; width:85%;}
        table, th, td {text-align:center;}
        </style>
    """, unsafe_allow_html=True)

# ------------------ SIDEBAR ------------------
def sidebar_menu():
    st.sidebar.markdown(f"**Logged in as:** {st.session_state.username}")
    st.sidebar.markdown("---")

    st.sidebar.markdown("### Donation Guidance")
    guidance_action = st.sidebar.selectbox(
        "", ["Select", "Upcoming Events & Drives", "Donation Tips & Guidelines", "Blood Donation FAQ", "Book Donation Slot"],
        key="guidance_dropdown"
    )

    st.sidebar.markdown("### Analytics & Visuals")
    analytics_action = st.sidebar.selectbox(
        "", ["Select", "Blood Stock Trend", "My Blood Type Status", "Who's Needed Now?"],
        key="analytics_dropdown"
    )

    st.sidebar.markdown("---")
    if st.sidebar.button("View Profile"):
        st.session_state.show_profile = True

    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.show_profile = False
        st.rerun()

    for action in (guidance_action, analytics_action):
        if action != "Select":
            st.session_state.selected_action = action

# ------------------ MAIN UI ------------------
def main():
    if not st.session_state.logged_in:
        unauth_menu()
        return

    display_small_logo()
    sidebar_menu()

    if st.session_state.show_profile:
        show_profile()
        return

    action = st.session_state.selected_action or "Home"

    if action == "Home":
        st.header("Welcome to LifeLink")
        st.write("Use the sidebar to navigate donation guidance, analytics, bookings and your profile.")
        # Removed Current Blood Stock Snapshot

    elif action == "Upcoming Events & Drives":
        st.header("Upcoming Donation Drives & Events")
        st.info("📅 Next Drive: Nov 1, City Hall, 10:00 AM - 4:00 PM")
        st.info("📅 Blood Camp: Nov 15, Community Center, 9:00 AM - 2:00 PM")

    elif action == "Donation Tips & Guidelines":
        st.header("Donation Tips & Guidelines")
        st.markdown("""
        **BEFORE DONATION:**  
        Stay hydrated by drinking plenty of water or non-caffeinated beverages the day before and the day of donation  
        Eat a balanced meal with iron-rich foods like spinach, beans, red meat, or fortified cereals, and avoid fatty foods  
        Avoid alcohol and smoking for at least 24 hours before donating  
        Skip heavy exercise the day of donation  
        Get a good night's sleep (6 to 8 hours) before donation  
        Bring a valid government-issued ID  
        Check your eligibility, including age, weight, health, medications, and recent travel  
        Wear comfortable clothing with sleeves that can be rolled up easily  
        Know your medical history and be ready to answer questions honestly  
        Relax your mind and body to reduce anxiety  

        **DURING DONATION:**  
        Stay calm and take deep breaths if nervous  
        Follow all instructions given by staff  
        Keep your arm relaxed to make vein access easier  
        Talk, listen to music, or bring a distraction to pass the time  
        Report any feelings of dizziness, nausea, or discomfort immediately  
        Keep your hand and arm still while the needle is inserted  
        Focus on positive thoughts and remember your donation is saving lives  

        **AFTER DONATION:**  
        Rest for a few minutes in the recovery area until you feel steady  
        Rehydrate with water or juice  
        Eat a light snack such as cookies, crackers, or fruit to boost energy  
        Avoid heavy lifting, exercise, or strenuous activity for a few hours  
        Keep the bandage on for 4 to 6 hours to prevent bleeding or bruising  
        Watch for any side effects like bruising, dizziness, or fatigue and report if severe  
        Include iron-rich foods in your meals to replenish your iron levels  
        Track your next eligible donation date  
        Let the staff know if you develop a fever or infection after donating  

        **EXTRA TIPS:**  
        Bring a friend for support and company  
        Be honest about medications or supplements you take  
        Keep your stress levels low as mental prep helps with recovery  
        Wear sunscreen if donating outdoors at a blood drive  
        Avoid caffeine immediately before donating as it may dehydrate you  
        Smile and reward yourself, as donating blood is a big act of kindness
        """)

    elif action == "Blood Donation FAQ":
        st.header("Blood Donation FAQ")
        question = st.text_area("Ask any question (simulated).")
        if st.button("Submit Question"):
            st.success("✅ Question submitted.")

    elif action == "Book Donation Slot":
        st.header("Book a Donation Slot")
        profile = get_user_profile(st.session_state.username) or ("", "", "", "")
        pre_fullname = profile[0]
        pre_contact = profile[3]

        with st.form("booking_form"):
            full_name = st.text_input("Full Name", value=pre_fullname)
            contact = st.text_input("Contact", value=pre_contact)
            blood_group = st.selectbox("Blood Group", ['A+','A-','B+','B-','O+','O-','AB+','AB-'])
            center = st.selectbox("Donation Center",
                                  ["City Hall", "Community Center", "Central Hospital", "Mobile Unit"])
            booking_date = st.date_input("Booking Date", min_value=date.today())
            booking_time = st.selectbox("Time Slot",
                                        ["09:00 AM","10:00 AM","11:00 AM","12:00 PM","01:00 PM","02:00 PM","03:00 PM"])
            submitted = st.form_submit_button("Book Slot")

        if submitted:
            if not all([full_name.strip(), contact.strip()]):
                st.error("⚠️ Please provide full name and contact.")
            else:
                create_booking(st.session_state.username, full_name.strip(), contact.strip(),
                               blood_group, center, booking_date.isoformat(), booking_time)

        st.markdown("---")
        st.markdown("### My Upcoming Bookings")
        bookings = get_user_bookings(st.session_state.username)
        if bookings:
            df = pd.DataFrame(bookings, columns=["BookingID","FullName","Contact","BloodGroup","Center","BookingDate","BookingTime","CreatedAt"])
            df["BookingDate"] = pd.to_datetime(df["BookingDate"]).dt.date
            render_centered_table(df[["BookingID","FullName","Contact","BloodGroup","Center","BookingDate","BookingTime"]])

            st.write("### Cancel a booking")
            bid = st.number_input("Enter BookingID to cancel", min_value=0, step=1)
            if st.button("Cancel Booking"):
                if bid > 0:
                    cancel_booking(int(bid), st.session_state.username)
                    st.rerun()
                else:
                    st.error("Enter a valid BookingID.")
        else:
            st.info("No bookings yet.")

    elif action == "Blood Stock Trend":
        st.header("Blood Stock Trend")
        stock = view_stock()
        df_stock = pd.DataFrame(stock, columns=["BloodGroup","Units"])
        df_stock["Units"] = pd.to_numeric(df_stock["Units"])
        chart = alt.Chart(df_stock).mark_bar().encode(
            x=alt.X("BloodGroup:N", sort=None),
            y=alt.Y("Units:Q"),
            tooltip=["BloodGroup","Units"]
        )
        st.altair_chart(chart, use_container_width=True)

    elif action == "My Blood Type Status":
        st.header("My Blood Type Status")
        user_blood_type = st.text_input("Enter your blood type")
        if st.button("Check Status"):
            stock = dict(view_stock())
            units = stock.get(user_blood_type, None)
            if units is None:
                st.error("❌ Unknown blood group.")
            elif units < 5:
                st.warning(f"⚠️ Low stock: {units} units")
            else:
                st.success(f"Available units: {units}")

    elif action == "Who's Needed Now?":
        st.header("Urgent Blood Needs")
        stock = dict(view_stock())
        low = {bg:u for bg,u in stock.items() if u < 5}
        if low:
            st.warning("Low stock groups:")
            for bg,u in low.items():
                st.write(f"- {bg}: {u} units")
        else:
            st.success("All blood types sufficiently stocked.")

    else:
        st.info("Choose an action from the sidebar.")

# ------------------ UNAUTH UI ------------------
def unauth_menu():
    st.sidebar.title("LifeLink")
    choice = st.sidebar.selectbox("Menu", ["Home", "Signup", "Login"])

    if choice == "Home":
        # Display logo without center alignment
        display_main_logo()

    elif choice == "Signup":
        st.header("Create an Account")
        with st.form("signup_form"):
            uname = st.text_input("Username")
            pw = st.text_input("Password", type='password')
            full_name = st.text_input("Full Name")
            age = st.number_input("Age", 0, 120, value=18)
            gender = st.selectbox("Gender", ["Male", "Female", "Other"])
            contact = st.text_input("Contact")
            submitted = st.form_submit_button("Signup")
        if submitted:
            if signup(uname, pw, full_name, age, gender, contact):
                st.info("Go to Login to continue.")

    elif choice == "Login":
        st.header("Login")
        uname = st.text_input("Username", key="login_uname")
        pw = st.text_input("Password", type='password', key="login_pw")
        if st.button("Login"):
            user = login(uname, pw)
            if user:
                st.session_state.logged_in = True
                st.session_state.username = user[0]
                st.session_state.role = user[1]
                st.session_state.show_profile = False
                st.rerun()
            else:
                st.error("❌ Invalid username or password.")

# ------------------ PROFILE ------------------
def show_profile():
    profile = get_user_profile(st.session_state.username)
    if not profile:
        st.error("Profile not found.")
        return

    full_name, age, gender, contact = profile
    st.header("My Profile")
    with st.form("profile_form"):
        fn = st.text_input("Full Name", value=full_name)
        ag = st.number_input("Age", min_value=0, max_value=120, value=age or 18)
        gen = st.selectbox("Gender", ["Male","Female","Other"],
                           index=["Male","Female","Other"].index(gender))
        cont = st.text_input("Contact", value=contact)
        save = st.form_submit_button("Save Changes")
    if save:
        update_profile(st.session_state.username, fn, ag, gen, cont)

    st.markdown("---")
    if st.button("Back to Dashboard"):
        st.session_state.show_profile = False
        st.rerun()

# ------------------ START ------------------
if __name__ == "__main__":
    main()

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

import streamlit as st
import mysql.connector
import bcrypt
from datetime import datetime

# Database Connection 
conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="root",
    database="khoj_db1"
)
cursor = conn.cursor()

# Create Users Table
cursor.execute('''CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100),
    email VARCHAR(100) UNIQUE,
    password VARCHAR(255),
    phone VARCHAR(15),
    role ENUM('USER', 'VOLUNTEER')
)''')

# Create Lost & Found Table
cursor.execute('''CREATE TABLE IF NOT EXISTS lost_found (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_name VARCHAR(100),
    train_number VARCHAR(50),
    compartment_number VARCHAR(50),
    seat_number VARCHAR(50),
    item_description TEXT,
    phone_number VARCHAR(15),
    status ENUM('Pending', 'Received', 'Assigned to Volunteer', 'Searching', 'Found', 'Out for Delivery', 'Resolved') DEFAULT 'Pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)''')

# Create Medical Assistance Table
cursor.execute('''CREATE TABLE IF NOT EXISTS medical_assistance (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_name VARCHAR(100),
    symptoms TEXT,
    station_left VARCHAR(100),
    arriving_station VARCHAR(100),
    assistance_type VARCHAR(50),
    status ENUM('Pending', 'Received', 'Assigned to Volunteer', 'In Progress', 'Out for Assistance', 'Resolved') DEFAULT 'Pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)''')

# Create Women's Safety Table with Travel Companion Features
cursor.execute('''CREATE TABLE IF NOT EXISTS womens_safety (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_name VARCHAR(100),
    boarding_station VARCHAR(100),
    destination_station VARCHAR(100),
    time_of_boarding VARCHAR(50),
    phone_number VARCHAR(15),
    travel_date DATE,
    looking_for_companion BOOLEAN DEFAULT FALSE,
    status ENUM('Pending', 'Received', 'Assigned to Volunteer', 'In Progress', 'Assistance Dispatched', 'Resolved') DEFAULT 'Pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)''')

# Create Travel Companions Table
cursor.execute('''CREATE TABLE IF NOT EXISTS travel_companions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    request_id INT,
    companion_name VARCHAR(100),
    companion_phone VARCHAR(15),
    status ENUM('Pending', 'Accepted', 'Rejected') DEFAULT 'Pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (request_id) REFERENCES womens_safety(id)
)''')

# Create Volunteer Assignments Table
cursor.execute('''CREATE TABLE IF NOT EXISTS volunteer_assignments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    complaint_type VARCHAR(50),
    complaint_id INT,
    volunteer_name VARCHAR(100),
    volunteer_phone VARCHAR(15),
    volunteer_email VARCHAR(100),
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)''')

conn.commit()

# User Management Functions
def register_user(name, email, password, phone, role):
    hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
    try:
        cursor.execute("INSERT INTO users (name, email, password, phone, role) VALUES (%s, %s, %s, %s, %s)", 
                      (name, email, hashed_pw, phone, role))
        conn.commit()
        return True
    except mysql.connector.IntegrityError:
        return False

def authenticate_user(email, password):
    cursor.execute("SELECT id, name, password, role, phone FROM users WHERE email=%s", (email,))
    user = cursor.fetchone()
    if user and bcrypt.checkpw(password.encode(), user[2].encode()):
        return user[0], user[1], user[3], user[4], email
    return None, None, None, None, None

# Complaint Management Functions
def add_lost_found(user_name, train_number, compartment_number, seat_number, item_description, phone_number):
    cursor.execute("""
        INSERT INTO lost_found 
        (user_name, train_number, compartment_number, seat_number, item_description, phone_number) 
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (user_name, train_number, compartment_number, seat_number, item_description, phone_number))
    conn.commit()

def add_medical_assistance(user_name, symptoms, station_left, arriving_station, assistance_type):
    cursor.execute("""
        INSERT INTO medical_assistance 
        (user_name, symptoms, station_left, arriving_station, assistance_type) 
        VALUES (%s, %s, %s, %s, %s)
    """, (user_name, symptoms, station_left, arriving_station, assistance_type))
    conn.commit()

def add_womens_safety(user_name, boarding_station, destination_station, time_of_boarding, phone_number, travel_date, looking_for_companion):
    cursor.execute("""
        INSERT INTO womens_safety 
        (user_name, boarding_station, destination_station, time_of_boarding, phone_number, travel_date, looking_for_companion) 
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (user_name, boarding_station, destination_station, time_of_boarding, phone_number, travel_date, looking_for_companion))
    conn.commit()

# Travel Companion Functions
def find_travel_companions(boarding_station, destination_station, travel_date):
    cursor.execute("""
        SELECT id, user_name, time_of_boarding, phone_number 
        FROM womens_safety 
        WHERE boarding_station = %s 
        AND destination_station = %s 
        AND travel_date = %s 
        AND looking_for_companion = TRUE 
        AND status != 'Resolved'
    """, (boarding_station, destination_station, travel_date))
    return cursor.fetchall()

def request_companion(request_id, companion_name, companion_phone):
    cursor.execute("""
        INSERT INTO travel_companions 
        (request_id, companion_name, companion_phone) 
        VALUES (%s, %s, %s)
    """, (request_id, companion_name, companion_phone))
    conn.commit()

def get_companion_requests(user_name):
    cursor.execute("""
        SELECT tc.id, ws.user_name AS requester_name, tc.companion_name, 
               ws.boarding_station, ws.destination_station, ws.travel_date, 
               ws.time_of_boarding, tc.status, tc.created_at,
               ws.phone_number AS requester_phone,
               tc.companion_phone
        FROM travel_companions tc
        JOIN womens_safety ws ON tc.request_id = ws.id
        WHERE ws.user_name = %s OR tc.companion_name = %s
        ORDER BY tc.created_at DESC
    """, (user_name, user_name))
    return cursor.fetchall()

# Volunteer Functions
def assign_volunteer(complaint_type, complaint_id, volunteer_name, volunteer_phone, volunteer_email):
    cursor.execute("""
        INSERT INTO volunteer_assignments 
        (complaint_type, complaint_id, volunteer_name, volunteer_phone, volunteer_email)
        VALUES (%s, %s, %s, %s, %s)
    """, (complaint_type, complaint_id, volunteer_name, volunteer_phone, volunteer_email))
    conn.commit()

def get_lost_found_complaints(volunteer_email=None):
    if volunteer_email:
        cursor.execute("""
            SELECT lf.id, lf.user_name, lf.train_number, lf.compartment_number, 
                   lf.seat_number, lf.item_description, lf.phone_number, lf.status, 
                   lf.created_at
            FROM lost_found lf
            LEFT JOIN volunteer_assignments va 
            ON va.complaint_type='lost_found' AND va.complaint_id=lf.id
            WHERE (lf.status = 'Pending' OR lf.status = 'Received')
            OR (va.volunteer_email = %s)
            ORDER BY lf.status, lf.created_at DESC
        """, (volunteer_email,))
    else:
        cursor.execute("""
            SELECT lf.id, lf.user_name, lf.train_number, lf.compartment_number, 
                   lf.seat_number, lf.item_description, lf.phone_number, lf.status, 
                   lf.created_at
            FROM lost_found lf
            WHERE status IN ('Pending', 'Received')
            ORDER BY lf.status, lf.created_at DESC
        """)
    return cursor.fetchall()

def get_medical_assistance_complaints(volunteer_email=None):
    if volunteer_email:
        cursor.execute("""
            SELECT ma.id, ma.user_name, ma.symptoms, ma.station_left, 
                   ma.arriving_station, ma.assistance_type, ma.status, ma.created_at
            FROM medical_assistance ma
            LEFT JOIN volunteer_assignments va 
            ON va.complaint_type='medical_assistance' AND va.complaint_id=ma.id
            WHERE (ma.status = 'Pending' OR ma.status = 'Received')
            OR (va.volunteer_email = %s)
            ORDER BY ma.status, ma.created_at DESC
        """, (volunteer_email,))
    else:
        cursor.execute("""
            SELECT ma.id, ma.user_name, ma.symptoms, ma.station_left, 
                   ma.arriving_station, ma.assistance_type, ma.status, ma.created_at
            FROM medical_assistance ma
            WHERE status IN ('Pending', 'Received')
            ORDER BY ma.status, ma.created_at DESC
        """)
    return cursor.fetchall()

def get_womens_safety_complaints(volunteer_email=None):
    if volunteer_email:
        cursor.execute("""
            SELECT ws.id, ws.user_name, ws.boarding_station, ws.destination_station, 
                   ws.time_of_boarding, ws.phone_number, ws.status, ws.created_at
            FROM womens_safety ws
            LEFT JOIN volunteer_assignments va 
            ON va.complaint_type='womens_safety' AND va.complaint_id=ws.id
            WHERE (ws.status = 'Pending' OR ws.status = 'Received')
            OR (va.volunteer_email = %s)
            ORDER BY ws.status, ws.created_at DESC
        """, (volunteer_email,))
    else:
        cursor.execute("""
            SELECT ws.id, ws.user_name, ws.boarding_station, ws.destination_station, 
                   ws.time_of_boarding, ws.phone_number, ws.status, ws.created_at
            FROM womens_safety ws
            WHERE status IN ('Pending', 'Received')
            ORDER BY ws.status, ws.created_at DESC
        """)
    return cursor.fetchall()

def update_complaint_status(table_name, complaint_id, new_status, volunteer_details=None):
    cursor.execute(f"UPDATE {table_name} SET status=%s WHERE id=%s", (new_status, complaint_id))
    if new_status == 'Assigned to Volunteer' and volunteer_details:
        assign_volunteer(
            table_name,
            complaint_id,
            volunteer_details['name'],
            volunteer_details['phone'],
            volunteer_details['email']
        )
    conn.commit()

def get_user_complaints(user_name):
    complaints = {
        'lost_found': [],
        'medical_assistance': [],
        'womens_safety': []
    }
    
    # Lost & Found
    cursor.execute("""
        SELECT lf.id, lf.train_number, lf.compartment_number, lf.seat_number, 
               lf.item_description, lf.phone_number, lf.status, lf.created_at,
               va.volunteer_name, va.volunteer_phone, va.volunteer_email, va.assigned_at
        FROM lost_found lf
        LEFT JOIN volunteer_assignments va 
        ON va.complaint_type='lost_found' AND va.complaint_id=lf.id
        WHERE lf.user_name = %s
        ORDER BY lf.created_at DESC
    """, (user_name,))
    complaints['lost_found'] = cursor.fetchall()
    
    # Medical Assistance
    cursor.execute("""
        SELECT ma.id, ma.symptoms, ma.station_left, ma.arriving_station, 
               ma.assistance_type, ma.status, ma.created_at,
               va.volunteer_name, va.volunteer_phone, va.volunteer_email, va.assigned_at
        FROM medical_assistance ma
        LEFT JOIN volunteer_assignments va 
        ON va.complaint_type='medical_assistance' AND va.complaint_id=ma.id
        WHERE ma.user_name = %s
        ORDER BY ma.created_at DESC
    """, (user_name,))
    complaints['medical_assistance'] = cursor.fetchall()
    
    # Women's Safety
    cursor.execute("""
        SELECT ws.id, ws.boarding_station, ws.destination_station, 
               ws.time_of_boarding, ws.phone_number, ws.status, ws.created_at,
               va.volunteer_name, va.volunteer_phone, va.volunteer_email, va.assigned_at
        FROM womens_safety ws
        LEFT JOIN volunteer_assignments va 
        ON va.complaint_type='womens_safety' AND va.complaint_id=ws.id
        WHERE ws.user_name = %s
        ORDER BY ws.created_at DESC
    """, (user_name,))
    complaints['womens_safety'] = cursor.fetchall()
    
    return complaints

def analyze_lost_found_patterns():
    """Analyze patterns in lost & found items"""
    cursor.execute("""
        SELECT train_number, compartment_number, item_description, 
               created_at, status, HOUR(created_at) as hour_of_day,
               DAYOFWEEK(created_at) as day_of_week
        FROM lost_found
    """)
    df = pd.DataFrame(cursor.fetchall(), columns=['train_number', 'compartment_number', 
                                                  'item_description', 'created_at', 'status',
                                                  'hour_of_day', 'day_of_week'])
    return df

def analyze_medical_emergencies():
    """Analyze medical emergency patterns"""
    cursor.execute("""
        SELECT station_left, arriving_station, symptoms, 
               assistance_type, created_at, status,
               HOUR(created_at) as hour_of_day,
               DAYOFWEEK(created_at) as day_of_week
        FROM medical_assistance
    """)
    df = pd.DataFrame(cursor.fetchall(), columns=['station_left', 'arriving_station', 
                                                  'symptoms', 'assistance_type', 'created_at',
                                                  'status', 'hour_of_day', 'day_of_week'])
    return df

def analyze_safety_hotspots():
    """Analyze women's safety request patterns"""
    cursor.execute("""
        SELECT boarding_station, destination_station, 
               time_of_boarding, status, created_at,
               HOUR(created_at) as hour_of_day,
               DAYOFWEEK(created_at) as day_of_week
        FROM womens_safety
    """)
    df = pd.DataFrame(cursor.fetchall(), columns=['boarding_station', 'destination_station',
                                                  'time_of_boarding', 'status', 'created_at',
                                                  'hour_of_day', 'day_of_week'])
    return df

def generate_insights():
    """Generate comprehensive insights from all data"""
    lost_found_df = analyze_lost_found_patterns()
    medical_df = analyze_medical_emergencies()
    safety_df = analyze_safety_hotspots()
    
    insights = {
        'lost_found': {
            'total_cases': len(lost_found_df),
            'resolution_rate': (lost_found_df['status'] == 'Resolved').mean() * 100,
            'peak_hours': lost_found_df['hour_of_day'].mode().iloc[0],
            'common_items': lost_found_df['item_description'].value_counts().head(5).to_dict()
        },
        'medical': {
            'total_cases': len(medical_df),
            'emergency_rate': (medical_df['assistance_type'] == 'Ambulance Assistance').mean() * 100,
            'common_symptoms': medical_df['symptoms'].value_counts().head(5).to_dict(),
            'high_risk_stations': medical_df['station_left'].value_counts().head(3).to_dict()
        },
        'safety': {
            'total_requests': len(safety_df),
            'risky_hours': safety_df['hour_of_day'].mode().iloc[0],
            'common_routes': pd.DataFrame({
                'route': safety_df['boarding_station'] + ' to ' + safety_df['destination_station']
            }).value_counts().head(5).to_dict()
        }
    }
    
    return insights

def create_visualizations():
    """Create interactive visualizations for the dashboard"""
    lost_found_df = analyze_lost_found_patterns()
    medical_df = analyze_medical_emergencies()
    safety_df = analyze_safety_hotspots()
    
    # Lost & Found Heatmap
    lost_found_heatmap = px.density_heatmap(
        lost_found_df,
        x='hour_of_day',
        y='day_of_week',
        title='Lost & Found Reports Distribution'
    )
    
    # Medical Emergency Timeline
    medical_timeline = px.line(
        medical_df.groupby('created_at').size().reset_index(),
        x='created_at',
        y=0,
        title='Medical Emergencies Over Time'
    )
    
    # Safety Requests Map (if coordinates available)
    safety_stations = pd.concat([
        safety_df['boarding_station'],
        safety_df['destination_station']
    ]).value_counts().reset_index()
    safety_stations.columns = ['station', 'count']
    
    return {
        'lost_found_heatmap': lost_found_heatmap,
        'medical_timeline': medical_timeline,
        'station_data': safety_stations
    }

def predict_resource_needs(days_ahead=7):
    """Predict resource requirements for upcoming days"""
    cursor.execute("""
        SELECT DATE(created_at) as date, 
               COUNT(*) as total_cases,
               SUM(CASE WHEN status = 'Resolved' THEN 1 ELSE 0 END) as resolved_cases
        FROM (
            SELECT created_at, status FROM lost_found
            UNION ALL
            SELECT created_at, status FROM medical_assistance
            UNION ALL
            SELECT created_at, status FROM womens_safety
        ) combined
        GROUP BY DATE(created_at)
    """)

    historical_data = pd.DataFrame(cursor.fetchall(), 
                                   columns=['date', 'total_cases', 'resolved_cases'])

    # Check if historical_data is empty
    if historical_data.empty:
        avg_cases = 0  # Default to zero if no historical data
        avg_resolution_rate = 0  # Default to zero
    else:
        avg_cases = historical_data['total_cases'].rolling(window=7).mean().iloc[-1]
        avg_resolution_rate = (historical_data['resolved_cases'] / historical_data['total_cases']).mean()

        # Handle NaN cases
        if pd.isna(avg_cases):
            avg_cases = historical_data['total_cases'].mean()  # Use mean instead
        if pd.isna(avg_resolution_rate):
            avg_resolution_rate = 0  # Default to zero

    predictions = pd.DataFrame({
        'date': [datetime.now().date() + timedelta(days=i) for i in range(days_ahead)],
        'predicted_cases': [round(avg_cases)] * days_ahead,
        'predicted_resolutions': [round(avg_cases * avg_resolution_rate)] * days_ahead
    })

    return predictions


def add_analytics_dashboard():
    """Add analytics dashboard to Streamlit interface"""
    st.title("KHOJ Analytics Dashboard")
    
    insights = generate_insights()
    visualizations = create_visualizations()
    predictions = predict_resource_needs()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Lost & Found Cases", insights['lost_found']['total_cases'])
        st.metric("Resolution Rate", f"{insights['lost_found']['resolution_rate']:.1f}%")
    
    with col2:
        st.metric("Medical Emergencies", insights['medical']['total_cases'])
        st.metric("Emergency Rate", f"{insights['medical']['emergency_rate']:.1f}%")
    
    with col3:
        st.metric("Safety Requests", insights['safety']['total_requests'])
        st.metric("Peak Hour", f"{insights['safety']['risky_hours']:02d}:00")
    
    st.plotly_chart(visualizations['lost_found_heatmap'])
    st.plotly_chart(visualizations['medical_timeline'])
    
    st.subheader("Resource Needs Forecast")
    st.dataframe(predictions)


# Streamlit UI
st.title("KHOJ - Find & Help")

# Initialize session state
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_id = None
    st.session_state.user_name = ""
    st.session_state.user_phone = ""
    st.session_state.user_email = ""
    st.session_state.role = ""

# Menu options based on user role
menu = st.sidebar.selectbox(
    "Menu", 
    ["Login", "Register"] if not st.session_state.logged_in 
    else ["Home", "Track Applications", "Analytics Dashboard", "Logout"]
)


# Register Page
if menu == "Register":
    st.subheader("Register")
    name = st.text_input("Full Name")
    email = st.text_input("Email")
    phone = st.text_input("Phone Number")
    password = st.text_input("Password", type="password")
    role = st.selectbox("Register as", ["USER", "VOLUNTEER"])
    if st.button("Register"):
        if register_user(name, email, password, phone, role):
            st.success("Registered successfully! You can now login.")
        else:
            st.error("Email already exists. Try logging in.")

# Login Page
elif menu == "Login":
    st.subheader("Login")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        # Login Page (continued)
        user_id, user_name, role, phone, email = authenticate_user(email, password)
        if role:
            st.session_state.logged_in = True
            st.session_state.user_id = user_id
            st.session_state.user_name = user_name
            st.session_state.user_phone = phone
            st.session_state.user_email = email
            st.session_state.role = role
            st.success(f"Welcome, {user_name} ({role})!")
            st.rerun()

        else:
            st.error("Invalid email or password")

# Track Applications Page
elif menu == "Track Applications":
    st.subheader("Track Your Applications")
    
    complaints = get_user_complaints(st.session_state.user_name)
    
    tab1, tab2, tab3, tab4 = st.tabs(["Lost & Found", "Medical Assistance", "Women's Safety", "Travel Companions"])
    
    with tab1:
        st.write("### Lost & Found Complaints")
        if complaints['lost_found']:
            for complaint in complaints['lost_found']:
                id, train_number, compartment_number, seat_number, \
                item_description, phone_number, status, created_at, \
                volunteer_name, volunteer_phone, volunteer_email, assigned_at = complaint
                
                with st.expander(f"Complaint Status: {status} - {created_at}"):
                    st.write(f"**Train Number:** {train_number}")
                    st.write(f"**Compartment:** {compartment_number}")
                    st.write(f"**Seat:** {seat_number}")
                    st.write(f"**Item:** {item_description}")
                    st.write(f"**Current Status:** {status}")
                    
                    if status == "Assigned to Volunteer" and volunteer_name:
                        st.write("---")
                        st.write("### Volunteer Details")
                        st.write(f"**Name:** {volunteer_name}")
                        st.write(f"**Contact:** {volunteer_phone}")
                        st.write(f"**Email:** {volunteer_email}")
                        st.write(f"**Assigned:** {assigned_at}")
        else:
            st.info("No Lost & Found complaints found.")
    
    with tab2:
        st.write("### Medical Assistance Requests")
        if complaints['medical_assistance']:
            for complaint in complaints['medical_assistance']:
                id, symptoms, station_left, arriving_station, \
                assistance_type, status, created_at, \
                volunteer_name, volunteer_phone, volunteer_email, assigned_at = complaint
                
                with st.expander(f"Request Status: {status} - {created_at}"):
                    st.write(f"**Symptoms:** {symptoms}")
                    st.write(f"**Last Station:** {station_left}")
                    st.write(f"**Arriving Station:** {arriving_station}")
                    st.write(f"**Assistance Type:** {assistance_type}")
                    st.write(f"**Current Status:** {status}")
                    
                    if status == "Assigned to Volunteer" and volunteer_name:
                        st.write("---")
                        st.write("### Volunteer Details")
                        st.write(f"**Name:** {volunteer_name}")
                        st.write(f"**Contact:** {volunteer_phone}")
                        st.write(f"**Email:** {volunteer_email}")
                        st.write(f"**Assigned:** {assigned_at}")
        else:
            st.info("No Medical Assistance requests found.")
    
    with tab3:
        st.write("### Women's Safety Requests")
        if complaints['womens_safety']:
            for complaint in complaints['womens_safety']:
                id, boarding_station, destination_station, \
                time_of_boarding, phone_number, status, created_at, \
                volunteer_name, volunteer_phone, volunteer_email, assigned_at = complaint
                
                with st.expander(f"Request Status: {status} - {created_at}"):
                    st.write(f"**Boarding Station:** {boarding_station}")
                    st.write(f"**Destination Station:** {destination_station}")
                    st.write(f"**Time of Boarding:** {time_of_boarding}")
                    st.write(f"**Current Status:** {status}")
                    
                    if status == "Assigned to Volunteer" and volunteer_name:
                        st.write("---")
                        st.write("### Volunteer Details")
                        st.write(f"**Name:** {volunteer_name}")
                        st.write(f"**Contact:** {volunteer_phone}")
                        st.write(f"**Email:** {volunteer_email}")
                        st.write(f"**Assigned:** {assigned_at}")
        else:
            st.info("No Women's Safety requests found.")
    
    with tab4:
        st.write("### Travel Companion Requests")
        companion_requests = get_companion_requests(st.session_state.user_name)
    
    if companion_requests:
        sent_requests = []
        received_requests = []
        
        for request in companion_requests:
            (id, requester, companion, boarding, destination, 
             date, time, status, created_at, requester_phone, companion_phone) = request
            
            # Separate requests into sent and received
            if requester == st.session_state.user_name:
                sent_requests.append(request)
            else:
                received_requests.append(request)
        
        # Display Received Requests
        st.write("#### Received Requests")
        if received_requests:
            for request in received_requests:
                (id, requester, companion, boarding, destination, 
                 date, time, status, created_at, requester_phone, companion_phone) = request
                
                with st.expander(f"Request from {requester} - {status}"):
                    st.write(f"**Route:** {boarding} to {destination}")
                    st.write(f"**Date:** {date}")
                    st.write(f"**Time:** {time}")
                    
                    if status == 'Pending':
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("Accept", key=f"accept_{id}"):
                                cursor.execute("""
                                    UPDATE travel_companions 
                                    SET status='Accepted', companion_phone=%s 
                                    WHERE id=%s
                                """, (st.session_state.user_phone, id))
                                conn.commit()
                                st.success("Request accepted!")
                                st.experimental_rerun()
                        with col2:
                            if st.button("Reject", key=f"reject_{id}"):
                                cursor.execute("""
                                    UPDATE travel_companions 
                                    SET status='Rejected' 
                                    WHERE id=%s
                                """, (id,))
                                conn.commit()
                                st.success("Request rejected!")
                                st.experimental_rerun()
                    elif status == 'Accepted':
                        st.write("#### Contact Details")
                        st.write(f"**Requester Phone:** {requester_phone}")
        else:
            st.info("No received requests.")
        
        # Display Sent Requests
        st.write("#### Sent Requests")
        if sent_requests:
            for request in sent_requests:
                (id, requester, companion, boarding, destination, 
                 date, time, status, created_at, requester_phone, companion_phone) = request
                
                with st.expander(f"Request to {companion} - {status}"):
                    st.write(f"**Route:** {boarding} to {destination}")
                    st.write(f"**Date:** {date}")
                    st.write(f"**Time:** {time}")
                    st.write(f"**Status:** {status}")
                    
                    if status == 'Accepted':
                        st.write("#### Contact Details")
                        st.write(f"**Companion Phone:** {companion_phone}")
        else:
            st.info("No sent requests.")
    else:
        st.info("No travel companion requests found.")

elif menu == "Analytics Dashboard":
    add_analytics_dashboard()

# Home Page
elif st.session_state.logged_in and menu == "Home":
    if st.session_state.role == "USER":
        st.subheader(f"Welcome {st.session_state.user_name} ({st.session_state.role})")
        
        tab1, tab2, tab3 = st.tabs(["Lost & Found", "Medical Assistance", "Women's Safety Travel"])
        
        with tab1:
            st.write("### Lost & Found")
            with st.form("lost_found_form"):
                train_number = st.text_input("Train Number or Name")
                compartment_number = st.text_input("Compartment Number")
                seat_number = st.text_input("Seat Number")
                item_description = st.text_area("Item Description")
                phone_number = st.text_input("Your Phone Number", value=st.session_state.user_phone)
                submitted = st.form_submit_button("Submit")
                if submitted and all([train_number, compartment_number, seat_number, item_description, phone_number]):
                    add_lost_found(st.session_state.user_name, train_number, compartment_number, 
                                 seat_number, item_description, phone_number)
                    st.success("Lost & Found request submitted successfully!")

        with tab2:
            st.write("### Medical Assistance")
            with st.form("medical_assistance_form"):
                symptoms = st.text_area("Symptoms")
                station_left = st.text_input("Last Station Left")
                arriving_station = st.text_input("Arriving Station")
                assistance_type = st.radio("Do you need assistance?", ["Ambulance Assistance", "Volunteer Assistance"])
                submitted = st.form_submit_button("Submit")
                if submitted and all([symptoms, station_left, arriving_station, assistance_type]):
                    add_medical_assistance(st.session_state.user_name, symptoms, station_left, 
                                        arriving_station, assistance_type)
                    st.success("Medical assistance request submitted successfully!")

        with tab3:
            st.write("### Women's Safety Travel")
            with st.form("womens_safety_form"):
                boarding_station = st.text_input("Boarding Station")
                destination_station = st.text_input("Destination Station")
                travel_date = st.date_input("Date of Travel")
                time_of_boarding = st.time_input("Time of Boarding")
                phone_number = st.text_input("Your Phone Number", value=st.session_state.user_phone)
                looking_for_companion = st.checkbox("Looking for Travel Companion?")
                
                submitted = st.form_submit_button("Submit")
                if submitted and all([boarding_station, destination_station, time_of_boarding, phone_number]):
                    add_womens_safety(
                        st.session_state.user_name, 
                        boarding_station, 
                        destination_station, 
                        time_of_boarding.strftime("%H:%M"), 
                        phone_number,
                        travel_date,
                        looking_for_companion
                    )
                    st.success("Women's Safety Travel details submitted successfully!")

            if looking_for_companion:
                st.write("### Available Travel Companions")
                companions = find_travel_companions(boarding_station, destination_station, travel_date)
                
                if companions:
                    st.write("Found potential travel companions on your route:")
                    for companion in companions:
                        id, name, time, phone = companion
                        if name != st.session_state.user_name:  # Don't show own request
                            with st.expander(f"Traveller: {name}"):
                                st.write(f"**Boarding Time:** {time}")
                                st.write(f"**Contact:** {phone}")
                                if st.button("Request to Travel Together", key=f"companion_{id}"):
                                    request_companion(id, st.session_state.user_name, st.session_state.user_phone)
                                    st.success("Request sent successfully!")
                else:
                    st.info("No travel companions found for your route and date. Your request has been posted for others to find.")

    # Volunteer Dashboard
    elif st.session_state.role == "VOLUNTEER":
        st.subheader("Volunteer Dashboard")
        
        tab1, tab2, tab3 = st.tabs(["Lost & Found", "Medical Assistance", "Women's Safety"])
        
        with tab1:
            st.write("### Lost & Found Complaints")
            complaints = get_lost_found_complaints(st.session_state.user_email)
            for complaint in complaints:
                id, user_name, train_number, compartment_number, seat_number, \
                item_description, phone_number, status, created_at = complaint
                
                with st.expander(f"Lost & Found - {status} (by {user_name}) - {created_at}"):
                    st.write(f"**Train Number:** {train_number}")
                    st.write(f"**Compartment:** {compartment_number}")
                    st.write(f"**Seat:** {seat_number}")
                    st.write(f"**Item:** {item_description}")
                    st.write(f"**Phone:** {phone_number}")
                    st.write(f"**Current Status:** {status}")
                    
                    if status != "Resolved":
                        status_options = [
                            'Pending',
                            'Received',
                            'Assigned to Volunteer',
                            'Searching',
                            'Found',
                            'Out for Delivery',
                            'Resolved'
                        ]
                        new_status = st.selectbox(
                            "Update Status",
                            status_options,
                            key=f"lf_status_{id}"
                        )
                        
                        if new_status == "Assigned to Volunteer":
                            volunteer_details = {
                                'name': st.session_state.user_name,
                                'phone': st.session_state.user_phone,
                                'email': st.session_state.user_email
                            }
                        else:
                            volunteer_details = None
                            
                        if st.button(f"Update Status", key=f"lf_{id}"):
                            update_complaint_status("lost_found", id, new_status, volunteer_details)
                            st.success("Status updated successfully!")
                            st.experimental_rerun()
        
        with tab2:
            st.write("### Medical Assistance Requests")
            complaints = get_medical_assistance_complaints(st.session_state.user_email)
            for complaint in complaints:
                id, user_name, symptoms, station_left, arriving_station, \
                assistance_type, status, created_at = complaint
                
                with st.expander(f"Medical Assistance - {status} (by {user_name}) - {created_at}"):
                    st.write(f"**Symptoms:** {symptoms}")
                    st.write(f"**Last Station:** {station_left}")
                    st.write(f"**Arriving Station:** {arriving_station}")
                    st.write(f"**Assistance Type:** {assistance_type}")
                    st.write(f"**Current Status:** {status}")
                    
                    if status != "Resolved":
                        status_options = [
                            'Pending',
                            'Received',
                            'Assigned to Volunteer',
                            'In Progress',
                            'Out for Assistance',
                            'Resolved'
                        ]
                        new_status = st.selectbox(
                            "Update Status",
                            status_options,
                            key=f"ma_status_{id}"
                        )
                        
                        if new_status == "Assigned to Volunteer":
                            volunteer_details = {
                                'name': st.session_state.user_name,
                                'phone': st.session_state.user_phone,
                                'email': st.session_state.user_email
                            }
                        else:
                            volunteer_details = None
                            
                        if st.button(f"Update Status", key=f"ma_{id}"):
                            update_complaint_status("medical_assistance", id, new_status, volunteer_details)
                            st.success("Status updated successfully!")
                            st.experimental_rerun()
        
        with tab3:
            st.write("### Women's Safety Travel Requests")
            complaints = get_womens_safety_complaints(st.session_state.user_email)
            for complaint in complaints:
                id, user_name, boarding_station, destination_station, \
                time_of_boarding, phone_number, status, created_at = complaint
                
                with st.expander(f"Women's Safety - {status} (by {user_name}) - {created_at}"):
                    st.write(f"**Boarding Station:** {boarding_station}")
                    st.write(f"**Destination Station:** {destination_station}")
                    st.write(f"**Time of Boarding:** {time_of_boarding}")
                    st.write(f"**Phone Number:** {phone_number}")
                    st.write(f"**Current Status:** {status}")
                    
                    if status != "Resolved":
                        status_options = [
                            'Pending',
                            'Received',
                            'Group Created',
                            'RPF Informed',
                            'Resolved'
                        ]
                        new_status = st.selectbox(
                            "Update Status",
                            status_options,
                            key=f"ws_status_{id}"
                        )
                        
                        if new_status == "Assigned to Volunteer":
                            volunteer_details = {
                                'name': st.session_state.user_name,
                                'phone': st.session_state.user_phone,
                                'email': st.session_state.user_email
                            }
                        else:
                            volunteer_details = None
                            
                        if st.button(f"Update Status", key=f"ws_{id}"):
                            update_complaint_status("womens_safety", id, new_status, volunteer_details)
                            st.success("Status updated successfully!")
                            st.experimental_rerun()

# Logout
elif menu == "Logout":
    st.session_state.logged_in = False
    st.session_state.user_id = None
    st.session_state.user_name = ""
    st.session_state.user_phone = ""
    st.session_state.user_email = ""
    st.session_state.role = ""
    st.success("Logged out successfully.")
    st.rerun()

import streamlit as st
import pandas as pd
import bcrypt
import plotly.express as px
from datetime import datetime
import uuid
import os

# --- Constants
EMPLOYEE_FILE = "employee_list.csv"
REVIEW_FILE = "reviews.csv"

CATEGORIES = [
    "Behavior",
    "Communication",
    "Technical Knowledge",
    "Team Contribution",
    "Initiative",
    "Leadership (Optional)"
]

# --- Load secrets for admin credentials
ADMIN_USERNAME = st.secrets["admin"]["username"]
HASHED_PASSWORD = st.secrets["admin"]["password"]

# --- Initialize data file if not exists
if not os.path.exists(REVIEW_FILE):
    pd.DataFrame(columns=["id", "timestamp", "employee_id", "employee_name"] + CATEGORIES + ["comment"]).to_csv(REVIEW_FILE, index=False)

# --- Utility Functions
@st.cache_data
def load_employees():
    df = pd.read_csv(EMPLOYEE_FILE)
    df['display'] = df['Employee ID'].astype(str) + " - " + df['Employee Name']
    return df[['Employee ID', 'Employee Name', 'display']]

def load_reviews():
    if not os.path.exists(REVIEW_FILE):
        return pd.DataFrame()
    return pd.read_csv(REVIEW_FILE)

def save_review(entry):
    df = load_reviews()
    df = pd.concat([df, pd.DataFrame([entry])], ignore_index=True)
    df.to_csv(REVIEW_FILE, index=False)

# --- Search employees by name or ID
def employee_search_selectbox(employees_df, label="Select Employee"):
    query = st.text_input("🔍 Search by Name or ID")
    if query:
        filtered = employees_df[
            employees_df['Employee Name'].str.lower().str.contains(query.lower()) |
            employees_df['Employee ID'].astype(str).str.contains(query)
        ]
        if filtered.empty:
            st.warning("No employees found for this search.")
            return None
    else:
        filtered = employees_df

    selected = st.selectbox(label, filtered['display']) if not filtered.empty else None
    if selected:
        emp = filtered[filtered['display'] == selected].iloc[0]
        return emp
    return None

# --- Main UI functions
def show_survey_form():
    st.title("📝 Workmates Peer Review Form")
    st.markdown("Please provide your anonymous feedback about your colleague. Your responses will be confidential.")

    employees = load_employees()

    emp = employee_search_selectbox(employees)
    if emp is None:
        st.stop()

    st.markdown(f"### Reviewing: **{emp['Employee Name']}** (ID: {emp['Employee ID']})")

    ratings = {}
    for cat in CATEGORIES:
        ratings[cat] = st.slider(f"{cat}", 1, 5, 3)

    comment = st.text_area("💬 Optional Comment")

    if st.button("✅ Submit Review"):
        review = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "employee_id": emp['Employee ID'],
            "employee_name": emp['Employee Name'],
            "comment": comment.strip(),
            **ratings
        }
        save_review(review)

        # --- Animated Card UI
        st.markdown(f"""
            <div style="
                background: linear-gradient(135deg, #89f7fe, #66a6ff);
                padding: 30px;
                border-radius: 20px;
                box-shadow: 0 8px 20px rgba(0, 0, 0, 0.2);
                animation: pop-in 0.6s ease-out;
                text-align: center;
                font-size: 1.3rem;
                font-weight: bold;
                color: #ffffff;
                margin-top: 20px;
            ">
                🎉 Thank you! Your anonymous review for <span style="color: #ffd700;">{emp['Employee Name']}</span> has been submitted.
            </div>

            <style>
            @keyframes pop-in {{
            0% {{ transform: scale(0.5); opacity: 0; }}
            100% {{ transform: scale(1); opacity: 1; }}
            }}
            </style>
        """, unsafe_allow_html=True)

        st.balloons()

        # Prevent rerun so the card stays visible
        st.stop()

def show_admin_portal():
    st.title("🔐 Admin Portal")

    username = st.text_input("Username")
    pw_col1, pw_col2 = st.columns([4, 1])
    with pw_col1:
        password = st.text_input("Password", type="password", key="password_input")
    with pw_col2:
        show_password = st.checkbox("👁", key="show_pw", help="Show Password")

    if show_password:
        st.text_input("Password (visible)", type="default", value=password, key="visible_pw")

    if st.button("Login"):
        if username == ADMIN_USERNAME and bcrypt.checkpw(password.encode(), HASHED_PASSWORD.encode()):
            st.success("🔓 Logged in as Admin")

            df = load_reviews()
            if df.empty:
                st.warning("No reviews submitted yet.")
                return

            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df["timestamp_formatted"] = df["timestamp"].dt.strftime("%Y-%m-%d %H:%M")

            # Filters
            with st.expander("📌 Filters", expanded=False):
                selected_employee = st.multiselect("Filter by Employee", df["employee_name"].unique())
                if selected_employee:
                    df = df[df["employee_name"].isin(selected_employee)]

            # Data Table
            st.subheader("📋 Peer Reviews")
            st.dataframe(
                df[["timestamp_formatted", "employee_name"] + CATEGORIES + ["comment"]]
                .rename(columns={"timestamp_formatted": "Timestamp", "employee_name": "Employee"})
            )

            # Summary
            st.subheader("📈 Summary Statistics")
            stats = df.groupby("employee_name")[CATEGORIES].mean().reset_index()
            stats["Total Score"] = stats[CATEGORIES].mean(axis=1)
            stats = stats.sort_values("Total Score", ascending=False)
            stats = stats.rename(columns={"employee_name": "Employee"})

            numeric_cols = stats.select_dtypes(include="number").columns
            st.dataframe(stats.style.format({col: "{:.2f}" for col in numeric_cols}), use_container_width=True)

            # Charts
            fig = px.bar(stats, x="Employee", y="Total Score", title="🏆 Average Total Score by Employee",
                         labels={"Employee": "Employee", "Total Score": "Average Score"})
            st.plotly_chart(fig, use_container_width=True)

            # Export Options
            st.subheader("⬇️ Export Data")
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button("📥 Download CSV", csv, "peer_reviews.csv", "text/csv")

        else:
            st.error("❌ Invalid credentials")

# --- Navigation
st.sidebar.title("🧭 Navigation")
option = st.sidebar.radio("Go to", ("Peer Review Form", "Admin Portal"))

if option == "Peer Review Form":
    show_survey_form()
else:
    show_admin_portal()

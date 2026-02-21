import streamlit as st
import pandas as pd
import sqlite3
import os

# Page Config
st.set_page_config(page_title="ResumeIQ Dashboard", layout="wide")

st.title("ResumeIQ Admin Dashboard")

# Database Connection
DB_PATH = os.path.join("instance", "resumeiq.db")

@st.cache_data
def load_data():
    if not os.path.exists(DB_PATH):
        st.error(f"Database not found at {DB_PATH}")
        return None, None
        
    conn = sqlite3.connect(DB_PATH)
    
    try:
        users = pd.read_sql("SELECT * FROM user", conn)
        resumes = pd.read_sql("SELECT * FROM resume", conn)
    except Exception as e:
        st.error(f"Error reading database: {e}")
        return None, None
    finally:
        conn.close()
        
    return users, resumes

users_df, resumes_df = load_data()

if users_df is not None and resumes_df is not None:
    # Metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Users", len(users_df))
    col2.metric("Total Resumes Analyzed", len(resumes_df))
    if not resumes_df.empty:
        avg_score = resumes_df['score'].mean()
        col3.metric("Average Resume Score", f"{avg_score:.1f}")
    else:
        col3.metric("Average Resume Score", "N/A")

    st.markdown("---")

    # Main Content
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Recent Resumes")
        if not resumes_df.empty:
            # Join with user to get username
            merged_df = pd.merge(resumes_df, users_df, left_on='user_id', right_on='id', suffixes=('_resume', '_user'))
            display_df = merged_df[['filename', 'username', 'role_applied', 'score', 'created_at_resume']].sort_values('created_at_resume', ascending=False)
            st.dataframe(display_df, use_container_width=True)
            
            st.subheader("Score Distribution")
            st.bar_chart(resumes_df.set_index('filename')['score'])
        else:
            st.info("No resumes found.")

    with col_right:
        st.subheader("Registered Users")
        if not users_df.empty:
            st.dataframe(users_df[['id', 'username', 'role', 'created_at']].sort_values('created_at', ascending=False), use_container_width=True)
        else:
            st.info("No users found.")
else:
    st.warning("Could not load data.")

if st.button("Refresh Data"):
    st.cache_data.clear()
    st.rerun()

import os
from dotenv import load_dotenv
import streamlit as st
import pandas as pd
import psycopg2
import logging

load_dotenv(dotenv_path=r'C:\Users\DELL\Desktop\internship\.env') 

# Configure logging to display messages in the terminal
logging.basicConfig(
    level=logging.INFO,  # Log level
    format="%(asctime)s - %(levelname)s - %(message)s"  # Log message format
)
# Fetch the database password from the environment variables
DB_PASSWORD = os.getenv('POSGRESS_PASSWORD')
if not DB_PASSWORD:
    st.error("Database password is missing in environment variables.")
    logging.error("Database password is missing in environment variables.")
    exit(1)  # Stop the application if password is missing

# Database connection parameters
DB_PARAMS = {
    'host': 'localhost',
    'database': 'vedthaware',
    'user': 'postgres',
    'password': DB_PASSWORD  # Using the environment variable for password
}

# Connect to the PostgreSQL database
def get_connection():
    logging.info("Attempting to connect to the database...")
    try:
        conn = psycopg2.connect(**DB_PARAMS)
        logging.info("Database connection successful.")
        return conn
    except Exception as e:
        logging.error(f"Failed to connect to the database: {e}")
        st.error(f"Failed to connect to the database: {e}")
        return None

# Function to create the student table
def create_student_table():
    logging.info("Creating student table if it doesn't exist.")
    query = """
    CREATE TABLE IF NOT EXISTS student (
        id INT PRIMARY KEY,
        student_name VARCHAR(100) NOT NULL,
        age INT NOT NULL,
        class VARCHAR(50),
        email VARCHAR(100) UNIQUE,
        phone_number VARCHAR(15) UNIQUE,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    conn = get_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute(query)
            conn.commit()
            cursor.close()
            logging.info("Student table created or already exists.")
        except Exception as e:
            logging.error(f"Error creating student table: {e}")
        finally:
            conn.close()

# Reset the sequence after deletion
def reset_id_sequence():
    conn = get_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT setval('student_id_seq', (SELECT MAX(id) FROM student));")
            conn.commit()
            cursor.close()
            logging.info("Sequence reset to the maximum id value.")
        except Exception as e:
            logging.error(f"Error resetting ID sequence: {e}")
        finally:
            conn.close()

# Insert or update student data
def upsert_student_data(df):
    logging.info(f"Uploading {len(df)} student records to the database.")
    conn = get_connection()
    if conn:
        cursor = conn.cursor()
        try:
            for _, row in df.iterrows():
                query = """
                INSERT INTO student (student_name, age, class, email, phone_number)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (email) DO UPDATE
                SET student_name = EXCLUDED.student_name,
                    age = EXCLUDED.age,
                    class = EXCLUDED.class,
                    phone_number = EXCLUDED.phone_number,
                    updated_at = CURRENT_TIMESTAMP;
                """
                cursor.execute(query, (row['student_name'], row['age'], row['class'], row['email'], row['phone_number']))

            conn.commit()
            logging.info("Student data uploaded successfully.")
        except Exception as e:
            logging.error(f"Error uploading student data: {e}")
            st.error(f"Error uploading student data: {e}")
        finally:
            cursor.close()
            conn.close()

# Update a student record
def update_student_record(id, name, age, class_name, email, phone_number):
    logging.info(f"Updating student record with ID: {id}")
    conn = get_connection()
    if conn:
        query = """
        UPDATE student
        SET student_name = %s, age = %s, class = %s, email = %s, phone_number = %s, updated_at = CURRENT_TIMESTAMP
        WHERE id = %s;
        """
        cursor = conn.cursor()
        try:
            cursor.execute(query, (name, age, class_name, email, phone_number, id))
            conn.commit()
            logging.info(f"Student record with ID {id} updated successfully.")
            st.success("Record updated successfully!")
        except Exception as e:
            logging.error(f"Error updating student record: {e}")
            st.error(f"Error updating student record: {e}")
        finally:
            cursor.close()
            conn.close()

# Delete a student record
def delete_student_record(id):
    logging.info(f"Deleting student record with ID: {id}")
    conn = get_connection()
    if conn:
        query = "DELETE FROM student WHERE id = %s;"
        cursor = conn.cursor()
        try:
            cursor.execute(query, (id,))
            conn.commit()
            logging.info(f"Student record with ID {id} deleted successfully.")
            st.success("Record deleted successfully!")
            # Reset the sequence after deletion
            reset_id_sequence()
        except Exception as e:
            logging.error(f"Error deleting student record: {e}")
            st.error(f"Error deleting student record: {e}")
        finally:
            cursor.close()
            conn.close()

# Fetch data from the database and display it in ascending order by id
def fetch_student_data():
    logging.info("Fetching student data from the database.")
    conn = get_connection()
    if conn:
        query = "SELECT * FROM student ORDER BY id ASC;"  # Added ORDER BY to sort records by id in ascending order
        df = pd.read_sql(query, conn)
        conn.close()
        logging.info(f"Fetched {len(df)} records from the database.")
        return df
    else:
        return pd.DataFrame()

# Streamlit UI
def main():
    # Custom title and header
    st.title("Student Data Management System 📚")
    st.markdown("""<style>.big-font { font-size:40px !important; color: #1E90FF; font-weight: bold; }</style>""", unsafe_allow_html=True)
    st.markdown('<p class="big-font">Welcome to the Student Management Portal!</p>', unsafe_allow_html=True)

    # Sidebar
    st.sidebar.title("Navigation")
    option = st.sidebar.radio("Choose an option", ("Upload Data", "View Data"))

    # Create the student table if not exists
    create_student_table()

    if option == "Upload Data":
        st.subheader("Upload Student Data 🗂️")
        uploaded_file = st.file_uploader("Upload an Excel file", type=["xlsx"])
        if uploaded_file is not None:
            # Read the Excel file
            df = pd.read_excel(uploaded_file)
            st.write("Preview of Uploaded Data:")
            st.dataframe(df)

            # Validate column names
            required_columns = {'student_name', 'age', 'class', 'email', 'phone_number'}
            if set(df.columns) >= required_columns:
                if st.button("Upload to Database"):
                    with st.spinner("Uploading data to the database... Please wait..."):
                        upsert_student_data(df)
                    st.success("Data uploaded successfully! 🎉")
            else:
                st.error(f"Excel file must contain the following columns: {', '.join(required_columns)}")

    elif option == "View Data":
        st.subheader("View Student Data 📋")
        student_data = fetch_student_data()
        if student_data.empty:
            st.write("No data available in the database. 📭")
            logging.info("No data found in the database.")
        else:
            st.write("Student Data from Database:")
            # Display the full table
            st.dataframe(student_data)

            # Add checkboxes for selection
            student_data['select'] = student_data.apply(lambda row: st.checkbox(f"Select {row['student_name']}", key=f"select_{row['id']}"), axis=1)
            selected_rows = student_data[student_data['select'] == True]

            if not selected_rows.empty:
                action = st.radio("Choose Action", ("Update", "Delete"))

                if action == "Update":
                    st.subheader("Update Selected Records 📝")
                    for idx, row in selected_rows.iterrows():
                        with st.form(key=f"update_form_{row['id']}"):
                            name = st.text_input("Name", row['student_name'])
                            age = st.number_input("Age", min_value=1, max_value=100, value=row['age'])
                            class_name = st.text_input("Class", row['class'])
                            email = st.text_input("Email", row['email'])
                            phone = st.text_input("Phone Number", row['phone_number'])
                            submit_button = st.form_submit_button(label="Update Record")

                            if submit_button:
                                update_student_record(row['id'], name, age, class_name, email, phone)

                elif action == "Delete":
                    st.subheader("Delete Selected Records 🗑️")
                    for idx, row in selected_rows.iterrows():
                        if st.button(f"Delete {row['student_name']}", key=f"delete_{row['id']}"):
                            delete_student_record(row['id'])

if __name__ == "__main__":
    main()

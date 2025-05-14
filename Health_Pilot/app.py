import joblib
import pandas as pd
import os
import sqlite3
import base64
from flask import Flask, render_template, request, url_for, jsonify
import joblib
import string
import re
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

app = Flask(__name__)

# Admin credentials
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'admin_password'


# Load symptoms from CSV (excluding the 'Disease' column)
csv_file_path = 'modified_csv_file.csv'  # Replace with the path to your CSV file
df = pd.read_csv(csv_file_path)
dataset_symptoms = set(df.drop(columns=['Disease']).values.flatten())


# Display all registered doctors in the admin panel
@app.route('/admin', methods=['GET', 'POST'])
def admin_panel():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if authenticate_admin(username, password):
            # Admin authentication successful
            doctors = load_doctors_from_database()
            return render_template('admin_panel.html', doctors=doctors)
        else:
            # Admin authentication failed
            return render_template('admin_login.html', message='Invalid credentials')

    return render_template('admin_login.html')
# Admin authentication function
def authenticate_admin(username, password):
    return username == ADMIN_USERNAME and password == ADMIN_PASSWORD

import joblib

# Load the trained model from the saved file
model_file_path = 'best_model_no_2.joblib'

loaded_model = joblib.load(model_file_path)


# Download NLTK resources (uncomment the next two lines if not downloaded)
# nltk.download('punkt')
# nltk.download('stopwords')

stop_words = set(stopwords.words('english'))

# Function to clean and tokenize text
def clean_and_tokenize(text):
    text = text.translate(str.maketrans('', '', string.punctuation))  # Remove Punctuation
    text = re.sub(r'\d+', '', text)  # Remove Digits
    text = text.replace('\n', ' ')  # Remove New Lines
    text = text.strip()  # Remove Leading White Space
    text = re.sub(' +', ' ', text)  # Remove multiple white spaces

    # Tokenize text using NLTK
    tokens = [word for word in word_tokenize(text) if word.lower() not in stop_words]
    return ' '.join(tokens)

@app.route('/')
def index():
    return render_template('index.html')


# Function to predict disease from user input
def predict_disease(user_input):
    try:
        # Clean and tokenize user input
        cleaned_input = clean_and_tokenize(user_input)

        # Check if any token in the cleaned input is a symptom from the dataset
        input_tokens = set(cleaned_input.split())
        dataset_symptom_tokens = set(' '.join(dataset_symptoms).split())

        if not any(token in dataset_symptom_tokens for token in input_tokens):
            return 'Invalid symptoms', None  # Return both the message and None for prediction

        # Make prediction using the trained model
        prediction = loaded_model.predict([cleaned_input])[0]
        return prediction, None
    except Exception as e:
        return str(e), None

# Route to recommend doctors based on user input symptoms
@app.route('/recommend', methods=['POST'])
def recommend():
    if request.method == 'POST':
        user_input = request.form['symptoms']

        # Use the predict_disease function to get the predicted disease and message
        predicted_disease, invalid_symptom_message = predict_disease(user_input)

        if invalid_symptom_message:
            return render_template('result.html', invalid_symptom=True, invalid_symptom_message=invalid_symptom_message)

        # Retrieve doctors from the SQL database based on the predicted disease
        with sqlite3.connect('your_database.db') as connection:
            cursor = connection.cursor()
            # When retrieving doctors for recommendation, include a condition to exclude unapproved doctors
            # cursor.execute("SELECT * FROM doctors WHERE disease_specialist = ? AND approval_status = 1",
            #                (predicted_disease,))
            # matched_doctors = [dict(zip([column[0] for column in cursor.description], row)) for row in
            #                    cursor.fetchall()]

            cursor.execute("SELECT * FROM doctors WHERE disease_specialist = ?", (predicted_disease,))
            matched_doctors = [dict(zip([column[0] for column in cursor.description], row)) for row in
                               cursor.fetchall()]

        if matched_doctors:
            return render_template('result.html', predicted_disease=predicted_disease, matched_doctors=matched_doctors)
        else:
            return render_template('result.html', predicted_disease=predicted_disease, no_matching_doctors=True)





# Load doctors from the SQL database
def load_doctors_from_database():
    with sqlite3.connect('your_database.db') as connection:
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM doctors")
        doctors = [dict(zip([column[0] for column in cursor.description], row)) for row in cursor.fetchall()]
    return doctors



@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Handle doctor registration form data
        full_name = request.form.get('full_name')
        degree = request.form.get('degree')
        specialization = request.form.get('specialization')
        disease_specialist = request.form.get('disease_specialist')
        email = request.form.get('email')
        contact = request.form.get('contact')
        address = request.form.get('address')
        country = request.form.get('country')
        gender = request.form.get('gender')

        # Handle image upload
        file = request.files['file-input']
        if file:
            # Convert image to base64
            image_data = base64.b64encode(file.read()).decode('utf-8')

            # Save the doctor details to the SQL database
            database_file = 'your_database.db'

            # Create the database file if it doesn't exist
            if not os.path.exists(database_file):
                with sqlite3.connect(database_file) as connection:
                    cursor = connection.cursor()
                    cursor.execute(
                        """
                        CREATE TABLE doctors (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            full_name TEXT,
                            degree TEXT,
                            specialization TEXT,
                            disease_specialist TEXT,
                            email TEXT,
                            contact TEXT,
                            address TEXT,
                            country TEXT,
                            gender TEXT,
                            image_data TEXT
                        );
                        """
                        # """
                        # CREATE TABLE doctors (
                        #     id INTEGER PRIMARY KEY AUTOINCREMENT,
                        #     full_name TEXT,
                        #     degree TEXT,
                        #     specialization TEXT,
                        #     disease_specialist TEXT,
                        #     email TEXT,
                        #     contact TEXT,
                        #     address TEXT,
                        #     country TEXT,
                        #     gender TEXT,
                        #     image_data TEXT,
                        #     approval_status INTEGER DEFAULT 0  -- 0: Not approved, 1: Approved
                        # );
                        # """
                    )
                    connection.commit()

            with sqlite3.connect(database_file) as connection:
                cursor = connection.cursor()
                cursor.execute(
                    """
                    INSERT INTO doctors (full_name, degree, specialization, disease_specialist, email, contact, address, country, gender, image_data, approval_status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                    """,
                    (full_name, degree, specialization, disease_specialist, email, contact, address, country, gender,
                     image_data)
                )
                # cursor.execute(
                #     """
                #     INSERT INTO doctors (full_name, degree, specialization, disease_specialist, email, contact, address, country, gender, image_data)
                #     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                #     """,
                #     (full_name, degree, specialization, disease_specialist, email, contact, address, country, gender,
                #      image_data)
                # )
                connection.commit()

        return render_template('index.html', message='Registration successful!')

    return render_template('register.html')

# Update doctor data

@app.route('/admin/update/<int:doctor_id>', methods=['GET', 'POST'], endpoint='update_doctor')
def update_doctor(doctor_id):
    # Load doctors from the SQL database
    doctors = load_doctors_from_database()

    # Find the doctor to update in the 'doctors' list
    doctor_to_update = next((doctor for doctor in doctors if doctor['id'] == doctor_id), None)

    if request.method == 'POST':
        # Implement doctor data update logic here
        # Update the 'doctors' list and the SQL database

        # Extract updated information from the form
        updated_full_name = request.form.get('full_name')
        updated_degree = request.form.get('degree')
        updated_specialization = request.form.get('specialization')
        updated_disease_specialist = request.form.get('disease_specialist')
        updated_email = request.form.get('email')
        updated_contact = request.form.get('contact')
        updated_address = request.form.get('address')
        updated_country = request.form.get('country')
        updated_gender = request.form.get('gender')

        # Handle image upload
        file = request.files['file-input']
        if file:
            # Convert image to base64
            updated_image_data = base64.b64encode(file.read()).decode('utf-8')
            doctor_to_update['image_data'] = updated_image_data

        # Update the doctor information
        doctor_to_update['full_name'] = updated_full_name
        doctor_to_update['degree'] = updated_degree
        doctor_to_update['specialization'] = updated_specialization
        doctor_to_update['disease_specialist'] = updated_disease_specialist
        doctor_to_update['email'] = updated_email
        doctor_to_update['contact'] = updated_contact
        doctor_to_update['address'] = updated_address
        doctor_to_update['country'] = updated_country
        doctor_to_update['gender'] = updated_gender

        # Update the SQL database
        with sqlite3.connect('your_database.db') as connection:
            cursor = connection.cursor()
            cursor.execute("""
                UPDATE doctors
                SET full_name=?, degree=?, specialization=?, disease_specialist=?, email=?, contact=?, address=?, country=?, gender=?, image_data=?
                WHERE id=?
            """, (updated_full_name, updated_degree, updated_specialization, updated_disease_specialist, updated_email, updated_contact, updated_address, updated_country, updated_gender, updated_image_data, doctor_id))
            connection.commit()

        return redirect(url_for('admin_panel', message='Update successful!'))

    # Render the update doctor form using the register.html template
    return render_template('register.html', doctor=doctor_to_update)



@app.route('/admin/delete/<int:doctor_id>', methods=['GET', 'POST'], endpoint='admin_delete')
def delete_doctor(doctor_id):
    # Ensure that only the admin can access this route
    username = request.form.get('username')
    password = request.form.get('password')

    if not authenticate_admin(username, password):
        return render_template('admin_login.html', message='Authentication required to delete doctor data.')

    # Load doctors from the SQL database
    doctors = load_doctors_from_database()

    # Find the doctor to delete in the 'doctors' list
    doctor_to_delete = next((doctor for doctor in doctors if doctor['id'] == doctor_id), None)

    if doctor_to_delete:
        # Delete the doctor from the 'doctors' list
        doctors.remove(doctor_to_delete)

        # Delete the doctor from the SQL database
        with sqlite3.connect('your_database.db') as connection:
            cursor = connection.cursor()
            cursor.execute("DELETE FROM doctors WHERE id=?", (doctor_id,))
            connection.commit()

        return redirect(url_for('admin_panel', message='Delete successful!'))

    # If the doctor is not found, render the admin panel without changes
    return redirect(url_for('admin_panel', message='Doctor not found for deletion.'))

if __name__ == '__main__':
    app.run(debug=True)

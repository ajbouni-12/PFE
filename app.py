import os
from flask import Flask, render_template, request, redirect, url_for, send_file, session
import firebase_admin
from firebase_admin import credentials, db as firebase_db
import qrcode
import io
import base64

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

app = Flask(__name__)

# Initialize Firebase Admin SDK with your credentials

cred = credentials.Certificate(r"final-b47ee-firebase-adminsdk-54ud5-222e8dfc0e.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://final-b47ee-default-rtdb.firebaseio.com/'
})

# Set secret key for session management
app.secret_key = b'xlT2P3v3GI3PXTbFqqICxztVNH0zf29NXyakCrjF'

# Route to display the home page
@app.route('/')
def home():
    return render_template('home.html')

# Route to display the form
@app.route('/form.html')
def form():
    return render_template('form.html')

# Route to display the page home1
@app.route('/home1')
def home1():
    return render_template('home1.html')

# Route to display the login page
@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/service')
def service():
    # Code to handle requests to the '/service' endpoint
    return render_template('service.html')

@app.route('/signup')
def signup():
    return render_template('signup.html')

@app.route('/paiement')
def paiement():
    return render_template('paiement.html')
# Route to handle form submission for signup
@app.route('/form_signup', methods=['POST'])
def form_signup():
    name = request.form['fullname']
    email = request.form['email']
    phone = request.form['phone']
    password = request.form['password']
    confirm_password = request.form['confirm-password']
    
    # Check if passwords match
    if password != confirm_password:
        return "Passwords do not match!"
    
    # Insert user data into Firebase Realtime Database
    user_data = {
        'fullname': name,
        'email': email,
        'phone': phone,
        'password': password
    }
    firebase_db.reference('users').child(name).set(user_data)

    # Redirect user to a confirmation page
    return redirect(url_for('home1'))

@app.route('/form_login', methods=['POST'])
def form_login():
    email = request.form['email']
    password = request.form['password']

    users_ref = firebase_db.reference('users')
    query = users_ref.order_by_child('email').equal_to(email).limit_to_first(1).get()

    if query:
        user_data = list(query.values())[0]
        if 'password' in user_data and user_data['password'] == password:
            session['email'] = email
            session.permanent = True  # Make the session permanent
            return redirect(url_for('home1'))  # Redirection vers home1  
    # Authentication failed, show error message
    return render_template('login.html', error="Invalid email or password.")

@app.route('/submit-form', methods=['POST'])
def submit_form():
    # Get form data from POST request
    name = request.form['name']
    prenom = request.form['prenom']
    email = request.form['email']
    telephone = request.form['telephone']
    cin = request.form['cin']
    date_debut = request.form['date_debut']
    date_fin = request.form['date_fin']
    reference_maison = request.form['reference_maison']

    # Insert form data into Firebase Realtime Database
    form_data = {
        'name': name,
        'prenom': prenom,
        'email': email,
        'telephone': telephone,
        'cin': cin,
        'date_debut': date_debut,
        'date_fin': date_fin,
        'reference_maison': reference_maison
    }
    firebase_db.reference('Reservation').child(cin).set(form_data)

    # Generate QR code from the saved data
    text = f"CIN: {cin} Reference maison: {reference_maison}"
    qr = qrcode.make(text)
  
    img_byte_array = io.BytesIO()
    qr.save(img_byte_array, format='PNG')
    qrcode_content = img_byte_array.getvalue()

    # Insert QR code into Firebase Realtime Database
    qr_data = {
        'date_debut': date_debut,
        'date_fin': date_fin,
        'reference_maison': reference_maison,
        'qrcode': text  # Store Base64 encoded data
    }
    firebase_db.reference('QRcode').child(text).set(qr_data)

    # Define destination path for download
    home_directory = os.path.expanduser("~")
    destination_path = os.path.join(home_directory, 'contracts')
    os.makedirs(destination_path, exist_ok=True)

    # Create a new PDF file in the destination folder
    pdf_filename = f'contract_{name}_{prenom}.pdf'
    pdf_path = os.path.join(destination_path, pdf_filename)
    c = canvas.Canvas(pdf_path, pagesize=letter)
    
    # Set font and size for the title (bold)
    c.setFont("Helvetica-Bold", 16)  # Setting font to bold and size to 16
    title_text = "Contrat de location"
    title_width = c.stringWidth(title_text, "Helvetica-Bold", 16)
    c.drawString((letter[0] - title_width) / 2, 750, title_text)  # Centering the title

    # Set font and size for the rest of the content (regular)
    c.setFont("Helvetica", 12)  # Setting font to regular and size to 12

    # Drawing the rest of the content as paragraphs
    rental_info =[  f"Le présent contrat de location est établi entre {name} {prenom} et Agence Tunisia location ATL ,",
                    f"pour la maison sous le numéro {reference_maison}",
                    f"et pour une période allant du {date_debut} au {date_fin}."]
    y_position = 710  # Initial y position for the content
    for line in rental_info:
        c.drawString(100, y_position, line)
        y_position -= 20 

    # Draw the signature image
    signature_image_path = "signature.png"  # Replace with the path to your signature image
    c.drawInlineImage(signature_image_path, 250, 600, 50, 50)  # Adjust x, y, width, height as needed

    # Save the PDF
    c.save()

    # Save the QR code image
    qr_filename = f'qr_{name}_{prenom}.png'
    qr_path = os.path.join(destination_path, qr_filename)
    qr.save(qr_path)

    # Redirect to the route for downloading the contract
    return redirect(url_for('download_contract', name=name, prenom=prenom, date_debut=date_debut, date_fin=date_fin, qr_filename=qr_filename))


@app.route('/download-contract/<name>/<prenom>/<date_debut>/<date_fin>/<qr_filename>', methods=['GET'])
def download_contract(name, prenom, date_debut, date_fin, qr_filename):
    # Define destination path for download
    home_directory = os.path.expanduser("~")
    destination_path = os.path.join(home_directory, 'contracts')

    # Path to the PDF and QR code files
    pdf_filename = f'contract_{name}_{prenom}.pdf'
    pdf_path = os.path.join(destination_path, pdf_filename)

    # Return the PDF and QR code files for download
    return send_file(pdf_path, as_attachment=True), send_file(os.path.join(destination_path, qr_filename), as_attachment=True)

if __name__ == '__main__':
    app.run(host="0.0.0.0" ,port=int("8000"),debug=False)

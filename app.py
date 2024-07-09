import requests
from flask import Flask, render_template, request, redirect, url_for, jsonify, session, flash, json
from pymongo import MongoClient
import os
from os.path import join, dirname
from dotenv import load_dotenv
import hashlib
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from bson.objectid import ObjectId
import base64
import logging
import locale
import json
import pytz
from bson.errors import InvalidId
from apscheduler.schedulers.background import BackgroundScheduler
import random
from flask_mail import Mail, Message
import jwt


locale.setlocale(locale.LC_ALL, '')

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config['UPLOAD_FOLDER'] = 'static/img/uploads/profile'
app.config['UPLOAD_Gallery'] = 'static/img/uploads/gallery'
app.config['UPLOAD_email'] = 'static/img/uploads/email'
app.config['UPLOAD_teamMember'] = 'static/img/uploads/teamMembers'
app.config['MAX_CONTENT_PATH'] = 1 * 1024 * 1024
app.secret_key = 'supersecretkey'

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

#Konvigurasi .env
MONGODB_URI = os.environ.get("MONGODB_URI")
DB_NAME = os.environ.get("DB_NAME")
SECRET_KEY = os.environ.get("SECRET_KEY")
MIDTRANS_SERVER_KEY = os.environ.get("MIDTRANS_SERVER_KEY")

client = MongoClient(MONGODB_URI)
db = client[DB_NAME]

# Konfigurasi Flask-Mail
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT'))
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')

mail = Mail(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_user_info():
    if 'logged_in' in session:
        email = session['email']
        user_info = db.users.find_one({'email': email})
        return user_info
    return None

def get_admin_info():
    if 'logged_in' in session:
        email = session['email']
        admin_info = db.admin.find_one({'email': email})
        return admin_info
    return None
#error handling
@app.errorhandler(404)
def page_not_found(e):
    return render_template('error_page/404.html'), 404

@app.errorhandler(403)
def forbidden(e):
    return render_template('error_page/403.html'), 403

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('error_page/500.html'), 500

@app.errorhandler(Exception)
def handle_exception(e):
    return render_template('error_page/error.html', error=e), 500

@app.route('/', methods=['GET'])
def home():
    # Ambil ulasan dari database
    reviews = list(db.reviews.find().sort('created_at', -1))  # Mengambil semua ulasan dan mengurutkan berdasarkan tanggal

    for review in reviews:
        user = db.users.find_one({'email': review['email']})
        if user:
            review['profile_picture_url'] = user.get('profile_picture_url', '../../../static/img/default-profile.jpg')
            review['full_name'] = user.get('full_name', 'Anonim')

    return render_template('home/index.html', reviews=reviews)

@app.route('/rooms', methods=['GET'])
def rooms():
    check_in_date_str = request.args.get('check_in_date')
    today = datetime.today().date()
    tanggal_cek_in = None

    if check_in_date_str:
        try:
            tanggal_cek_in = datetime.strptime(check_in_date_str, '%Y-%m-%d').date()
        except ValueError:
            return redirect(url_for('error_page'))

    if not check_in_date_str:
        check_in_date = datetime.today().strftime('%d/%m/%Y')
    else:
        try:
            parsed_date = datetime.strptime(check_in_date_str, '%d/%m/%Y')
        except ValueError:
            try:
                parsed_date = datetime.strptime(check_in_date_str, '%Y-%m-%d')
            except ValueError:
                return redirect(url_for('error_page'))

        check_in_date = parsed_date.strftime('%d/%m/%Y')

    query_date = check_in_date

    deluxe_room = db.room_prices.find_one({"date": query_date, "room_type": "Deluxe"})
    deluxe_family_room = db.room_prices.find_one({"date": query_date, "room_type": "Family Deluxe"})

    return render_template('room/rooms.html',
                           deluxe_room=deluxe_room, 
                           deluxe_family_room=deluxe_family_room, 
                           format_currency=format_currency, 
                           today=today, 
                           tanggal_cek_in=tanggal_cek_in)

@app.route('/rooms/deluxe', methods=['GET'])
def deluxe_room():
    return render_template('room/duluxe.html')

@app.route('/team/member', methods=['GET'])
def team_member():
    # Cek pengaturan
    setting = db.settings.find_one({'setting': 'team_member_enabled'})
    team_member_enabled = setting['value'] if setting else False
    
    if not team_member_enabled:
        return render_template('error_page/error_setting.html', message="Halaman Team Member dinonaktifkan."), 403
    
    # Periksa apakah pengguna login
    user_logged_in = 'user_id' in session
    
    team_members = db.teamMember.find()
    return render_template('teamMemberPage/teamMember.html', team_members=team_members, user_logged_in=user_logged_in)

@app.route('/faq')
def faq():
    faqs = db.faqs.find()
    return render_template('faq/faq.html', faqs=faqs)

@app.route('/rooms/family-deluxe', methods=['GET'])
def deluxe_family():
    return render_template('room/family_room.html')

@app.route('/facilities', methods=['GET'])
def facilities():
    return render_template('facilities/facilities.html')

@app.route('/gallery', methods=['GET'])
def gallery():
    gallery = list(db.gallery.find())
    return render_template('gallery/gallery.html', gallery=gallery)

@app.route('/contact', methods=['GET'])
def contact():
    return render_template('contact/contact.html')

@app.route('/book', methods=['GET'])
def book():
    check_in_date = request.args.get('check_in_date')
    check_in_date_str = request.args.get('check_in_date')
    today = datetime.today().date()
    tanggal_cek_in = None
    if check_in_date_str:
        tanggal_cek_in = datetime.strptime(check_in_date_str, '%Y-%m-%d').date()

    if not check_in_date:
        check_in_date = datetime.today().strftime('%d/%m/%Y')
    else:
        try:
            # Try to parse the date in 'dd/mm/yyyy' format
            parsed_date = datetime.strptime(check_in_date, '%d/%m/%Y')
        except ValueError:
            # If it fails, try to parse it in 'yyyy-mm-dd' format
            parsed_date = datetime.strptime(check_in_date, '%Y-%m-%d')
        check_in_date = parsed_date.strftime('%d/%m/%Y')

    query_date = check_in_date

    deluxe_room = db.room_prices.find_one({"date": query_date, "room_type": "Deluxe"})
    deluxe_family_room = db.room_prices.find_one({"date": query_date, "room_type": "Family Deluxe"})

    return render_template('book/book.html', deluxe_room=deluxe_room, deluxe_family_room=deluxe_family_room, format_currency=format_currency, today=today, tanggal_cek_in=tanggal_cek_in)

@app.route('/sign_in', methods=['POST'])
def sign_in():
    email = request.form.get('email')
    password = request.form.get('password')
    recaptcha_response = request.form.get('g-recaptcha-response')

    # Verify reCAPTCHA
    secret_key =  os.getenv('SECRET_KEY')
    payload = {
        'secret': secret_key,
        'response': recaptcha_response
    }
    recaptcha_verify = requests.post('https://www.google.com/recaptcha/api/siteverify', data=payload)
    result = recaptcha_verify.json()

    if not result.get('success'):
        return jsonify({'result': 'fail', 'msg': 'Invalid reCAPTCHA. Please try again.'})

    user = db.users.find_one({'email': email})

    if user:
        if not user['is_active']:
            return jsonify({'result': 'unverified', 'msg': 'Akun belum diaktifkan. Silakan verifikasi email Anda.'})

        hashed_password = hashlib.sha256(password.encode('utf-8')).hexdigest()
        if user['password'] == hashed_password:
            session['logged_in'] = True
            session['email'] = email
            session['full_name'] = user['full_name']
            session['user_id'] = str(user['_id'])
            return jsonify({'result': 'success', 'msg': 'Login berhasil'})
        else:
            return jsonify({'result': 'fail', 'msg': 'Password Salah!!!'})
    else:
        return jsonify({'result': 'fail', 'msg': 'Pengguna tidak ditemukan!'})

def send_otp(email, otp):
    try:
        msg = Message("Kode OTP Anda", recipients=[email])
        msg.body = (
            f"Kode OTP Anda adalah {otp}. Kode ini berlaku selama satu jam.\n"
            "Mohon jangan bagikan kode ini kepada siapa pun."
        )
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

def generate_otp():
    return random.randint(100000, 999999)

def save_otp(email, otp):
    expiration_time = datetime.now() + timedelta(hours=1)
    db.otps.insert_one({'email': email, 'otp': otp, 'expires_at': expiration_time})

def verify_otp(email, otp):
    record = db.otps.find_one({'email': email, 'otp': otp})
    if record and record['expires_at'] > datetime.now():
        db.otps.delete_one({'_id': record['_id']})
        return True
    return False

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            full_name = request.form.get('fullName')
            email = request.form.get('email')
            password = request.form.get('password')
            confirm_password = request.form.get('confirmPassword')
            phone_number = request.form.get('phoneNumber')
            birth_date = request.form.get('birthDate')
            gender = request.form.get('gender')
            address = request.form.get('address')
            city = request.form.get('city')
            region = request.form.get('region')
            postal_code = request.form.get('postalCode')

            if not all([full_name, email, password, confirm_password, phone_number, birth_date, gender, address, city, region, postal_code]):
                return jsonify({'error': 'Semua field yang diberi tanda * harus diisi.'}), 400

            if password != confirm_password:
                return jsonify({'error': 'Kata sandi dan konfirmasi kata sandi tidak cocok.'}), 400

            if db.users.find_one({'email': email}):
                return jsonify({'error': 'Email sudah digunakan.'}), 400

            hashed_password = hashlib.sha256(password.encode('utf-8')).hexdigest()
            profile_picture_url = url_for('static', filename='img/uploads/profile/profile_placeholder.png')

            user_data = {
                'full_name': full_name,
                'email': email,
                'password': hashed_password,
                'phone_number': phone_number,
                'birth_date': birth_date,
                'gender': gender,
                'address': address,
                'city': city,
                'region': region,
                'postal_code': postal_code,
                'profile_picture_url': profile_picture_url,
                'is_active': False,
                'created_at': datetime.now()
            }

            user_id = db.users.insert_one(user_data).inserted_id

            otp = generate_otp()
            save_otp(email, otp)
            if send_otp(email, otp):
                return jsonify({'success': 'Pendaftaran berhasil! Silakan cek email Anda untuk kode OTP.', 'redirect': f'/otp/{user_id}'}), 200
            else:
                return jsonify({'error': 'Gagal mengirim email OTP. Coba lagi nanti.'}), 500
        except Exception as e:
            print(f"Error: {e}")
            return jsonify({'error': str(e)}), 500

    return render_template('register/register.html')

def delete_unverified_users():
    threshold = datetime.now() - timedelta(minutes=1)
    result = db.users.delete_many({'is_active': False, 'created_at': {'$lt': threshold}})
    logging.info(f"Deleted {result.deleted_count} unverified users")

scheduler = BackgroundScheduler()
scheduler.add_job(func=delete_unverified_users, trigger="interval", hours=5)
scheduler.start()

@app.route('/otp/<user_id>', methods=['GET', 'POST'])
def otp(user_id):
    user = db.users.find_one({'_id': ObjectId(user_id)})
    if not user:
        return redirect(url_for('register'))

    if request.method == 'POST':
        otp = request.form.get('otp')
        if verify_otp(user['email'], otp):
            db.users.update_one({'_id': ObjectId(user_id)}, {'$set': {'is_active': True}})
            return jsonify({'success': 'Verifikasi berhasil!'}), 200
        else:
            return jsonify({'error': 'Kode OTP salah atau sudah kadaluarsa.'}), 400

    return render_template('register/otp.html', email=user['email'])

@app.route('/verify_otp', methods=['POST'])
def verify_otp_route():
    email = request.form.get('email')
    otp = request.form.get('otp')

    if verify_otp(email, int(otp)):
        db.users.update_one({'email': email}, {'$set': {'is_active': True}})
        return jsonify({'success': 'Akun Anda telah diaktifkan!'}), 200
    else:
        return jsonify({'error': 'OTP tidak valid atau telah kadaluwarsa.'}), 400


# Fungsi untuk menghasilkan token JWT
def generate_token(email):
    token = jwt.encode({'email': email, 'exp': datetime.utcnow() + timedelta(minutes=15)}, SECRET_KEY, algorithm='HS256')
    return token

# Fungsi untuk memverifikasi token JWT
def verify_token(token):
    try:
        data = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return data['email']
    except jwt.ExpiredSignatureError:
        logging.error("Token has expired")
        return None
    except jwt.InvalidTokenError as e:
        logging.error(f"Invalid token: {e}")
        return None

# Route untuk permintaan lupa password
@app.route('/forget/password', methods=['GET', 'POST'])
def forget_password():
    if request.method == 'POST':
        email = request.form['email']
        logging.info(f"Received password reset request for email: {email}")
        
        try:
            user = db.users.find_one({'email': email})
            logging.debug(f"Database response for email {email}: {user}")
            if user:
                token = generate_token(email)
                reset_link = url_for('reset_password', token=token, _external=True)
                msg = Message('Reset Password', recipients=[email])
                msg.body = f'Klik link berikut untuk mereset password Anda: {reset_link}\n\nKode ini berlaku selama 15 menit.'
                try:
                    mail.send(msg)
                    logging.info(f"Password reset email sent to: {email}")
                    return jsonify({'success': True})
                except Exception as e:
                    logging.error(f"Failed to send email: {e}")
                    return jsonify({'success': False, 'error': str(e)}), 500
            else:
                logging.warning(f"Email not found: {email}")
                return jsonify({'success': False, 'error': 'Email not found'}), 404
        except Exception as e:
            logging.error(f"Error processing password reset request: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    return render_template('login/forget_password.html')

# Route untuk mereset password
@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if request.method == 'POST':
        password = request.form['password']
        email = verify_token(token)
        if email:
            hashed_password = hashlib.sha256(password.encode('utf-8')).hexdigest()
            db.users.update_one({'email': email}, {'$set': {'password': hashed_password}})
            logging.info(f"Password reset successful for email: {email}")
            return jsonify({'success': True})
        else:
            logging.warning("Invalid or expired token used for password reset.")
            return jsonify({'success': False, 'error': 'Token tidak valid atau kadaluarsa.'}), 400
    return render_template('login/reset_password.html', token=token)

@app.route("/login", methods=['GET', 'POST'])
def login():
    # Cek pengaturan
    setting = db.settings.find_one({'setting': 'login_enabled'})
    login_enabled = setting['value'] if setting else False

    if not login_enabled:
        return render_template('error_page/error_setting.html', message="Halaman login dinonaktifkan."), 403

    msg = request.args.get("msg")
    return render_template("login/login.html", msg=msg)

@app.route("/user/index")
def user_index():
    user_info = get_user_info()
    if user_info:
        reviews = list(db.reviews.find().sort('created_at', -1))  # Mengambil semua ulasan dan mengurutkan berdasarkan tanggal

        for review in reviews:
            user = db.users.find_one({'email': review['email']})
            if user:
                review['profile_picture_url'] = user.get('profile_picture_url', '../../../static/img/default-profile.jpg')
                review['full_name'] = user.get('full_name', 'Anonim')
        return render_template('user/home/index.html', user_info=user_info, reviews=reviews)
    else:
        return redirect(url_for('login'))

# khusus user login yang bisa akses
@app.route('/user/rooms', methods=['GET'])
def user_rooms():
    user_info = get_user_info()
    if user_info:
        check_in_date_str = request.args.get('check_in_date')
        today = datetime.today().date()
        tanggal_cek_in = None

        if check_in_date_str:
            try:
                tanggal_cek_in = datetime.strptime(check_in_date_str, '%Y-%m-%d').date()
            except ValueError:
                return redirect(url_for('error_page'))

        if not check_in_date_str:
            check_in_date = datetime.today().strftime('%d/%m/%Y')
        else:
            try:
                parsed_date = datetime.strptime(check_in_date_str, '%d/%m/%Y')
            except ValueError:
                try:
                    parsed_date = datetime.strptime(check_in_date_str, '%Y-%m-%d')
                except ValueError:
                    return redirect(url_for('error_page'))

            check_in_date = parsed_date.strftime('%d/%m/%Y')

        query_date = check_in_date

        deluxe_room = db.room_prices.find_one({"date": query_date, "room_type": "Deluxe"})
        deluxe_family_room = db.room_prices.find_one({"date": query_date, "room_type": "Family Deluxe"})

        return render_template('user/room/rooms.html',
                            user_info=user_info,
                            deluxe_room=deluxe_room, 
                            deluxe_family_room=deluxe_family_room, 
                            format_currency=format_currency, 
                            today=today, 
                            tanggal_cek_in=tanggal_cek_in)
    else:
        return redirect(url_for('login'))
    
@app.route('/user/faq')
def user_faq():
    faqs = db.faqs.find()
    return render_template('user/faq/faq.html', faqs=faqs)

@app.route('/user/rooms/deluxe', methods=['GET'])
def user_deluxe_room():
    user_info = get_user_info()
    if user_info:
        return render_template('user/room/deluxe.html', user_info=user_info)
    else:
        return redirect(url_for('login'))

@app.route('/user/rooms/family-deluxe', methods=['GET'])
def user_deluxe_family():
    user_info = get_user_info()
    if user_info:
        return render_template('user/room/family_room.html', user_info=user_info)
    else:
        return redirect(url_for('login'))

@app.route('/user/facilities', methods=['GET'])
def user_facilities():
    user_info = get_user_info()
    if user_info:
        return render_template('user/facilities/facilities.html', user_info=user_info)
    else:
        return redirect(url_for('login'))

@app.route('/user/gallery', methods=['GET'])
def user_gallery():
    user_info = get_user_info()
    if user_info:
        gallery = list(db.gallery.find())
        return render_template('user/gallery/gallery.html', gallery=gallery, user_info=user_info)
    else:
        return redirect(url_for('login'))

@app.route('/user/contact', methods=['GET'])
def user_contact():
    user_info = get_user_info()
    if user_info:
        return render_template('user/contact/contact.html', user_info=user_info)
    else:
        return redirect(url_for('login'))

@app.route('/user/profile', methods=['GET'])
def user_profile():
    user_info = get_user_info()
    if user_info:
        email = user_info.get('email')
        reviews = list(db.reviews.find({'email': email}))
        return render_template('user/profile/profile.html', user_info=user_info, reviews=reviews)
    else:
        return redirect(url_for('login'))

@app.route('/delete_review/<review_id>', methods=['DELETE'])
def delete_review(review_id):
    email = session.get('email')
    if email:
        result = db.reviews.delete_one({'_id': ObjectId(review_id), 'email': email})
        if result.deleted_count:
            return jsonify({'success': True}), 200
        else:
            return jsonify({'success': False}), 404
    else:
        return jsonify({'success': False}), 403

@app.route('/user/profile/edit', methods=['GET', 'POST'])
def edit_profile():
    if 'logged_in' in session:
        email = session['email']
        user_info = db.users.find_one({'email': email})

        if request.method == 'POST':
            full_name = request.form.get('fullName')
            phone_number = request.form.get('phoneNumber')
            birth_date = request.form.get('birthDate')
            gender = request.form.get('gender')
            address = request.form.get('address')
            city = request.form.get('city')
            region = request.form.get('region')
            postal_code = request.form.get('postalCode')

            db.users.update_one(
                {'email': email},
                {'$set': {
                    'full_name': full_name,
                    'phone_number': phone_number,
                    'birth_date': birth_date,
                    'gender': gender,
                    'address': address,
                    'city': city,
                    'region': region,
                    'postal_code': postal_code
                }}
            )
            return redirect(url_for('user_profile'))
        
        return render_template('user/profile/edit_profile.html', user_info=user_info)
    else:
        return redirect(url_for('login'))

@app.route('/user/profile/upload_photo', methods=['POST'])
def upload_photo():
    if 'logged_in' in session:
        email = session['email']
        if 'profile_picture' in request.files:
            profile_picture = request.files['profile_picture']
            if profile_picture:
                filename = secure_filename(profile_picture.filename)
                profile_picture_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                profile_picture.save(profile_picture_path)
                
                profile_picture_url = url_for('static', filename='img/uploads/profile/' + filename)
                db.users.update_one(
                    {'email': email},
                    {'$set': {'profile_picture_url': profile_picture_url}}
                )
        return redirect(url_for('user_profile'))
    else:
        return redirect(url_for('login'))


def format_currency(value):
    return locale.format_string("%d", value, grouping=True)

# Timezone for Indonesia (Jakarta)
wib = pytz.timezone('Asia/Jakarta')

@app.route('/user/reservasi', methods=['GET'])
def user_reservasi():
    if 'logged_in' in session:
        email = session['email']
        user_info = db.users.find_one({'email': email})

        # Get filters from request args
        booking_code = request.args.get('booking_code', '')
        tipe_kamar = request.args.get('tipe_kamar', '')
        page = int(request.args.get('page', 1))
        limit = 5
        skip = (page - 1) * limit

        # Fetch bookings from both collections
        query = {'email': email}
        if booking_code:
            query['booking_code'] = booking_code
        if tipe_kamar:
            query['tipe_kamar'] = tipe_kamar

        deluxe_bookings = list(db.deluxe_booking.find(query).sort('created_at', -1).skip(skip).limit(limit))
        family_deluxe_bookings = list(db.family_deluxe_booking.find(query).sort('created_at', -1).skip(skip).limit(limit))
        
        # Combine bookings
        all_bookings = deluxe_bookings + family_deluxe_bookings
        all_bookings = sorted(all_bookings, key=lambda k: k['created_at'], reverse=True)

        now = datetime.now()

        for booking in all_bookings:
            # Convert string dates from the database to datetime objects
            check_in_date_str = booking.get('check_in_date', '')
            check_out_date_str = booking.get('check_out_date', '')
            
            try:
                check_in_date = datetime.strptime(check_in_date_str, '%d/%m/%Y')
                check_out_date = datetime.strptime(check_out_date_str, '%d/%m/%Y')
                
                # Convert dates to strings for the template to use
                booking['check_in_date'] = check_in_date.strftime('%d/%m/%Y')
                booking['check_out_date'] = check_out_date.strftime('%d/%m/%Y')

                # Check if current time is after check-out date
                booking['can_review'] = now > check_out_date
            except ValueError:
                booking['check_in_date'] = check_in_date_str
                booking['check_out_date'] = check_out_date_str
                booking['can_review'] = False

            review_exists = db.reviews.find_one({'booking_id': str(booking['_id']), 'email': email}) is not None
            booking['review_exists'] = review_exists

        if request.args.get('page'):
            return render_template('user/reservasi/booking_list.html', user_bookings=all_bookings)
        else:
            return render_template('user/reservasi/reservasi.html', user_info=user_info, user_bookings=all_bookings, format_currency=format_currency)
    else:
        return redirect(url_for('login'))
        
@app.route('/give_review/<booking_id>', methods=['GET', 'POST'])
def give_review(booking_id):
    if 'logged_in' in session:
        email = session.get('email')
        if not email:
            flash('Anda harus login untuk memberikan ulasan', 'danger')
            return redirect(url_for('login'))

        user_info = db.users.find_one({'email': email})

        # Check booking in deluxe_booking collection
        booking = db.deluxe_booking.find_one({'_id': ObjectId(booking_id)})
        room_type = 'Deluxe'

        # If not found, check in family_deluxe_booking collection
        if not booking:
            booking = db.family_deluxe_booking.find_one({'_id': ObjectId(booking_id)})
            room_type = 'Family Deluxe'

        if not booking:
            flash('Booking tidak ditemukan', 'danger')
            return redirect(url_for('user_reservasi'))

        # Check if review already exists for this booking
        review_exists = db.reviews.find_one({'booking_id': booking_id, 'email': email})
        if review_exists:
            flash('Anda sudah menulis ulasan untuk booking ini', 'danger')
            return redirect(url_for('user_reservasi'))

        if request.method == 'POST':
            rating = int(request.form.get('rating'))
            review = request.form.get('review')

            db.reviews.insert_one({
                'booking_id': booking_id,
                'booking_code': booking['booking_code'],
                'email': email,
                'full_name': user_info['full_name'],  # Add user full name
                'rating': rating,
                'review': review,
                'tipe_kamar': room_type,
                'created_at': datetime.now(wib),
                'profile_picture_url': user_info.get('profile_picture_url', '/static/img/uploads/profile/profile_placeholder.png'),  # Add profile picture URL
            })

            flash('Ulasan berhasil disimpan', 'success')
            return redirect(url_for('user_reservasi'))

        return render_template('user/reservasi/give_review.html', user_info=user_info, booking=booking)
    else:
        return redirect(url_for('login_user'))
        
#handle halaman error user
@app.route('/error')
def error_page():
    user_info = get_user_info()

    if user_info:
        return render_template('user/error_page/error_page.html', user_info=user_info)
    else:
        return redirect(url_for('login'))


@app.route('/user/book', methods=['GET'])
def user_book():
    user_info = get_user_info()
    if user_info:

        check_in_date_str = request.args.get('check_in_date')
        today = datetime.today().date()
        tanggal_cek_in = None

        if check_in_date_str:
            try:
                tanggal_cek_in = datetime.strptime(check_in_date_str, '%Y-%m-%d').date()
            except ValueError:
                return redirect(url_for('error_page'))

        if not check_in_date_str:
            check_in_date = datetime.today().strftime('%d/%m/%Y')
        else:
            try:
                parsed_date = datetime.strptime(check_in_date_str, '%d/%m/%Y')
            except ValueError:
                try:
                    parsed_date = datetime.strptime(check_in_date_str, '%Y-%m-%d')
                except ValueError:
                    return redirect(url_for('error_page'))

            check_in_date = parsed_date.strftime('%d/%m/%Y')

        query_date = check_in_date

        deluxe_room = db.room_prices.find_one({"date": query_date, "room_type": "Deluxe"})
        deluxe_family_room = db.room_prices.find_one({"date": query_date, "room_type": "Family Deluxe"})

        return render_template('user/book/book.html', 
                            user_info=user_info, 
                            deluxe_room=deluxe_room, 
                            deluxe_family_room=deluxe_family_room, 
                            format_currency=format_currency, 
                            today=today, 
                            tanggal_cek_in=tanggal_cek_in)  
    else:
        return redirect(url_for('login'))
    
@app.route('/user/room/booking/deluxe-room', methods=['GET', 'POST'])
def user_deluxe_book():
    user_info = get_user_info()  # Function to get user information
    
    check_in_date_str = request.args.get('check_in_date', datetime.today().strftime('%Y-%m-%d'))
    
    check_in_date = datetime.strptime(check_in_date_str, '%Y-%m-%d')

    query_date = check_in_date.strftime('%d/%m/%Y')
    
    price_info = db.room_prices.find_one({'date': query_date, 'room_type': 'Deluxe'})
    if price_info:
        harga_normal = price_info.get('price', 0)
        harga_diskon = price_info.get('discount_price', 0)
    else:
        harga_normal = 0
        harga_diskon = 0
    
    # Ambil lama inap dari parameter URL atau gunakan nilai default 1 malam jika tidak ada
    lama_inap = int(request.args.get('lamaInap', '1'))
    
    check_out_date = check_in_date + timedelta(days=lama_inap)
    
    check_in_date_display_str = check_in_date.strftime('%d/%m/%Y')
    check_out_date_display_str = check_out_date.strftime('%d/%m/%Y')

    # Render template dengan informasi yang diperlukan
    if user_info:
        return render_template(
            'user/book/deluxe_book.html', 
            user_info=user_info, 
            check_in_date_display=check_in_date_display_str,  
            check_in_date=check_in_date_str,  
            check_out_date=check_out_date_display_str,
            harga_normal=harga_normal, 
            harga_diskon=harga_diskon, 
            lama_inap=lama_inap,
            format_currency=format_currency
        )
    else:
        return redirect(url_for('login'))

@app.route('/deluxe_save_booking', methods=['POST'])
def deluxe_save_booking():
    if request.method == 'POST':
        data = request.get_json()

        booking_code = data.get('bookingCode')
        nama_lengkap = data.get('namaLengkap')
        email = data.get('email')
        nomor_handphone = data.get('nomorHandphone')
        pesanan_untuk = data.get('pesananUntuk')
        guest_name = data.get('guestName')
        lama_inap = data.get('lamaInap')
        permintaan_khusus = data.get('permintaanKhusus')
        harga_normal = data.get('hargaNormal')
        harga_diskon = data.get('hargaDiskon')
        diskon = data.get('diskon')  # Tambahkan untuk mendapatkan data diskon dari frontend
        kode_voucher = data.get('kodeVoucher','')
        check_in_date = data.get('checkInDate')
        check_out_date = data.get('checkOutDate')
        created_at = datetime.now(wib)
        updated_at = datetime.now(wib)

        try:
            lama_inap = int(lama_inap)
        except ValueError:
            return jsonify({'error': 'Lama inap harus berupa angka.'}), 400

        harga_total = harga_diskon * lama_inap - diskon  # Perhitungan harga total setelah diskon

        booking_data = {
            'booking_code': booking_code,
            'tipe_kamar': 'Deluxe',
            'nama_lengkap': nama_lengkap,
            'email': email,
            'nomor_handphone': nomor_handphone,
            'pesanan_untuk': pesanan_untuk,
            'guest_name': guest_name,
            'lama_inap': lama_inap,
            'permintaan_khusus': permintaan_khusus,
            'harga_normal': harga_normal,
            'harga_diskon': harga_diskon,
            'diskon': diskon,  # Simpan diskon yang diterapkan
            'harga_total': harga_total,
            'kode_voucher': kode_voucher,  # Simpan kode voucher yang digunakan
            'check_in_date': check_in_date,
            'check_out_date': check_out_date,
            'created_at': created_at,
            'updated_at': updated_at,
            'status': 'menunggu pembayaran'
        }

        db.deluxe_booking.insert_one(booking_data)

        return jsonify({'success': 'Booking berhasil disimpan!'}), 200

    return jsonify({'error': 'Metode tidak valid.'}), 400

@app.route('/validate_voucher', methods=['POST'])
def validate_voucher():
    data = request.get_json()
    kode_voucher = data.get('kode_voucher')
    lama_inap = data.get('lama_inap')
    harga_kamar = data.get('harga_kamar')
    tipe_kamar = data.get('tipe_kamar')  # Menambahkan tipe kamar dari permintaan

    voucher = db.discounts.find_one({'kode': kode_voucher})
    if not voucher:
        return jsonify({'valid': False, 'message': 'Kode voucher tidak valid.'}), 400

    current_date = datetime.now()
    start_date = datetime.strptime(voucher['tanggal_mulai'], '%d/%m/%Y')
    end_date = datetime.strptime(voucher['tanggal_akhir'], '%d/%m/%Y')

    # Cek apakah tanggal sekarang sebelum tanggal mulai
    if current_date < start_date:
        return jsonify({'valid': False, 'message': 'Voucher belum berlaku.'}), 400
    
    # Cek apakah tanggal sekarang setelah tanggal akhir
    if current_date > end_date:
        return jsonify({'valid': False, 'message': 'Voucher sudah tidak berlaku.'}), 400

    # Cek apakah tipe kamar cocok dengan voucher
    if voucher['tipe_kamar'].lower() != tipe_kamar.lower():
        return jsonify({'valid': False, 'message': 'Voucher tidak berlaku untuk tipe kamar ini.'}), 400

    if voucher['kuota'] <= 0:
        return jsonify({'valid': False, 'message': 'Kuota voucher telah habis.'}), 400

    if voucher['jenis_diskon'].lower() == 'persen':
        diskon = min(harga_kamar * (voucher['persentase'] / 100), voucher['diskon_maks'])
    else:
        diskon = min(voucher['potongan'], harga_kamar)

    return jsonify({'valid': True, 'diskon': diskon, 'message': 'Voucher berhasil diterapkan!', 'description': voucher.get('deskripsi', '')}), 200

@app.template_filter('tojson')
def tojson_filter(value):
    def convert(o):
        if isinstance(o, ObjectId):
            return str(o)
        if isinstance(o, datetime):
            return o.isoformat()
        return json.JSONEncoder().default(o)
    return json.dumps(value, default=convert)

@app.route('/payment_token/<booking_code>', methods=['GET'])
def payment_token(booking_code):
    logger.info(f'Received payment token request for booking_code: {booking_code}')
    booking = db.deluxe_booking.find_one({'booking_code': booking_code}) or db.family_deluxe_booking.find_one({'booking_code': booking_code})
    if booking:
        item_details = [
            {
                'id': booking_code,
                'price': booking['harga_total'],
                'quantity': 1,
                'name': f"Kamar {booking['tipe_kamar']}: {booking['lama_inap']} malam"
            }
        ]

        transaction_details = {
            'order_id': booking_code,
            'gross_amount': booking['harga_total']
        }
        customer_details = {
            'first_name': booking['nama_lengkap'],
            'email': booking['email'],
            'phone': booking['nomor_handphone']
        }
        payload = {
            'transaction_details': transaction_details,
            'customer_details': customer_details,
            'item_details': item_details
        }
        headers = {
            'Authorization': 'Basic ' + base64.b64encode((MIDTRANS_SERVER_KEY + ':').encode()).decode(),
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        response = requests.post('https://app.midtrans.com/snap/v1/transactions', headers=headers, json=payload)
        response_data = response.json()
        logger.info(f'Response from Midtrans: {response_data}')
        if 'token' in response_data:
            return jsonify({'token': response_data['token']})
        else:
            logger.error(f'Error from Midtrans: {response_data}')
            return jsonify({'error': response_data}), 500
    logger.error(f'Booking not found for booking_code: {booking_code}')
    return jsonify({'error': 'Booking not found'}), 404

@app.route('/payment_callback', methods=['POST'])
def payment_callback():
    data = request.json
    order_id = data['order_id']
    transaction_status = data['transaction_status']
    fraud_status = data['fraud_status']
    
    logger.info(f'Payment callback received for order_id: {order_id} with status: {transaction_status} and fraud status: {fraud_status}')
    
    booking = db.deluxe_booking.find_one({'booking_code': order_id}) or db.family_deluxe_booking.find_one({'booking_code': order_id})

    if booking:
        booking_collection = db.deluxe_booking if db.deluxe_booking.find_one({'booking_code': order_id}) else db.family_deluxe_booking
        if transaction_status == 'capture':
            if fraud_status == 'accept':
                booking_collection.update_one({'booking_code': order_id}, {'$set': {'status': 'menunggu konfirmasi'}})
                return jsonify({'result': 'success'})
        elif transaction_status in ['settlement', 'pending']:
            booking_collection.update_one({'booking_code': order_id}, {'$set': {'status': 'menunggu konfirmasi'}})
            return jsonify({'result': 'success'})
        elif transaction_status in ['deny', 'expire', 'cancel']:
            booking_collection.update_one({'booking_code': order_id}, {'$set': {'status': 'dibatalkan'}})
            return jsonify({'result': 'success'})
    return jsonify({'result': 'error'})

@app.route('/update_booking_status', methods=['POST'])
def update_booking_status():
    data = request.json
    if not data or 'booking_code' not in data or 'new_status' not in data:
        logger.error('Invalid request data')
        return jsonify({'result': 'error', 'message': 'Invalid request data'}), 400

    booking_code = data['booking_code']
    new_status = data['new_status']
    
    logger.info(f'Received request to update booking status for booking_code: {booking_code} to {new_status}')
    
    booking = db.deluxe_booking.find_one({'booking_code': booking_code}) or db.family_deluxe_booking.find_one({'booking_code': booking_code})
    if not booking:
        logger.error('Booking not found')
        return jsonify({'result': 'error', 'message': 'Booking not found'}), 404
    
    # Update booking status
    booking_collection = db.deluxe_booking if db.deluxe_booking.find_one({'booking_code': booking_code}) else db.family_deluxe_booking
    result = booking_collection.update_one({'booking_code': booking_code}, {'$set': {'status': new_status}})
    if result.modified_count > 0:
        # Update room stock
        try:
            check_in_date = datetime.strptime(booking['check_in_date'], '%d/%m/%Y')
            logger.info(f'Parsed check-in date: {check_in_date}')
        except ValueError:
            logger.error('Invalid date format in booking')
            return jsonify({'result': 'error', 'message': 'Invalid date format in booking'}), 400

        room_type = booking.get('tipe_kamar')
        if not room_type:
            logger.error('Room type not found in booking')
            return jsonify({'result': 'error', 'message': 'Room type not found in booking'}), 400

        # Log room type and check-in date
        logger.info(f'Room type: {room_type}, Check-in date: {check_in_date.strftime("%d/%m/%Y")}')

        # Ensure the room type matches the naming in room_prices
        if room_type == 'Deluxe Family':
            logger.info('Room type Deluxe Family detected')
            room_type = 'Family Deluxe'

        logger.info(f'Updating stock for room type: {room_type} on date: {check_in_date.strftime("%d/%m/%Y")}')
        
        # Check if the document exists in room_prices
        room_price_doc = db.room_prices.find_one({'date': check_in_date.strftime('%d/%m/%Y'), 'room_type': room_type})
        
        if room_price_doc:
            logger.info('Room price document found, updating stock')
            # If the document exists, update the stock
            update_result = db.room_prices.update_one(
                {'date': check_in_date.strftime('%d/%m/%Y'), 'room_type': room_type},
                {'$inc': {'stock': -1}}
            )
            logger.info(f'Update result: {update_result.modified_count}')
            if update_result.modified_count > 0:
                logger.info('Room stock updated successfully')
                return jsonify({'result': 'success'})
            else:
                logger.error('Failed to update room stock')
                return jsonify({'result': 'error', 'message': 'Failed to update room stock'}), 500
        else:
            logger.error('Room stock document not found for the specified date and room type')
            return jsonify({'result': 'error', 'message': 'Room stock document not found for the specified date and room type'}), 404
    else:
        logger.error('Failed to update booking status')
        return jsonify({'result': 'error', 'message': 'Failed to update booking status'}), 500

@app.route('/cancel_booking', methods=['POST'])
def cancel_booking():
    booking_id = request.form.get('booking_id')
    logger.info(f'Cancel booking request received for booking_id: {booking_id}')
    if booking_id:
        result_deluxe = db.deluxe_booking.update_one({'_id': ObjectId(booking_id)}, {'$set': {'status': 'dibatalkan'}})
        result_family = db.family_deluxe_booking.update_one({'_id': ObjectId(booking_id)}, {'$set': {'status': 'dibatalkan'}})
        
        if result_deluxe.modified_count > 0 or result_family.modified_count > 0:
            logger.info(f'Booking cancelled successfully for booking_id: {booking_id}')
            return jsonify({'result': 'success', 'msg': 'Booking berhasil dibatalkan.'})
        else:
            logger.error(f'Failed to cancel booking for booking_id: {booking_id}')
            return jsonify({'result': 'error', 'msg': 'Gagal membatalkan booking.'})
    logger.error(f'Invalid booking_id: {booking_id}')
    return jsonify({'result': 'error', 'msg': 'ID booking tidak valid.'})

#route ini menangani ketika terjadi kesalahan dalam pembayaran midtrans maka akan dibatalkan otomatis oleh sistem
@app.route('/booking_dibatalkan', methods=['POST'])
def booking_dibatalkan():
    booking_id = request.form.get('booking_id')
    logger.info(f'Cancel booking request received for booking_id: {booking_id}')
    
    try:
        object_id = ObjectId(booking_id)
        result_deluxe = db.deluxe_booking.update_one({'_id': object_id}, {'$set': {'status': 'dibatalkan'}})
        result_family = db.family_deluxe_booking.update_one({'_id': object_id}, {'$set': {'status': 'dibatalkan'}})
    except InvalidId:
        result_deluxe = db.deluxe_booking.update_one({'booking_code': booking_id}, {'$set': {'status': 'dibatalkan'}})
        result_family = db.family_deluxe_booking.update_one({'booking_code': booking_id}, {'$set': {'status': 'dibatalkan'}})

    if result_deluxe.modified_count > 0 or result_family.modified_count > 0:
        logger.info(f'Booking cancelled successfully for booking_id: {booking_id}')
        return jsonify({'result': 'success', 'msg': 'Booking berhasil dibatalkan.'})
    else:
        logger.error(f'Failed to cancel booking for booking_id: {booking_id}')
        return jsonify({'result': 'error', 'msg': 'Gagal membatalkan booking.'})


@app.route('/user/room/booking/deluxe-room/payment-success', methods=['GET', 'POST'])
def order_success():
    user_info = get_user_info()
    if user_info:
        return render_template('user/book/order_success.html', user_info=user_info)
    else:
        return redirect(url_for('login'))
    
@app.route('/user/room/booking/family-deluxe-room/payment-success', methods=['GET', 'POST'])
def order_family_success():
    user_info = get_user_info()
    if user_info:
        return render_template('user/book/order_success.html', user_info=user_info)
    else:
        return redirect(url_for('login'))

@app.route('/user/room/booking/family-deluxe-room', methods=['GET', 'POST'])
def user_family_deluxe_book():
    user_info = get_user_info()  # Function to get user information
    
    check_in_date_str = request.args.get('check_in_date', datetime.today().strftime('%Y-%m-%d'))
    
    check_in_date = datetime.strptime(check_in_date_str, '%Y-%m-%d')

    query_date = check_in_date.strftime('%d/%m/%Y')
    
    price_info = db.room_prices.find_one({'date': query_date, 'room_type': 'Family Deluxe'})
    if price_info:
        harga_normal = price_info.get('price', 0)
        harga_diskon = price_info.get('discount_price', 0)
    else:
        harga_normal = 0
        harga_diskon = 0
    
    # Ambil lama inap dari parameter URL atau gunakan nilai default 1 malam jika tidak ada
    lama_inap = int(request.args.get('lamaInap', '1'))
    
    check_out_date = check_in_date + timedelta(days=lama_inap)
    
    check_in_date_display_str = check_in_date.strftime('%d/%m/%Y')
    check_out_date_display_str = check_out_date.strftime('%d/%m/%Y')

    # Render template dengan informasi yang diperlukan
    if user_info:
        return render_template(
            'user/book/family_deluxe_book.html', 
            user_info=user_info, 
            check_in_date_display=check_in_date_display_str,  
            check_in_date=check_in_date_str,  
            check_out_date=check_out_date_display_str,
            harga_normal=harga_normal, 
            harga_diskon=harga_diskon, 
            lama_inap=lama_inap,
            format_currency=format_currency
        )
    else:
        return redirect(url_for('login'))

@app.route('/family_deluxe_save_booking', methods=['POST'])
def family_deluxe_save_booking():
    if request.method == 'POST':
        data = request.get_json()

        booking_code = data.get('bookingCode')
        nama_lengkap = data.get('namaLengkap')
        email = data.get('email')
        nomor_handphone = data.get('nomorHandphone')
        pesanan_untuk = data.get('pesananUntuk')
        guest_name = data.get('guestName')
        lama_inap = data.get('lamaInap')
        permintaan_khusus = data.get('permintaanKhusus')
        harga_normal = data.get('hargaNormal')
        harga_diskon = data.get('hargaDiskon')
        diskon = data.get('diskon')  # Tambahkan untuk mendapatkan data diskon dari frontend
        kode_voucher = data.get('kodeVoucher','')
        check_in_date = data.get('checkInDate')
        check_out_date = data.get('checkOutDate')
        created_at = datetime.now(wib)
        updated_at = datetime.now(wib)

        try:
            lama_inap = int(lama_inap)
        except ValueError:
            return jsonify({'error': 'Lama inap harus berupa angka.'}), 400

        harga_total = harga_diskon * lama_inap - diskon  # Perhitungan harga total setelah diskon

        booking_data = {
            'booking_code': booking_code,
            'tipe_kamar' : 'Family Deluxe',
            'nama_lengkap': nama_lengkap,
            'email': email,
            'nomor_handphone': nomor_handphone,
            'pesanan_untuk': pesanan_untuk,
            'guest_name': guest_name,
            'lama_inap': lama_inap,
            'permintaan_khusus': permintaan_khusus,
            'harga_normal': harga_normal,
            'harga_diskon': harga_diskon,
            'diskon': diskon,  # Simpan diskon yang diterapkan
            'harga_total': harga_total,
            'kode_voucher': kode_voucher,  # Simpan kode voucher yang digunakan
            'check_in_date': check_in_date,
            'check_out_date': check_out_date,
            'created_at': created_at,
            'updated_at': updated_at,
            'status': 'menunggu pembayaran'
        }

        db.family_deluxe_booking.insert_one(booking_data)

        return jsonify({'success': 'Booking berhasil disimpan!'}), 200

    return jsonify({'error': 'Metode tidak valid.'}), 400

@app.route('/user/room/booking/family-deluxe-room/payment-success', methods=['GET', 'POST'])
def family_order_success():
    user_info = get_user_info()
    if user_info:
        return render_template('user/book/order_success.html', user_info=user_info)
    else:
        return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

# Route admin
@app.route("/admin/login")
def login_admin():
    msg = request.args.get("msg")
    return render_template("admin/login/login.html", msg=msg)

@app.route('/admin/sign_in', methods=['POST'])
def admin_login():
    email = request.form.get('email')
    password = request.form.get('password')
    admin = db.admin.find_one({'email': email})
    recaptcha_response = request.form.get('g-recaptcha-response')
    # Verify reCAPTCHA
    secret_key =  os.getenv('SECRET_KEY')
    payload = {
        'secret': secret_key,
        'response': recaptcha_response
    }
    recaptcha_verify = requests.post('https://www.google.com/recaptcha/api/siteverify', data=payload)
    result = recaptcha_verify.json()
    if not result.get('success'):
        return jsonify({'result': 'fail', 'msg': 'Invalid reCAPTCHA. Please try again.'})
    if admin:
        hashed_password = hashlib.sha256(password.encode('utf-8')).hexdigest()
        if admin['password'] == hashed_password:
            session['logged_in'] = True
            session['email'] = email
            session['full_name'] = admin['full_name']
    
            return jsonify({'result': 'success', 'msg': 'Login berhasil'})
    return jsonify({'result': 'fail', 'msg': 'Password Salah!!!'})

@app.route('/admin/register', methods=['GET', 'POST'])
def admin_register():
    # Cek pengaturan
    setting = db.settings.find_one({'setting': 'register_enabled'})
    register_enabled = setting['value'] if setting else False
    
    if not register_enabled:
        return redirect(url_for('error_admin'))
    
    if request.method == 'POST':
        full_name = request.form.get('fullName')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirmPassword')
        role = request.form.get('role')

        if not full_name or not email or not password or not confirm_password:
            return jsonify({'error': 'Semua field yang diberi tanda * harus diisi.'}), 400

        if password != confirm_password:
            return jsonify({'error': 'Kata sandi dan konfirmasi kata sandi tidak cocok.'}), 400

        if db.users.find_one({'email': email}):
            return jsonify({'error': 'Email sudah digunakan.'}), 400

        hashed_password = hashlib.sha256(password.encode('utf-8')).hexdigest()
        profile_picture_url = url_for('static', filename='img/uploads/profile/profile_placeholder.png')

        user_data = {
            'full_name': full_name,
            'email': email,
            'password': hashed_password,
            'role': role,
            'profile_picture_url': profile_picture_url
        }
        db.admin.insert_one(user_data)
        return jsonify({'success': 'Pendaftaran berhasil!'}), 200

    return render_template('admin/register/register.html')

@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect(url_for('login_admin'))

def number_format(value):
    return "{:,.0f}".format(value)

# Register the filter in the Jinja environment
app.jinja_env.filters['number_format'] = number_format

@app.route('/admin/dashboard')
def admin_dashboard():
    admin_info = get_admin_info()
    if admin_info:
        # Mengambil data dari database
        # Data dari tabel deluxe_booking
        revenue_deluxe = sum(booking['harga_total'] for booking in db.deluxe_booking.find({'$or': [{'status': 'Pembayaran Berhasil'}, {'status': 'menunggu konfirmasi'}]}))
        total_guests_deluxe = db.deluxe_booking.count_documents({'status': 'Pembayaran Berhasil'})
        pending_payments_deluxe = db.deluxe_booking.count_documents({'status': 'menunggu pembayaran'})
        pending_confirmations_deluxe = db.deluxe_booking.count_documents({'status': 'menunggu konfirmasi'})
        accepted_bookings_deluxe = db.deluxe_booking.count_documents({'status': 'Pembayaran Berhasil'})
        rejected_bookings_deluxe = db.deluxe_booking.count_documents({'status': 'pesanan ditolak'})
        cancelled_bookings_deluxe = db.deluxe_booking.count_documents({'status': 'dibatalkan'})

        # Data dari tabel family_deluxe_booking
        revenue_family_deluxe = sum(booking['harga_total'] for booking in db.family_deluxe_booking.find({'$or': [{'status': 'Pembayaran Berhasil'}, {'status': 'menunggu konfirmasi'}]}))
        total_guests_family_deluxe = db.family_deluxe_booking.count_documents({'status': 'Pembayaran Berhasil'})
        pending_payments_family_deluxe = db.family_deluxe_booking.count_documents({'status': 'menunggu pembayaran'})
        pending_confirmations_family_deluxe = db.family_deluxe_booking.count_documents({'status': 'menunggu konfirmasi'})
        accepted_bookings_family_deluxe = db.family_deluxe_booking.count_documents({'status': 'Pembayaran Berhasil'})
        rejected_bookings_family_deluxe = db.family_deluxe_booking.count_documents({'status': 'pesanan ditolak'})
        cancelled_bookings_family_deluxe = db.family_deluxe_booking.count_documents({'status': 'dibatalkan'})

        # Menghitung pendapatan bulanan
        monthly_revenue = []
        for month in range(1, 13):
            start_date = datetime(2024, month, 1)
            if month == 12:
                end_date = datetime(2025, 1, 1)
            else:
                end_date = datetime(2024, month + 1, 1)
            monthly_sum = sum(booking['harga_total'] for booking in db.deluxe_booking.find({
                'status': 'pesanan diterima',
                'created_at': {
                    '$gte': start_date,
                    '$lt': end_date
                }
            }))
            monthly_revenue.append(monthly_sum)

        data = {
            'revenue': revenue_deluxe,
            'total_guests': total_guests_deluxe,
            'pending_payments': pending_payments_deluxe,
            'pending_confirmations': pending_confirmations_deluxe,
            'accepted_bookings': accepted_bookings_deluxe,
            'rejected_bookings': rejected_bookings_deluxe,
            'cancelled_bookings': cancelled_bookings_deluxe,
            'monthly_revenue': monthly_revenue,

            # Data dari tabel family_deluxe_booking
            'revenue_family_deluxe': revenue_family_deluxe,
            'total_guests_family_deluxe': total_guests_family_deluxe,
            'pending_payments_family_deluxe': pending_payments_family_deluxe,
            'pending_confirmations_family_deluxe': pending_confirmations_family_deluxe,
            'accepted_bookings_family_deluxe': accepted_bookings_family_deluxe,
            'rejected_bookings_family_deluxe': rejected_bookings_family_deluxe,
            'cancelled_bookings_family_deluxe': cancelled_bookings_family_deluxe
        }
        
        return render_template('admin/dashboard/dashboard.html', admin_info=admin_info, data=data)
    else:
        return redirect(url_for('login_admin'))
    
    
@app.route('/admin/profile', methods=['GET'])
def admin_profile():
    admin_info = get_admin_info()
    if admin_info:
        return render_template('admin/profile/profile.html', admin_info=admin_info)
    else:
        return redirect(url_for('login_admin'))

@app.route('/admin/profile/edit', methods=['GET', 'POST'])
def admin_edit_profile():
    admin_info = get_admin_info()

    if admin_info:  
        email = session['email']
        admin_info = db.admin.find_one({'email': email})

        if request.method == 'POST':
            full_name = request.form.get('fullName')
            phone_number = request.form.get('phoneNumber')
            birth_date = request.form.get('birthDate')
            gender = request.form.get('gender')
            address = request.form.get('address')
            city = request.form.get('city')
            region = request.form.get('region')
            postal_code = request.form.get('postalCode')

            db.admin.update_one(
                {'email': email},
                {'$set': {
                    'full_name': full_name,
                    'phone_number': phone_number,
                    'birth_date': birth_date,
                    'gender': gender,
                    'address': address,
                    'city': city,
                    'region': region,
                    'postal_code': postal_code
                }}
            )
            return redirect(url_for('admin_profile'))
        
        return render_template('admin/profile/edit_profile.html', admin_info=admin_info)
    else:
        return redirect(url_for('admin_login'))

@app.route('/admin/profile/upload_photo', methods=['POST'])
def admin_upload_photo():
    admin_info = get_admin_info()

    if admin_info:        
        email = session['email']
        if 'profile_picture' in request.files:
            profile_picture = request.files['profile_picture']
            if profile_picture:
                filename = secure_filename(profile_picture.filename)
                profile_picture_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                profile_picture.save(profile_picture_path)
                
                profile_picture_url = url_for('static', filename='img/uploads/profile/' + filename)
                db.admin.update_one(
                    {'email': email},
                    {'$set': {'profile_picture_url': profile_picture_url}}
                )
        return redirect(url_for('admin_profile'))
    else:
        return redirect(url_for('admin_login'))

@app.route('/admin/gallery/upload_photo', methods=['GET', 'POST'])
def admin_upload_gallery():
    admin_info = get_admin_info()
    if admin_info:        
        if request.method == 'POST':
            if 'gallery_picture' in request.files:
                gallery_picture = request.files['gallery_picture']
                if gallery_picture:
                    filename = secure_filename(gallery_picture.filename)
                    gallery_picture_path = os.path.join(app.config['UPLOAD_Gallery'], filename)
                    gallery_picture.save(gallery_picture_path)
                    
                    gallery_picture_url = url_for('static', filename='img/uploads/gallery/' + filename)
                    db.gallery.insert_one({'gallery_picture_url': gallery_picture_url})
                    flash('Gambar berhasil ditambahkan!', 'success')
                    return redirect(url_for('admin_gallery'))

        return render_template('admin/gallery/upload_gallery.html', admin_info=admin_info)
    else:
        return redirect(url_for('admin_login'))

@app.route('/admin/gallery', methods=['GET'])
def admin_gallery():
    admin_info = get_admin_info()
    if admin_info:
        page = int(request.args.get('page', 1))
        per_page = 5
        gallery = list(db.gallery.find().skip((page - 1) * per_page).limit(per_page))
        total_items = db.gallery.count_documents({})
        total_pages = (total_items + per_page - 1) // per_page
        return render_template('admin/gallery/gallery.html',admin_info=admin_info, gallery=gallery, page=page, total_pages=total_pages, total_items=total_items)
    else:
        return redirect(url_for('admin_login'))

@app.route('/admin/gallery/edit/<gallery_id>', methods=['GET', 'POST'])
def admin_edit_gallery(gallery_id):
    admin_info = get_admin_info()
    if admin_info:
        if request.method == 'POST':
            if 'gallery_picture' in request.files:
                gallery_picture = request.files['gallery_picture']
                if gallery_picture:
                    filename = secure_filename(gallery_picture.filename)
                    gallery_picture_path = os.path.join(app.config['UPLOAD_Gallery'], filename)
                    gallery_picture.save(gallery_picture_path)
                    
                    gallery_picture_url = url_for('static', filename='img/uploads/gallery/' + filename)
                    db.gallery.update_one({'_id': ObjectId(gallery_id)}, {'$set': {'gallery_picture_url': gallery_picture_url}})
        
        gallery_item = db.gallery.find_one({'_id': ObjectId(gallery_id)})
        return render_template('admin/gallery/edit_gallery.html', admin_info=admin_info, gallery_item=gallery_item)
    else:
        return redirect(url_for('admin_login'))

@app.route('/admin/delete_gallery', methods=['POST'])
def admin_delete_gallery():
    admin_info = get_admin_info()

    if admin_info:
        gallery_id = request.form.get('gallery_id')
        if gallery_id:
            result = db.gallery.delete_one({'_id': ObjectId(gallery_id)})
            if result.deleted_count > 0:
                return jsonify({'result': 'success'})
            else:
                return jsonify({'result': 'error', 'msg': 'Gagal menghapus foto.'})
        return jsonify({'result': 'error', 'msg': 'ID foto tidak valid.'})
    else:
        return redirect(url_for('admin_login'))
    
@app.route('/admin/bulk_delete_gallery', methods=['POST'])
def admin_bulk_delete_gallery():
    admin_info = get_admin_info()

    if admin_info:
        gallery_ids = request.form.getlist('gallery_ids[]')
        if gallery_ids:
            object_ids = [ObjectId(gallery_id) for gallery_id in gallery_ids]
            result = db.gallery.delete_many({'_id': {'$in': object_ids}})
            if result.deleted_count > 0:
                return jsonify({'result': 'success'})
            else:
                return jsonify({'result': 'error', 'msg': 'Gagal menghapus foto.'})
        return jsonify({'result': 'error', 'msg': 'Tidak ada ID foto yang valid.'})
    else:
        return redirect(url_for('admin_login'))
    
@app.route('/admin/user', methods=['GET'])
def admin_user():
    admin_info = get_admin_info()
    if admin_info:
        search_query = request.args.get('search')
        per_page = 5
        page = int(request.args.get('page', 1))
        
        if search_query:
            users = list(db.users.find({'email': {'$regex': search_query, '$options': 'i'}}).skip((page - 1) * per_page).limit(per_page))
            total_users = db.users.count_documents({'email': {'$regex': search_query, '$options': 'i'}})
        else:
            users = list(db.users.find().skip((page - 1) * per_page).limit(per_page))
            total_users = db.users.count_documents({})
        
        total_pages = (total_users + per_page - 1) // per_page
        return render_template('admin/user/user.html', users=users, admin_info=admin_info, page=page, total_pages=total_pages, total_users=total_users)
    else:
        return redirect(url_for('login_admin'))

@app.route('/admin/delete_user', methods=['POST'])
def admin_delete_user():
    admin_info = get_admin_info()
    if admin_info:
        user_id = request.form.get('user_id')
        if user_id:
            result = db.users.delete_one({'_id': ObjectId(user_id)})
            if result.deleted_count > 0:
                return jsonify({'result': 'success'})
            else:
                return jsonify({'result': 'error', 'msg': 'Gagal menghapus pengguna.'})
        return jsonify({'result': 'error', 'msg': 'ID pengguna tidak valid.'})
    else:
        return redirect(url_for('login_admin'))
    
@app.route('/admin/bulk_delete_users', methods=['POST'])
def admin_bulk_delete_users():
    admin_info = get_admin_info()
    if admin_info:
        user_ids = request.form.getlist('user_ids[]')
        if user_ids:
            object_ids = [ObjectId(user_id) for user_id in user_ids]
            result = db.users.delete_many({'_id': {'$in': object_ids}})
            if result.deleted_count > 0:
                return jsonify({'result': 'success'})
            else:
                return jsonify({'result': 'error', 'msg': 'Gagal menghapus pengguna.'})
        return jsonify({'result': 'error', 'msg': 'Tidak ada ID pengguna yang valid.'})
    else:
        return redirect(url_for('login_admin'))
    
@app.route('/admin/user/profile/<user_id>', methods=['GET', 'POST'])
def admin_edit_user_profile(user_id):
    if 'logged_in' in session:
        admin_info = get_admin_info()
        if admin_info:
            user_info = db.users.find_one({'_id': ObjectId(user_id)})

            if request.method == 'POST':
                full_name = request.form.get('fullName')
                phone_number = request.form.get('phoneNumber')
                birth_date = request.form.get('birthDate')
                gender = request.form.get('gender')
                address = request.form.get('address')
                city = request.form.get('city')
                region = request.form.get('region')
                postal_code = request.form.get('postalCode')

                db.users.update_one(
                    {'_id': ObjectId(user_id)},
                    {'$set': {
                        'full_name': full_name,
                        'phone_number': phone_number,
                        'birth_date': birth_date,
                        'gender': gender,
                        'address': address,
                        'city': city,
                        'region': region,
                        'postal_code': postal_code
                    }}
                )
                return redirect(url_for('admin_edit_user_profile', user_id=user_id))

            return render_template('admin/user/edit_user_profile.html', admin_info=admin_info, user_info=user_info)
        else:
            return redirect('/admin/login')
    else:
        return redirect('/admin/login')

@app.route('/admin/user/profile/<user_id>/upload_photo', methods=['POST'])
def admin_upload_user_photo(user_id):
    if 'logged_in' in session:
        admin_info = get_admin_info()
        if admin_info and 'profile_picture' in request.files:
            profile_picture = request.files['profile_picture']
            if profile_picture:
                filename = secure_filename(profile_picture.filename)
                profile_picture_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                profile_picture.save(profile_picture_path)
                
                profile_picture_url = url_for('static', filename='img/uploads/profile/' + filename)
                db.users.update_one(
                    {'_id': ObjectId(user_id)},
                    {'$set': {'profile_picture_url': profile_picture_url}}
                )
        return redirect(url_for('admin_edit_user_profile', user_id=user_id))
    else:
        return redirect(url_for('login_admin'))

def to_date_input_format(value):
    return datetime.strptime(value, '%d/%m/%Y').strftime('%Y-%m-%d')

app.jinja_env.filters['to_date_input_format'] = to_date_input_format

@app.route('/admin/room/edit/<room_id>', methods=['GET', 'POST'])
def admin_edit_room(room_id):
    if 'logged_in' in session:
        admin_info = get_admin_info()
        room = db.room_prices.find_one({'_id': ObjectId(room_id)})

        if request.method == 'POST':
            room_type = request.form.get('roomType')
            date = request.form.get('date')
            normal_price = request.form.get('price')
            discount_price = request.form.get('discount_price')
            stock = request.form.get('stock')

            # Convert stock to integer
            try:
                stock = int(stock)
            except ValueError:
                return jsonify({'error': 'Stock harus berupa angka.'}), 400

            # Convert prices to integer
            try:
                normal_price = int(normal_price)
                discount_price = int(discount_price)
            except ValueError:
                return jsonify({'error': 'Harga harus berupa angka.'}), 400

            # Convert date to datetime object and format it as DD/MM/YYYY
            try:
                date = datetime.strptime(date, '%Y-%m-%d').strftime('%d/%m/%Y')
            except ValueError:
                return jsonify({'error': 'Format tanggal salah.'}), 400

            db.room_prices.update_one(
                {'_id': ObjectId(room_id)},
                {'$set': {
                    'room_type': room_type,
                    'date': date,
                    'price': normal_price,
                    'discount_price': discount_price,
                    'stock': stock,
                    'updated_at': datetime.now(wib),
                }}
            )
            return redirect(url_for('admin_room'))

        # Ensure room_type is passed correctly to the template
        return render_template('admin/room/edit_room.html', admin_info=admin_info, room=room)
    else:
        return redirect(url_for('login_admin'))

@app.route('/admin/room/delete', methods=['POST'])
def admin_delete_room():
    admin_info = get_admin_info()
    if admin_info:
        room_id = request.form.get('room_id')
        if room_id:
            result = db.room_prices.delete_one({'_id': ObjectId(room_id)})
            if result.deleted_count > 0:
                return jsonify({'result': 'success'})
            else:
                return jsonify({'result': 'error', 'msg': 'Gagal menghapus kamar.'})
        return jsonify({'result': 'error', 'msg': 'ID kamar tidak valid.'})
    else:
        return redirect(url_for('login_admin'))
    
@app.route('/admin/bulk_delete_rooms', methods=['POST'])
def admin_bulk_delete_rooms():
    admin_info = get_admin_info()
    if admin_info:
        room_ids = request.form.getlist('room_ids[]')
        if room_ids:
            object_ids = [ObjectId(room_id) for room_id in room_ids]
            result = db.room_prices.delete_many({'_id': {'$in': object_ids}})
            if result.deleted_count > 0:
                return jsonify({'result': 'success'})
            else:
                return jsonify({'result': 'error', 'msg': 'Gagal menghapus kamar.'})
        return jsonify({'result': 'error', 'msg': 'Tidak ada ID kamar yang valid.'})
    else:
        return redirect(url_for('login_admin'))
    
@app.route('/admin/rooms', methods=['GET'])
def admin_room():
    admin_info = get_admin_info()
    if admin_info:
        search_query = request.args.get('search')
        room_type_filter = request.args.get('room_type')
        date_filter = request.args.get('date')
        per_page = 5
        page = int(request.args.get('page', 1))

        query = {}
        if search_query:
            query['type'] = {'$regex': search_query, '$options': 'i'}
        if room_type_filter:
            query['type'] = room_type_filter
        if date_filter:
            # Convert date to dd/mm/yyyy
            date_parts = date_filter.split('-')
            formatted_date = f"{date_parts[2]}/{date_parts[1]}/{date_parts[0]}"
            query['date'] = formatted_date

        rooms = list(db.room_prices.find(query)
                     .sort('created_at', -1)
                     .skip((page - 1) * per_page)
                     .limit(per_page))
        total_rooms = db.room_prices.count_documents(query)

        total_pages = (total_rooms + per_page - 1) // per_page
        return render_template('admin/room/room.html', rooms=rooms, admin_info=admin_info, page=page, total_pages=total_pages, total_rooms=total_rooms, format_currency=format_currency)
    else:
        return redirect(url_for('login_admin'))

@app.route('/admin/room/add', methods=['GET', 'POST'])
def admin_add_room():
    admin_info = get_admin_info()
    if admin_info:
        if request.method == 'POST':
            room_type = request.form.get('roomType')
            date = request.form.get('date')
            normal_price = request.form.get('price')
            discount_price = request.form.get('discount_price')
            stock = request.form.get('stock')

            # Convert stock to integer
            try:
                stock = int(stock)
            except ValueError:
                return jsonify({'error': 'Stock harus berupa angka.'}), 400

            # Convert prices to integer
            try:
                normal_price = int(normal_price)
                discount_price = int(discount_price)
            except ValueError:
                return jsonify({'error': 'Harga harus berupa angka.'}), 400

            # Convert date to datetime object and format it as DD/MM/YYYY
            try:
                date = datetime.strptime(date, '%Y-%m-%d').strftime('%d/%m/%Y')
            except ValueError:
                return jsonify({'error': 'Format tanggal salah.'}), 400

            new_room = {
                'room_type': room_type,
                'date': date,
                'price': normal_price,
                'discount_price': discount_price,
                'stock': stock,
                'created_at': datetime.now(wib),
                'updated_at': datetime.now(wib)
            }

            db.room_prices.insert_one(new_room)
            return redirect(url_for('admin_room'))
        
        return render_template('admin/room/add_room.html', admin_info=admin_info)
    else:
        return redirect(url_for('login_admin'))

@app.route('/admin/guest', methods=['GET'])
def admin_guest():
    admin_info = get_admin_info()
    if admin_info:
        search_query = request.args.get('search')
        booking_code_query = request.args.get('booking_code')
        date_query = request.args.get('date')
        entries_per_page = int(request.args.get('entries_per_page', 10))
        page = int(request.args.get('page', 1))

        query = {}
        if search_query:
            query['tipe_kamar'] = {'$regex': search_query, '$options': 'i'}
        if booking_code_query:
            query['booking_code'] = {'$regex': booking_code_query, '$options': 'i'}

        deluxe_guests = list(db.deluxe_booking.find(query)
                             .sort('created_at', -1)
                             .skip((page - 1) * entries_per_page)
                             .limit(entries_per_page))
        
        family_deluxe_guests = list(db.family_deluxe_booking.find(query)
                                    .sort('created_at', -1)
                                    .skip((page - 1) * entries_per_page)
                                    .limit(entries_per_page))

        guests = deluxe_guests + family_deluxe_guests

        for guest in guests:
            if isinstance(guest['created_at'], str):
                try:
                    guest['created_at'] = datetime.strptime(guest['created_at'], '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    guest['created_at'] = datetime.strptime(guest['created_at'], '%d/%m/%Y %H:%M:%S')

        guests = sorted(guests, key=lambda x: x['created_at'], reverse=True)

        total_deluxe_guests = db.deluxe_booking.count_documents(query)
        total_family_deluxe_guests = db.family_deluxe_booking.count_documents(query)
        total_guests = total_deluxe_guests + total_family_deluxe_guests

        total_pages = (total_guests + entries_per_page - 1) // entries_per_page

        return render_template('admin/guest/guest.html', 
                               guests=guests, 
                               admin_info=admin_info, 
                               page=page, 
                               total_pages=total_pages, 
                               total_guests=total_guests, 
                               entries_per_page=entries_per_page, 
                               format_currency=format_currency)
    else:
        return redirect(url_for('login_admin'))

@app.route('/admin/guest/delete/<guest_id>', methods=['POST'])
def admin_delete_guest(guest_id):
    if 'logged_in' in session:
        # Hapus dari deluxe_booking
        deluxe_result = db.deluxe_booking.delete_one({'_id': ObjectId(guest_id)})
        
        # Hapus dari family_deluxe_booking
        family_deluxe_result = db.family_deluxe_booking.delete_one({'_id': ObjectId(guest_id)})
        
        # Cek apakah ada data yang terhapus dari salah satu koleksi
        if deluxe_result.deleted_count > 0 or family_deluxe_result.deleted_count > 0:
            return jsonify({'result': 'success'})
        else:
            return jsonify({'result': 'error', 'message': 'Failed to delete guest'}), 400
    else:
        return jsonify({'result': 'error', 'message': 'Unauthorized'}), 401

def delete_all_guests():
    try:
        # Hapus dari deluxe_booking jika status menunggu pembayaran atau dibatalkan
        deluxe_result = db.deluxe_booking.delete_many({
            'status': {'$in': ['menunggu pembayaran', 'dibatalkan']}
        })

        # Hapus dari family_deluxe_booking jika status menunggu pembayaran atau dibatalkan
        family_deluxe_result = db.family_deluxe_booking.delete_many({
            'status': {'$in': ['menunggu pembayaran', 'dibatalkan']}
        })

        logging.debug(f"Deluxe deleted count: {deluxe_result.deleted_count}")
        logging.debug(f"Family Deluxe deleted count: {family_deluxe_result.deleted_count}")

        # Cek apakah ada data yang terhapus dari salah satu koleksi
        if deluxe_result.deleted_count > 0 or family_deluxe_result.deleted_count > 0:
            logging.info("Deleted guests successfully.")
        else:
            logging.warning("No matching guests found to delete.")
    except Exception as e:
        logging.error(f"Error: {e}")

# Scheduler untuk menjalankan delete_all_guests setiap satu menit
scheduler = BackgroundScheduler()
scheduler.add_job(func=delete_all_guests, trigger="interval", hours=5)
scheduler.start()

@app.route('/admin/guest/delete_all', methods=['POST'])
def delete_all_guests_route():
    try:
        delete_all_guests()
        return jsonify({'result': 'success'})
    except Exception as e:
        logging.error(f"Error: {e}")
        return jsonify({'result': 'error', 'message': 'An error occurred'}), 500

@app.route('/admin/guest/bulk_delete', methods=['POST'])
def admin_bulk_delete_guests():
    if 'logged_in' in session:
        guest_ids = request.json.get('guest_ids', [])
        if guest_ids:
            db.deluxe_booking.delete_many({'_id': {'$in': [ObjectId(guest_id) for guest_id in guest_ids]}})
            db.family_deluxe_booking.delete_many({'_id': {'$in': [ObjectId(guest_id) for guest_id in guest_ids]}})

            return jsonify({'result': 'success'})
        return jsonify({'result': 'error', 'message': 'No guests selected'}), 400
    else:
        return jsonify({'result': 'error', 'message': 'Unauthorized'}), 401

@app.route('/admin/guest/edit/<guest_id>', methods=['GET', 'POST'])
def admin_edit_guest(guest_id):
    if 'logged_in' in session:
        admin_info = get_admin_info()
        guest = db.deluxe_booking.find_one({'_id': ObjectId(guest_id)})

        if request.method == 'POST':
            booking_code = request.form.get('bookingCode')
            nama_lengkap = request.form.get('namaLengkap')
            email = request.form.get('email')
            nomor_handphone = request.form.get('nomorHandphone')
            pesanan_untuk = request.form.get('pesananUntuk')
            guest_name = request.form.get('guestName')
            lama_inap = request.form.get('lamaInap')
            harga_normal = request.form.get('hargaNormal')
            harga_diskon = request.form.get('hargaDiskon')
            harga_total = request.form.get('hargaTotal')
            check_in_date = request.form.get('checkInDate')
            check_out_date = request.form.get('checkOutDate')
            status = request.form.get('status')
            alasan_penolakan = request.form.get('alasan_penolakan')
            updated_at = datetime.now(wib)
            if status == 'pesanan ditolak' and not alasan_penolakan:
                return jsonify({'error': 'Alasan penolakan wajib diisi'}), 400
            # Convert numeric values
            try:
                lama_inap = int(lama_inap)
                harga_normal = float(harga_normal)
                harga_diskon = float(harga_diskon)
                harga_total = float(harga_total)
            except ValueError as e:
                return jsonify({'error': str(e)}), 400

            db.deluxe_booking.update_one(
                {'_id': ObjectId(guest_id)},
                {'$set': {
                    'booking_code': booking_code,
                    'nama_lengkap': nama_lengkap,
                    'email': email,
                    'nomor_handphone': nomor_handphone,
                    'pesanan_untuk': pesanan_untuk,
                    'guest_name': guest_name,
                    'lama_inap': lama_inap,
                    'harga_normal': harga_normal,
                    'harga_diskon': harga_diskon,
                    'harga_total': harga_total,
                    'check_in_date': check_in_date,
                    'check_out_date': check_out_date,
                    'status': status,
                    'alasan_penolakan': alasan_penolakan,
                    'updated_at': updated_at
                }}
            )
            return redirect(url_for('admin_guest'))

        return render_template('admin/guest/edit_guest.html', admin_info=admin_info, guest=guest)
    else:
        return redirect(url_for('login_admin'))

@app.route('/admin/guest/edit/familydlx/<guest_id>', methods=['GET', 'POST'])
def admin_edit_family_guest(guest_id):
    if 'logged_in' in session:
        admin_info = get_admin_info()
        guest = db.family_deluxe_booking.find_one({'_id': ObjectId(guest_id)})

        if request.method == 'POST':
            booking_code = request.form.get('bookingCode')
            nama_lengkap = request.form.get('namaLengkap')
            email = request.form.get('email')
            nomor_handphone = request.form.get('nomorHandphone')
            pesanan_untuk = request.form.get('pesananUntuk')
            guest_name = request.form.get('guestName')
            lama_inap = request.form.get('lamaInap')
            harga_normal = request.form.get('hargaNormal')
            harga_diskon = request.form.get('hargaDiskon')
            harga_total = request.form.get('hargaTotal')
            check_in_date = request.form.get('checkInDate')
            check_out_date = request.form.get('checkOutDate')
            status = request.form.get('status')
            alasan_penolakan = request.form.get('alasan_penolakan')
            updated_at = datetime.now(wib)

            if status == 'pesanan ditolak' and not alasan_penolakan:
                return jsonify({'error': 'Alasan penolakan wajib diisi'}), 400
            # Convert numeric values
            try:
                lama_inap = int(lama_inap)
                harga_normal = float(harga_normal)
                harga_diskon = float(harga_diskon)
                harga_total = float(harga_total)
            except ValueError as e:
                return jsonify({'error': str(e)}), 400

            db.family_deluxe_booking.update_one(
                {'_id': ObjectId(guest_id)},
                {'$set': {
                    'booking_code': booking_code,
                    'nama_lengkap': nama_lengkap,
                    'email': email,
                    'nomor_handphone': nomor_handphone,
                    'pesanan_untuk': pesanan_untuk,
                    'guest_name': guest_name,
                    'lama_inap': lama_inap,
                    'harga_normal': harga_normal,
                    'harga_diskon': harga_diskon,
                    'harga_total': harga_total,
                    'check_in_date': check_in_date,
                    'check_out_date': check_out_date,
                    'status': status,
                    'alasan_penolakan': alasan_penolakan,
                    'updated_at': updated_at
                }}
            )
            return redirect(url_for('admin_guest'))

        return render_template('admin/guest/edit_family_guest.html', admin_info=admin_info, guest=guest)
    else:
        return redirect(url_for('login_admin'))

@app.route('/admin/faq', methods=['GET'])
def admin_faq():
    admin_info = get_admin_info()
    if admin_info:
        search_query = request.args.get('search')
        per_page = 5
        page = int(request.args.get('page', 1))

        if search_query:
            faqs = list(db.faqs.find({'question': {'$regex': search_query, '$options': 'i'}}).skip((page - 1) * per_page).limit(per_page))
            total_faqs = db.faqs.count_documents({'question': {'$regex': search_query, '$options': 'i'}})
        else:
            faqs = list(db.faqs.find().skip((page - 1) * per_page).limit(per_page))
            total_faqs = db.faqs.count_documents({})

        total_pages = (total_faqs + per_page - 1) // per_page
        return render_template('admin/faq/faq.html', faqs=faqs, admin_info=admin_info, page=page, total_pages=total_pages, total_faqs=total_faqs)
    else:
        return redirect(url_for('login_admin'))

@app.route('/admin/add_faq', methods=['GET', 'POST'])
def admin_add_faq():
    admin_info = get_admin_info()
    if admin_info:
        if request.method == 'POST':
            question = request.form['question']
            answer = request.form['answer']
            db.faqs.insert_one({'pertanyaan': question, 'jawaban': answer, 'created_at': datetime.utcnow()})
            return redirect(url_for('admin_faq'))
        return render_template('admin/faq/add_faq.html', admin_info=admin_info)
    else:
        return redirect(url_for('login_admin'))

@app.route('/admin/edit_faq/<faq_id>', methods=['GET', 'POST'])
def admin_edit_faq(faq_id):
    admin_info = get_admin_info()
    if admin_info:
        faq = db.faqs.find_one({'_id': ObjectId(faq_id)})
        if request.method == 'POST':
            question = request.form['question']
            answer = request.form['answer']
            db.faqs.update_one({'_id': ObjectId(faq_id)}, {'$set': {'pertanyaan': question, 'jawaban': answer}})
            return redirect(url_for('admin_faq'))
        return render_template('admin/faq/edit_faq.html', faq=faq, admin_info=admin_info)
    else:
        return redirect(url_for('login_admin'))

@app.route('/admin/delete_faq', methods=['POST'])
def admin_delete_faq():
    admin_info = get_admin_info()
    if admin_info:
        faq_id = request.form.get('faq_id')
        if faq_id:
            result = db.faqs.delete_one({'_id': ObjectId(faq_id)})
            if result.deleted_count > 0:
                return jsonify({'result': 'success'})
            else:
                return jsonify({'result': 'error', 'msg': 'Gagal menghapus pertanyaan.'})
        return jsonify({'result': 'error', 'msg': 'ID pertanyaan tidak valid.'})
    else:
        return redirect(url_for('login_admin'))

@app.route('/admin/bulk_delete_faq', methods=['POST'])
def admin_bulk_delete_faq():
    admin_info = get_admin_info()
    if admin_info:
        faq_ids = request.form.getlist('faq_ids[]')
        if faq_ids:
            object_ids = [ObjectId(faq_id) for faq_id in faq_ids]
            result = db.faqs.delete_many({'_id': {'$in': object_ids}})
            if result.deleted_count > 0:
                return jsonify({'result': 'success'})
            else:
                return jsonify({'result': 'error', 'msg': 'Gagal menghapus pertanyaan.'})
        return jsonify({'result': 'error', 'msg': 'Tidak ada ID pertanyaan yang valid.'})
    else:
        return redirect(url_for('login_admin'))


#route diskon
def format_date(date_str):
    return datetime.strptime(date_str, '%Y-%m-%d').strftime('%d/%m/%Y')

@app.route('/admin/discount', methods=['GET'])
def admin_discount():
    admin_info = get_admin_info()
    if admin_info:
        search_query = request.args.get('search')
        per_page = 10
        page = int(request.args.get('page', 1))

        if search_query:
            discounts = list(db.discounts.find({'kode': {'$regex': search_query, '$options': 'i'}}).skip((page - 1) * per_page).limit(per_page))
            total_discounts = db.discounts.count_documents({'kode': {'$regex': search_query, '$options': 'i'}})
        else:
            discounts = list(db.discounts.find().skip((page - 1) * per_page).limit(per_page))
            total_discounts = db.discounts.count_documents({})

        # Mengambil data diskon dari booking yang sudah berhasil
        deluxe_bookings = list(db.deluxe_booking.find({'status': 'Pembayaran Berhasil'}))
        family_deluxe_bookings = list(db.family_deluxe_booking.find({'status': 'Pembayaran Berhasil'}))

        # Menghitung total diskon dan jumlah penggunaan diskon
        used_discounts = {}
        usage_counts = {}
        for booking in deluxe_bookings + family_deluxe_bookings:
            kode_voucher = booking.get('kode_voucher')
            if kode_voucher:
                if kode_voucher not in used_discounts:
                    used_discounts[kode_voucher] = 0
                    usage_counts[kode_voucher] = 0
                used_discounts[kode_voucher] += booking.get('diskon', 0)
                usage_counts[kode_voucher] += 1

        # Menambahkan informasi diskon yang telah digunakan ke diskon yang ditemukan
        for discount in discounts:
            discount['used'] = used_discounts.get(discount['kode'], 0)
            discount['usage_count'] = usage_counts.get(discount['kode'], 0)

        total_pages = (total_discounts + per_page - 1) // per_page
        return render_template('admin/discount/discount.html', discounts=discounts, admin_info=admin_info, page=page, total_pages=total_pages, total_discounts=total_discounts, format_currency=format_currency)
    else:
        return redirect(url_for('login_admin'))
    
@app.route('/mengurangi_kuota', methods=['POST'])
def mengurangi_kuota():
    data = request.get_json()
    kode_voucher = data.get('kodeVoucher')  # Sesuaikan dengan nama dari HTML

    app.logger.info(f"Request untuk mengurangi kuota voucher: {data}")

    # Log kode voucher yang diterima
    app.logger.info(f"Kode voucher yang diterima: {kode_voucher}")

    # Log semua kode voucher di database
    all_vouchers = db.discounts.find()
    app.logger.info("All vouchers in database:")
    for voucher in all_vouchers:
        app.logger.info(voucher)

    voucher = db.discounts.find_one({'kode': kode_voucher})
    if not voucher:
        app.logger.error('Kode voucher tidak valid.')
        return jsonify({'success': False, 'message': 'Kode voucher tidak valid.'}), 400

    if voucher['kuota'] <= 0:
        app.logger.error('Kuota voucher telah habis.')
        return jsonify({'success': False, 'message': 'Kuota voucher telah habis.'}), 400

    db.discounts.update_one(
        {'kode': kode_voucher},
        {'$inc': {'kuota': -1}}
    )

    app.logger.info('Kuota voucher berhasil dikurangi.')
    return jsonify({'success': True, 'message': 'Kuota voucher berhasil dikurangi.'}), 200

@app.route('/admin/discount/add', methods=['GET', 'POST'])
def admin_add_discount():
    admin_info = get_admin_info()
    if admin_info:
        if request.method == 'POST':
            jenis_diskon = request.form['jenis_diskon']
            discount_data = {
                'kode': request.form['kode'],
                'jenis_diskon': jenis_diskon,
                'diskon_maks': int(request.form['diskon_maks']),
                'kuota_awal': int(request.form['kuota_awal']),
                'kuota': int(request.form['kuota']),
                'tanggal_mulai': format_date(request.form['tanggal_mulai']),
                'tanggal_akhir': format_date(request.form['tanggal_akhir']),
                'deskripsi': request.form['deskripsi'],
                'tipe_kamar': request.form['tipe_kamar']
            }

            if jenis_diskon == 'persen':
                discount_data['persentase'] = int(request.form['persentase'])
            elif jenis_diskon == 'potongan':
                discount_data['potongan'] = int(request.form['potongan'])

            db.discounts.insert_one(discount_data)
            return redirect(url_for('admin_discount'))
        return render_template('admin/discount/add_discount.html', admin_info=admin_info)
    else:
        return redirect(url_for('login_admin'))

@app.route('/admin/discount/edit/<discount_id>', methods=['GET', 'POST'])
def admin_edit_discount(discount_id):
    admin_info = get_admin_info()
    if admin_info:
        discount = db.discounts.find_one({'_id': ObjectId(discount_id)})
        if not discount:
            return redirect(url_for('admin_discount'))

        if request.method == 'POST':
            jenis_diskon = request.form['jenis_diskon']
            discount_data = {
                'kode': request.form['kode'],
                'jenis_diskon': jenis_diskon,
                'diskon_maks': int(request.form['diskon_maks']),
                'kuota_awal': int(request.form['kuota_awal']),
                'kuota': int(request.form['kuota']),
                'tanggal_mulai': datetime.strptime(request.form['tanggal_mulai'], "%Y-%m-%d").strftime("%d/%m/%Y"),
                'tanggal_akhir': datetime.strptime(request.form['tanggal_akhir'], "%Y-%m-%d").strftime("%d/%m/%Y"),
                'deskripsi': request.form['deskripsi'],
                'tipe_kamar': request.form['tipe_kamar']
            }

            if jenis_diskon == 'persen':
                discount_data['persentase'] = int(request.form['persentase'])
            elif jenis_diskon == 'potongan':
                discount_data['potongan'] = int(request.form['potongan'])

            db.discounts.update_one({'_id': ObjectId(discount_id)}, {'$set': discount_data})
            return redirect(url_for('admin_discount'))

        # Convert date to the format 'YYYY-MM-DD' for the form input
        discount['tanggal_mulai'] = datetime.strptime(discount['tanggal_mulai'], "%d/%m/%Y").strftime("%Y-%m-%d")
        discount['tanggal_akhir'] = datetime.strptime(discount['tanggal_akhir'], "%d/%m/%Y").strftime("%Y-%m-%d")

        return render_template('admin/discount/edit_discount.html', admin_info=admin_info, discount=discount)
    else:
        return redirect(url_for('login_admin'))
    
@app.route('/admin/discount/delete', methods=['POST'])
def admin_delete_discount():
    admin_info = get_admin_info()
    if admin_info:
        discount_id = request.form.get('discount_id')
        if discount_id:
            result = db.discounts.delete_one({'_id': ObjectId(discount_id)})
            if result.deleted_count > 0:
                return jsonify({'result': 'success'})
            else:
                return jsonify({'result': 'error', 'msg': 'Gagal menghapus diskon.'})
        return jsonify({'result': 'error', 'msg': 'ID diskon tidak valid.'})
    else:
        return redirect(url_for('login_admin'))

@app.route('/admin/discount/bulk_delete', methods=['POST'])
def admin_bulk_delete_discounts():
    admin_info = get_admin_info()
    if admin_info:
        discount_ids = request.form.getlist('discount_ids[]')
        if discount_ids:
            object_ids = [ObjectId(discount_id) for discount_id in discount_ids]
            result = db.discounts.delete_many({'_id': {'$in': object_ids}})
            if result.deleted_count > 0:
                return jsonify({'result': 'success'})
            else:
                return jsonify({'result': 'error', 'msg': 'Gagal menghapus beberapa atau semua diskon.'})
        return jsonify({'result': 'error', 'msg': 'Tidak ada ID diskon yang valid.'})
    else:
        return redirect(url_for('login_admin'))

#route team member
@app.route('/admin/teamMember', methods=['GET'])
def admin_teamMember():
    admin_info = get_admin_info()
    if admin_info:
        search_query = request.args.get('search')
        per_page = 5
        page = int(request.args.get('page', 1))

        if search_query:
            team_members = list(db.teamMember.find({'name': {'$regex': search_query, '$options': 'i'}}).skip((page - 1) * per_page).limit(per_page))
            total_team_members = db.teamMember.count_documents({'name': {'$regex': search_query, '$options': 'i'}})
        else:
            team_members = list(db.teamMember.find().skip((page - 1) * per_page).limit(per_page))
            total_team_members = db.teamMember.count_documents({})

        total_pages = (total_team_members + per_page - 1) // per_page
        return render_template('admin/teamMember/teamMember.html', team_members=team_members, admin_info=admin_info, page=page, total_pages=total_pages, total_team_members=total_team_members)
    else:
        return redirect(url_for('login_admin'))


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}

@app.route('/admin/add_teamMember', methods=['GET', 'POST'])
def admin_add_team_member():
    admin_info = get_admin_info()
    if admin_info:
        if request.method == 'POST':
            name = request.form['name']
            role = request.form['role']
            institution = request.form['institution']
            instagram = request.form['instagram']
            linkedin = request.form['linkedin']

            if 'image' not in request.files:
                flash('Tidak ada file gambar yang diunggah', 'danger')
                return redirect(request.url)
            file = request.files['image']
            if file.filename == '':
                flash('Tidak ada file gambar yang dipilih', 'danger')
                return redirect(request.url)
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_teamMember'], filename)
                file.save(file_path)
                file_url = url_for('static', filename='img/uploads/teamMembers/' + filename)

                db.teamMember.insert_one({
                    'nama': name,
                    'role': role,
                    'universitas': institution,
                    'profile': file_url,
                    'link_instagram': instagram,
                    'link_linkedin': linkedin,
                    'created_at': datetime.utcnow()
                })
                flash('Team member berhasil ditambahkan!', 'success')
                return redirect(url_for('admin_teamMember'))
            else:
                flash('File tidak diperbolehkan', 'danger')
        return render_template('admin/teamMember/add_teamMember.html', admin_info=admin_info)
    else:
        return redirect(url_for('login_admin'))


@app.route('/admin/edit_teamMember/<team_member_id>', methods=['GET', 'POST'])
def admin_edit_team_member(team_member_id):
    admin_info = get_admin_info()
    if admin_info:
        team_member = db.teamMember.find_one({'_id': ObjectId(team_member_id)})
        if request.method == 'POST':
            name = request.form['name']
            role = request.form['role']
            institution = request.form['institution']
            instagram = request.form['instagram']
            linkedin = request.form['linkedin']
            current_image = request.form['current_image']

            # Handle file upload
            if 'image' in request.files:
                file = request.files['image']
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(app.config['UPLOAD_teamMember'], filename)
                    file.save(file_path)
                    image_url = url_for('static', filename='img/uploads/teamMembers/' + filename)
                else:
                    image_url = current_image
            else:
                image_url = current_image

            db.teamMember.update_one(
                {'_id': ObjectId(team_member_id)},
                {'$set': {
                    'nama': name,
                    'role': role,
                    'universitas': institution,
                    'profile': image_url,
                    'link_instagram': instagram,
                    'link_linkedin': linkedin
                }}
            )
            flash('Team member berhasil diperbarui!', 'success')
            return redirect(url_for('admin_teamMember'))

        return render_template('admin/teamMember/edit_teamMember.html', team_member=team_member, admin_info=admin_info)
    else:
        return redirect(url_for('login_admin'))

@app.route('/admin/delete_teamMember', methods=['POST'])
def admin_delete_team_member():
    team_member_id = request.form['team_member_id']
    db.teamMember.delete_one({'_id': ObjectId(team_member_id)})
    return jsonify({'result': 'success'})

@app.route('/admin/bulk_delete_teamMember', methods=['POST'])
def admin_bulk_delete_team_member():
    team_member_ids = request.form.getlist('team_member_ids[]')
    for team_member_id in team_member_ids:
        db.teamMember.delete_one({'_id': ObjectId(team_member_id)})
    return jsonify({'result': 'success'})


#ini route untuk setting
@app.route('/admin/settings', methods=['GET', 'POST'])
def admin_settings():
    admin_info = get_admin_info()
    if admin_info:
        if request.method == 'POST':
            register_enabled = request.form.get('registerEnabled') == 'active'
            login_enabled = request.form.get('loginEnabled') == 'active'
            team_member_enabled = request.form.get('teamMemberEnabled') == 'active'
            
            # Save settings to database
            db.settings.update_one({'setting': 'register_enabled'}, {'$set': {'value': register_enabled}}, upsert=True)
            db.settings.update_one({'setting': 'login_enabled'}, {'$set': {'value': login_enabled}}, upsert=True)
            db.settings.update_one({'setting': 'team_member_enabled'}, {'$set': {'value': team_member_enabled}}, upsert=True)
            
            return redirect(url_for('admin_settings'))

        # Fetch settings from database
        register_setting = db.settings.find_one({'setting': 'register_enabled'})
        login_setting = db.settings.find_one({'setting': 'login_enabled'})
        team_member_setting = db.settings.find_one({'setting': 'team_member_enabled'})
        
        register_enabled = register_setting['value'] if register_setting else None
        login_enabled = login_setting['value'] if login_setting else None
        team_member_enabled = team_member_setting['value'] if team_member_setting else None
        
        return render_template('admin/settings/settings.html', register_enabled=register_enabled, login_enabled=login_enabled, team_member_enabled=team_member_enabled, admin_info=admin_info)
    else:
        return redirect(url_for('login_admin'))

@app.route('/admin/send_email', methods=['GET', 'POST'])
def admin_send_email():
    admin_info = get_admin_info()
    if admin_info:
        if request.method == 'POST':
            selected_emails = request.form.getlist('selectedEmails')
            send_to_all = request.form.get('sendToAll')
            email_content = request.form.get('emailContent')
            kode_voucher = request.form.get('kodeVoucher')
            email_header = request.form.get('emailHeader')

            logging.info('Processing email send request...')
            logging.info(f'Selected emails: {selected_emails}')
            logging.info(f'Send to all: {send_to_all}')
            logging.info(f'Email content: {email_content}')
            logging.info(f'Kode voucher: {kode_voucher}')
            logging.info(f'Email header: {email_header}')

            recipients = []
            if send_to_all:
                recipients = [user['email'] for user in db.users.find()]
                logging.info('Sending to all users')
            else:
                recipients = selected_emails
                logging.info('Sending to selected users')

            # Upload the image if it exists
            file_url = ''
            if 'emailImage' in request.files:
                file = request.files['emailImage']
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(app.config['UPLOAD_email'], filename)
                    file.save(file_path)
                    file_url = url_for('static', filename='img/uploads/emails/' + filename, _external=True)

            # Send emails and save to database
            for email in recipients:
                user = db.users.find_one({'email': email})
                if user:
                    full_name = user['full_name']
                    try:
                        send_promotional_email(email, full_name, email_content, kode_voucher, email_header, file_url)
                        logging.info(f"Email sent to {email} with voucher {kode_voucher}")

                        # Save email record to the database
                        email_record = {
                            'email': email,
                            'full_name': full_name,
                            'kode_voucher': kode_voucher,
                            'email_header': email_header,
                            'email_content': email_content,
                            'image_url': file_url,
                            'sent_at': datetime.utcnow()
                        }
                        db.email_promotions.insert_one(email_record)

                    except Exception as e:
                        logging.error(f"Error sending email to {email}: {e}")

            return redirect(url_for('admin_send_email'))

        users = list(db.users.find())
        discounts = list(db.discounts.find())
        logging.info('Loaded users and discounts for email send form')
        return render_template('admin/email/send_email.html', admin_info=admin_info, users=users, discounts=discounts)
    else:
        logging.warning('Unauthorized access attempt to /admin/send_email')
        return redirect(url_for('login_admin'))

@app.route('/admin/search_users', methods=['GET'])
def admin_search_users():
    email_query = request.args.get('email', '')
    if email_query:
        matched_users = list(db.users.find({'email': {'$regex': email_query, '$options': 'i'}}, {'_id': 0, 'email': 1}))
        return jsonify(matched_users)
    return jsonify([])

def send_promotional_email(email, full_name, content, kode_voucher, email_header, image_url):
    msg = Message('Promosi Spesial dari Hotel Telaga Mas', recipients=[email])
    msg.html = render_template('admin/email/promosi_email.html', full_name=full_name, kode_voucher=kode_voucher, content=content, email_header=email_header, image_url=image_url)
    mail.send(msg)

@app.context_processor
def inject_team_member_setting():
    setting = db.settings.find_one({'setting': 'team_member_enabled'})
    team_member_enabled = setting['value'] if setting else False
    return dict(team_member_enabled=team_member_enabled)

@app.route('/error/admin')
def error_admin():
    return render_template('error_page/error_setting.html', message="Registrasi admin dinonaktifkan")

if __name__ == '__main__':
    app.run("0.0.0.0", port=5000, debug=True)
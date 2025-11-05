from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import openai
import os
import datetime
import logging

# Tambahan untuk rate limiting (install via pip install flask-limiter)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

app = Flask(__name__)
app.config['SECRET_KEY'] = 'super-secret-key'  # Ganti dengan os.getenv untuk production
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///coding_ai.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Rate limiter: 10 request per menit per IP untuk API routes
limiter = Limiter(app, key_func=get_remote_address, default_limits=["10 per minute"])

# API Key: DIMASUKKAN SEBAGAI HARDCODE (TIDAK AMAN - GANTI KE ENV VAR!)
openai.api_key = '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'

# Logging setup
logging.basicConfig(level=logging.INFO)

# -------------------- Models --------------------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    is_premium = db.Column(db.Boolean, default=False)
    codes = db.relationship('CodeHistory', backref='user', lazy=True)

class CodeHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    prompt = db.Column(db.Text, nullable=False)
    code = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# -------------------- Routes --------------------
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Login gagal! Username atau password salah.', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        if User.query.filter_by(username=username).first():
            flash('Username sudah terpakai!', 'warning')
            return redirect(url_for('register'))
        new_user = User(username=username, password=password)
        db.session.add(new_user)
        db.session.commit()
        flash('Registrasi berhasil! Silakan login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Berhasil logout!', 'success')
    return redirect(url_for('home'))

@app.route('/dashboard')
@login_required
def dashboard():
    codes = CodeHistory.query.filter_by(user_id=current_user.id).order_by(CodeHistory.timestamp.desc()).all()
    return render_template('dashboard.html', codes=codes)

@app.route('/upgrade')
@login_required
def upgrade():
    current_user.is_premium = True
    db.session.commit()
    flash('Upgrade ke Premium berhasil!', 'success')
    return redirect(url_for('dashboard'))

# -------------------- OpenAI API Functions --------------------
def openai_request(prompt, system_prompt="You are a coding assistant.", temperature=0.7, max_tokens=1500):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens,
            temperature=temperature
        )
        return response.choices[0].message['content'].strip()
    except openai.error.OpenAIError as e:
        logging.error(f"OpenAI Error: {str(e)}")
        return f"Error: {str(e)}"
    except Exception as e:
        logging.error(f"Unexpected Error: {str(e)}")
        return "Unexpected error occurred."

# -------------------- API Routes (dengan rate limiting) --------------------
@app.route('/generate_code', methods=['POST'])
@login_required
@limiter.limit("5 per minute")
def generate_code():
    if not current_user.is_premium:
        return jsonify({'error': 'Upgrade ke Premium dulu!'}), 403
    data = request.json
    prompt = data.get('prompt', '')
    lang = data.get('lang', 'python')
    if not prompt:
        return jsonify({'error': 'Prompt diperlukan'}), 400
    full_prompt = f"Generate {lang} code for: {prompt}"
    code = openai_request(full_prompt, system_prompt="You are a premium coding assistant. Generate clean, efficient code.")
    new_code = CodeHistory(user_id=current_user.id, prompt=prompt, code=code)
    db.session.add(new_code)
    db.session.commit()
    return jsonify({'code': code})

@app.route('/fix_code', methods=['POST'])
@login_required
@limiter.limit("5 per minute")
def fix_code():
    if not current_user.is_premium:
        return jsonify({'error': 'Upgrade ke Premium dulu!'}), 403
    data = request.json
    code = data.get('code', '')
    error = data.get('error', '')
    if not code:
        return jsonify({'error': 'Kode diperlukan'}), 400
    prompt = f"Fix this code: {code}. Error: {error}. Explain the fix."
    fixed = openai_request(prompt, system_prompt="Debug and fix code, provide clear explanation.", temperature=0.5)
    return jsonify({'fixed_code': fixed})

@app.route('/review_code', methods=['POST'])
@login_required
@limiter.limit("5 per minute")
def review_code():
    if not current_user.is_premium:
        return jsonify({'error': 'Upgrade ke Premium dulu!'}), 403
    data = request.json
    code = data.get('code', '')
    if not code:
        return jsonify({'error': 'Kode diperlukan'}), 400
    prompt = f"Review this code for best practices, security, optimization, and maintainability: {code}"
    review = openai_request(prompt)
    return jsonify({'review': review})

@app.route('/optimize_code', methods=['POST'])
@login_required
@limiter.limit("5 per minute")
def optimize_code():
    if not current_user.is_premium:
        return jsonify({'error': 'Upgrade ke Premium dulu!'}), 403
    data = request.json
    code = data.get('code', '')
    if not code:
        return jsonify({'error': 'Kode diperlukan'}), 400
    prompt = f"Optimize this code for performance and readability: {code}"
    optimized = openai_request(prompt, system_prompt="Optimize code for speed, memory, and readability.")
    return jsonify({'optimized_code': optimized})

@app.route('/refactor_code', methods=['POST'])
@login_required
@limiter.limit("5 per minute")
def refactor_code():
    if not current_user.is_premium:
        return jsonify({'error': 'Upgrade ke Premium dulu!'}), 403
    data = request.json
    code = data.get('code', '')
    if not code:
        return jsonify({'error': 'Kode diperlukan'}), 400
    prompt = f"Refactor this code for better structure and readability: {code}"
    refactored = openai_request(prompt, system_prompt="Refactor code for improved structure.")
    return jsonify({'refactored_code': refactored})

@app.route('/chat', methods=['POST'])
@login_required
@limiter.limit("10 per minute")
def chat():
    if not current_user.is_premium:
        return jsonify({'error': 'Upgrade ke Premium dulu!'}), 403
    data = request.json
    message = data.get('message', '')
    if not message:
        return jsonify({'error': 'Pesan diperlukan'}), 400
    response = openai_request(message, system_prompt="You are a helpful coding assistant for quick chats.")
    return jsonify({'response': response})

@app.route('/get_history', methods=['GET'])
@login_required
def get_history():
    codes = CodeHistory.query.filter_by(user_id=current_user.id).order_by(CodeHistory.timestamp.desc()).all()
    history = [{'id': c.id, 'prompt': c.prompt, 'code': c.code, 'timestamp': c.timestamp.isoformat()} for c in codes]
    return jsonify({'codes': history})

# -------------------- Run App --------------------
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)

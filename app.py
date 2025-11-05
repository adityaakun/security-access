from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import openai
import os
import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///coding_ai.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

openai.api_key = os.getenv('OPENAI_API_KEY', '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')

# Model Database
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

# Routes
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
        flash('Login gagal!')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        new_user = User(username=username, password=password)
        db.session.add(new_user)
        db.session.commit()
        flash('Registrasi berhasil!')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/dashboard')
@login_required
def dashboard():
    if not current_user.is_premium:
        return redirect(url_for('upgrade'))
    codes = CodeHistory.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard.html', codes=codes)

@app.route('/upgrade')
@login_required
def upgrade():
    # Simulasi payment
    current_user.is_premium = True
    db.session.commit()
    flash('Upgrade ke Premium berhasil!')
    return redirect(url_for('dashboard'))

@app.route('/generate_code', methods=['POST'])
@login_required
def generate_code():
    if not current_user.is_premium:
        return jsonify({'error': 'Upgrade ke Premium dulu!'}), 403
    data = request.json
    prompt = data.get('prompt', '')
    lang = data.get('lang', 'python')
    if not prompt:
        return jsonify({'error': 'Prompt diperlukan'}), 400
    
    full_prompt = f"Generate {lang} code for: {prompt}"
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a premium coding assistant. Generate clean, efficient code."},
                {"role": "user", "content": full_prompt}
            ],
            max_tokens=1500,
            temperature=0.7
        )
        code = response.choices[0].message['content'].strip()
        # Simpan ke history
        new_code = CodeHistory(user_id=current_user.id, prompt=prompt, code=code)
        db.session.add(new_code)
        db.session.commit()
        return jsonify({'code': code})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/fix_code', methods=['POST'])
@login_required
def fix_code():
    if not current_user.is_premium:
        return jsonify({'error': 'Upgrade ke Premium dulu!'}), 403
    data = request.json
    code = data.get('code', '')
    error = data.get('error', '')
    if not code:
        return jsonify({'error': 'Kode diperlukan'}), 400
    
    prompt = f"Fix this code: {code}. Error: {error}. Provide corrected code and explanation."
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Debug and fix code, explain changes."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1500,
            temperature=0.5
        )
        fixed = response.choices[0].message['content'].strip()
        return jsonify({'fixed_code': fixed})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/review_code', methods=['POST'])
@login_required
def review_code():
    if not current_user.is_premium:
        return jsonify({'error': 'Upgrade ke Premium dulu!'}), 403
    data = request.json
    code = data.get('code', '')
    if not code:
        return jsonify({'error': 'Kode diperlukan'}), 400
    
    prompt = f"Review this code for best practices, security, and improvements: {code}"
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Provide detailed code review."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1500
        )
        review = response.choices[0].message['content'].strip()
        return jsonify({'review': review})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/optimize_code', methods=['POST'])
@login_required
def optimize_code():
    if not current_user.is_premium:
        return jsonify({'error': 'Upgrade ke Premium dulu!'}), 403
    data = request.json
    code = data.get('code', '')
    if not code:
        return jsonify({'error': 'Kode diperlukan'}), 400
    
    prompt = f"Optimize this code for performance and efficiency: {code}"
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Optimize code for speed and resources."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1500
        )
        optimized = response.choices[0].message['content'].strip()
        return jsonify({'optimized_code': optimized})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import openai
import os
import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///coding_ai.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

openai.api_key = os.getenv('OPENAI_API_KEY', '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')

# Model Database
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

# Routes
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
        flash('Login gagal!')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        new_user = User(username=username, password=password)
        db.session.add(new_user)
        db.session.commit()
        flash('Registrasi berhasil!')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/dashboard')
@login_required
def dashboard():
    if not current_user.is_premium:
        return redirect(url_for('upgrade'))
    codes = CodeHistory.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard.html', codes=codes)

@app.route('/upgrade')
@login_required
def upgrade():
    # Simulasi payment
    current_user.is_premium = True
    db.session.commit()
    flash('Upgrade ke Premium berhasil!')
    return redirect(url_for('dashboard'))

@app.route('/generate_code', methods=['POST'])
@login_required
def generate_code():
    if not current_user.is_premium:
        return jsonify({'error': 'Upgrade ke Premium dulu!'}), 403
    data = request.json
    prompt = data.get('prompt', '')
    lang = data.get('lang', 'python')
    if not prompt:
        return jsonify({'error': 'Prompt diperlukan'}), 400
    
    full_prompt = f"Generate {lang} code for: {prompt}"
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a premium coding assistant. Generate clean, efficient code."},
                {"role": "user", "content": full_prompt}
            ],
            max_tokens=1500,
            temperature=0.7
        )
        code = response.choices[0].message['content'].strip()
        # Simpan ke history
        new_code = CodeHistory(user_id=current_user.id, prompt=prompt, code=code)
        db.session.add(new_code)
        db.session.commit()
        return jsonify({'code': code})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/fix_code', methods=['POST'])
@login_required
def fix_code():
    if not current_user.is_premium:
        return jsonify({'error': 'Upgrade ke Premium dulu!'}), 403
    data = request.json
    code = data.get('code', '')
    error = data.get('error', '')
    if not code:
        return jsonify({'error': 'Kode diperlukan'}), 400
    
    prompt = f"Fix this code: {code}. Error: {error}. Provide corrected code and explanation."
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Debug and fix code, explain changes."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1500,
            temperature=0.5
        )
        fixed = response.choices[0].message['content'].strip()
        return jsonify({'fixed_code': fixed})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/review_code', methods=['POST'])
@login_required
def review_code():
    if not current_user.is_premium:
        return jsonify({'error': 'Upgrade ke Premium dulu!'}), 403
    data = request.json
    code = data.get('code', '')
    if not code:
        return jsonify({'error': 'Kode diperlukan'}), 400
    
    prompt = f"Review this code for best practices, security, and improvements: {code}"
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Provide detailed code review."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1500
        )
        review = response.choices[0].message['content'].strip()
        return jsonify({'review': review})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/optimize_code', methods=['POST'])
@login_required
def optimize_code():
    if not current_user.is_premium:
        return jsonify({'error': 'Upgrade ke Premium dulu!'}), 403
    data = request.json
    code = data.get('code', '')
    if not code:
        return jsonify({'error': 'Kode diperlukan'}), 400
    
    prompt = f"Optimize this code for performance and efficiency: {code}"
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Optimize code for speed and resources."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1500
        )
        optimized = response.choices[0].message['content'].strip()
        return jsonify({'optimized_code': optimized})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)

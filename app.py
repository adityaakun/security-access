# app.py - Backend Flask untuk AI Coding Assistant
from flask import Flask, request, jsonify, render_template
from transformers import pipeline
import logging
import os
from datetime import datetime

app = Flask(__name__)

# Konfigurasi logging untuk debugging dan monitoring
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load model AI untuk generate kode (gunakan model kecil seperti CodeGPT atau GPT-2 fine-tuned)
# Untuk efisiensi, gunakan pipeline dari Hugging Face. Jika ingin lebih baik, ganti dengan API.
try:
    code_generator = pipeline("text-generation", model="microsoft/DialoGPT-medium")  # Placeholder; ganti dengan model coding seperti "Salesforce/codegen-350M-mono"
    logger.info("Model AI loaded successfully.")
except Exception as e:
    logger.error(f"Failed to load model: {e}")
    code_generator = None

# Fungsi untuk generate kode berdasarkan prompt
def generate_code(prompt, max_length=500):
    if code_generator:
        try:
            result = code_generator(prompt, max_length=max_length, num_return_sequences=1)
            return result[0]['generated_text']
        except Exception as e:
            logger.error(f"Error generating code: {e}")
            return "Error: Unable to generate code."
    else:
        return "AI model not loaded. Please check configuration."

# Fungsi untuk fix kode (sederhana: deteksi error dan saran perbaikan)
def fix_code(code_input):
    # Placeholder logic: Cek syntax Python sederhana
    try:
        compile(code_input, '<string>', 'exec')
        return "Code is syntactically correct. No fixes needed."
    except SyntaxError as e:
        logger.info(f"Syntax error detected: {e}")
        return f"Syntax error: {e}. Suggestion: Check indentation and syntax."
    except Exception as e:
        return f"Other error: {e}. Please provide more details."

# Route untuk halaman utama (render template)
@app.route('/')
def index():
    return render_template('index.html')

# API endpoint untuk generate kode
@app.route('/generate', methods=['POST'])
def api_generate():
    data = request.get_json()
    prompt = data.get('prompt', '')
    if not prompt:
        return jsonify({'error': 'Prompt is required'}), 400
    code = generate_code(prompt)
    logger.info(f"Generated code for prompt: {prompt[:50]}...")
    return jsonify({'code': code})

# API endpoint untuk fix kode
@app.route('/fix', methods=['POST'])
def api_fix():
    data = request.get_json()
    code = data.get('code', '')
    if not code:
        return jsonify({'error': 'Code is required'}), 400
    fixed = fix_code(code)
    logger.info(f"Fixed code: {code[:50]}...")
    return jsonify({'fixed': fixed})

# Route untuk upload file kode (opsional, untuk fitur lanjutan)
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    # Simpan file sementara dan proses
    filepath = os.path.join('uploads', file.filename)
    file.save(filepath)
    with open(filepath, 'r') as f:
        code = f.read()
    fixed = fix_code(code)
    os.remove(filepath)  # Hapus setelah proses
    return jsonify({'fixed': fixed})

# Middleware untuk logging request
@app.before_request
def log_request_info():
    logger.info(f"Request: {request.method} {request.url} from {request.remote_addr}")

# Error handler
@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal error: {error}")
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    # Buat folder uploads jika belum ada
    if not os.path.exists('uploads'):
        os.makedirs('uploads')
    app.run(debug=True, host='0.0.0.0', port=5000)

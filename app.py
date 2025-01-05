from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import csv

app = Flask(__name__, template_folder='templates')

# Configurações
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///library.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Limite de 16 MB para uploads
app.secret_key = 'mysecretkey'

# Verificar e criar pastas
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

EXPORT_FOLDER = os.path.join(os.getcwd(), 'exports')
if not os.path.exists(EXPORT_FOLDER):
    os.makedirs(EXPORT_FOLDER)

db = SQLAlchemy(app)

# Modelos de dados
class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(10), nullable=False)  # 'book'
    title = db.Column(db.String(100), nullable=False)
    author = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    filename = db.Column(db.String(100), nullable=True)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False, unique=True)
    password = db.Column(db.String(100), nullable=False)

# Funções auxiliares
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'txt'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Rotas
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/books')
def view_books():
    books = Item.query.filter_by(type='book').all()
    return render_template('books.html', books=books)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user_exists = User.query.filter_by(username=username).first()
        if user_exists:
            flash("Usuário já existe!", "danger")
            return redirect(url_for('register'))
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        flash("Conta criada com sucesso!", "success")
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            flash("Login bem-sucedido!", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("Usuário ou senha incorretos.", "danger")
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash("Você precisa fazer login para acessar essa página.", "danger")
        return redirect(url_for('login'))
    return render_template('dashboard.html')

@app.route('/upload_books', methods=['GET', 'POST'])
def upload_books():
    if 'user_id' not in session:
        flash("Você precisa fazer login para acessar essa página.", "danger")
        return redirect(url_for('login'))
    if request.method == 'POST':
        file = request.files.get('file')
        title = request.form['title']
        author = request.form['author']
        description = request.form['description']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            new_book = Item(type='book', title=title, author=author, description=description, filename=filename)
            db.session.add(new_book)
            db.session.commit()
            flash("Livro enviado com sucesso!", "success")
            return redirect(url_for('view_books'))
        flash("Erro ao fazer upload do arquivo.", "danger")
    return render_template('upload_books.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash("Você saiu com sucesso!", "success")
    return redirect(url_for('index'))

@app.route('/export_users')
def export_users():
    users = User.query.all()
    file_path = os.path.join(EXPORT_FOLDER, 'users.csv')
    with open(file_path, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['Username', 'Password'])
        for user in users:
            writer.writerow([user.username, user.password])
    return send_from_directory(EXPORT_FOLDER, 'users.csv', as_attachment=True)

@app.route('/uploads/<filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True, port=5001)

with app.app_context():
    db.create_all()

import os
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

app = Flask(__name__)
app.config['SECRET_KEY'] = 'super-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# Папка для сохранения загруженных файлов
app.config['UPLOAD_FOLDER'] = 'static/uploads'

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# ТАБЛИЦА ПОЛЬЗОВАТЕЛЕЙ
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

# ТАБЛИЦА ТРЕКОВ
class Track(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    artist_name = db.Column(db.String(100), nullable=False)
    track_title = db.Column(db.String(100), nullable=False)
    file_path = db.Column(db.String(200), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# 1. ГЛАВНАЯ СТРАНИЦА
@app.route('/')
@login_required
def index():
    user_tracks = Track.query.filter_by(user_id=current_user.id).all()
    return render_template('index.html', tracks=user_tracks)

# 2. ОБРАБОТЧИК ЗАГРУЗКИ ТРЕКА
@app.route('/upload', methods=['POST'])
@login_required
def upload_track():
    artist_name = request.form.get('artist_name')
    track_title = request.form.get('track_title')
    file = request.files.get('track_file')

    if not artist_name or not track_title or not file:
        flash('Все поля должны быть заполнены!')
        return redirect(url_for('index'))

    if file.filename == '':
        flash('Файл не выбран!')
        return redirect(url_for('index'))

    if file:
        try:
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(file_path)

            new_track = Track(
                artist_name=artist_name,
                track_title=track_title,
                file_path=file_path,
                user_id=current_user.id
            )
            db.session.add(new_track)
            db.session.commit()

            flash(f'Трек "{artist_name} — {track_title}" успешно загружен!')
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка базы данных при загрузке: {e}')
            
        return redirect(url_for('index'))

# 3. ОБРАБОТЧИК УДАЛЕНИЯ ТРЕКА
@app.route('/delete/<int:track_id>', methods=['POST'])
@login_required
def delete_track(track_id):
    track = Track.query.get_or_404(track_id)
    
    if track.user_id != current_user.id:
        flash('У вас нет прав на удаление этого трека!')
        return redirect(url_for('index'))
        
    try:
        if os.path.exists(track.file_path):
            os.remove(track.file_path)
            
        db.session.delete(track)
        db.session.commit()
        
        flash(f'Релиз успешно удален!')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при удалении трека: {e}')
        
    return redirect(url_for('index'))

# 3.5 ОБРАБОТЧИК РЕДАКТИРОВАНИЯ ТРЕКА
@app.route('/edit/<int:track_id>', methods=['POST'])
@login_required
def edit_track(track_id):
    track = Track.query.get_or_404(track_id)
    
    if track.user_id != current_user.id:
        flash('У вас нет прав на редактирование этого трека!')
        return redirect(url_for('index'))
        
    new_artist = request.form.get('artist_name')
    new_title = request.form.get('track_title')
    
    if not new_artist or not new_title:
        flash('Поля изменения не могут быть пустыми!')
        return redirect(url_for('index'))
        
    try:
        track.artist_name = new_artist
        track.track_title = new_title
        db.session.commit()
        flash('Данные трека успешно обновлены!')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при обновлении данных: {e}')
        
    return redirect(url_for('index'))

# 4. СТРАНИЦА ВХОДА
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.password == password: 
            login_user(user)
            return redirect(url_for('index'))
        return 'Неверный логин или пароль'
    return render_template('login.html')

# 5. СТРАНИЦА РЕГИСТРАЦИИ
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            return 'Пожалуйста, заполните все поля формы!'
        
        if User.query.filter_by(username=username).first():
            return 'Такой пользователь уже существует'
            
        try:
            new_user = User(username=username, password=password)
            db.session.add(new_user)
            db.session.commit()
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            return f"Ошибка при работе с базой данных: {e}"
            
    return render_template('register.html')

# 6. ОБРАБОТЧИК ВЫХОДА ИЗ СИСТЕМЫ
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='127.0.0.1', port=5000, debug=True)

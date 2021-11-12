from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_required, login_user, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date, timedelta
from flask_mail import Mail, Message
from threading import Thread
import time

app = Flask(__name__)

app.config['SECRET_KEY'] = 'secret key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data_base.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAIL_SERVER'] = 'smtp.googlemail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'TimeDis.app@gmail.com'
app.config['MAIL_DEFAULT_SENDER'] = 'TimeDis.app@gmail.com'
app.config['MAIL_PASSWORD'] = 'Time_mail_Dis_sender_2020'

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'log'
mail = Mail(app)


def create_mail():
    time_now = time.strftime("%H:%M", time.localtime())
    if time_now == '08:00' or time_now == '14:00' or time_now == '20:00':
        user = db.session.query(Users).all()
        for elm in user:
            msg = Message('Уведомление от TimeDis', sender=app.config['MAIL_USERNAME'], recipients=[elm.mail])

            with app.app_context():
                msg.html = render_template('mail.html', name=elm.login)
                mail.send(msg)


def mailing():
    while True:
        create_mail()
        time.sleep(60)


def thread():
    thread = Thread(target=mailing)
    thread.start()


def del_old():
    remind = db.session.query(Reminds).filter(Reminds.id_user == current_user.id).all()
    for elm in remind:
        if elm.date < date.today():
            db.session.delete(elm)
    return db.session.commit()


def delete(id):
    for_del = db.session.query(Reminds).filter(Reminds.id == id).all()
    db.session.delete(for_del[0])
    db.session.commit()
    return redirect(url_for('show'))


def next_day(id):
    day = date.today()
    n_day = day + timedelta(days=1)
    db.session.query(Reminds).filter(Reminds.id == id).update({'date': date(int(n_day.year), int(n_day.month), int(n_day.day))}, synchronize_session='fetch')
    db.session.commit()
    return redirect(url_for('menu'))


def success(id):
    db.session.query(Reminds).filter(Reminds.id == id).update({'state': 1}, synchronize_session='fetch')
    db.session.commit()
    return redirect(url_for('menu'))


@login_manager.user_loader
def load_user(user_id):
    return db.session.query(Users).get(user_id)


class Users(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(20), unique=True, nullable=False)
    mail = db.Column(db.String(100), nullable=False)
    pr = db.relationship('Reminds', backref='users', uselist=False)

    def __repr__(self):
        return '<Users %r>' % self.id


class Reminds(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(50), nullable=False)
    comment = db.Column(db.String(100), nullable=True)
    date = db.Column(db.Date, nullable=False)
    priory = db.Column(db.String(100), nullable=False)
    state = db.Column(db.Boolean, default=0)
    id_user = db.Column(db.Integer, db.ForeignKey('users.id'))

    def __repr__(self):
        return '<Reminds %r>' % self.id


db.create_all()
thread()


@app.route('/', methods=['POST', 'GET'])
@app.route('/log/', methods=['POST', 'GET'])
def log():
    if current_user.is_authenticated:
        return redirect(url_for('menu'))
    if request.method == "POST":
        if request.form['btn'] == 'Войти':
            login = request.form['login']
            password = request.form['pass']
            user = db.session.query(Users).filter(Users.login == login).first()
            if user and check_password_hash(user.password, password):
                login_user(user)
                return redirect(url_for('menu'))
            flash("Неверный логин/пароль", 'error1')
            return redirect(url_for('log'))

        elif request.form['btn'] == 'Зарегистрироваться':
            login = request.form['new_login']
            mail = request.form['mail']
            password = generate_password_hash(request.form['new_pass'])
            chek_pass = request.form['new_pass2']
            if check_password_hash(password, chek_pass) != True:
                flash("Пароли не совпадают", 'error2')
                return redirect(url_for('log'))
            try:
                user = Users(login=login, password=password, mail=mail)
                db.session.add(user)
                db.session.commit()
                return redirect('/log')
            except:
                db.session.rollback()
                return 'DataBaseError :('
    else:
        return render_template('login.html')


@app.route('/logout/')
@login_required
def logout():
    logout_user()
    return redirect(url_for('log'))


@app.route('/menu/', methods=['POST', 'GET'])
@login_required
def menu():
    if request.method == 'POST':
        try:
            if request.form['for_next_day']:
                next_day(request.form['for_next_day'])
        except:
            try:
                if request.form['success']:
                    success(request.form['success'])
            except:
                delete(request.form['delete'])

    login = current_user.login
    daily = db.session.query(Reminds).filter(Reminds.id_user == current_user.id, Reminds.date == date.today()).order_by(Reminds.priory).all()
    daily1 = db.session.query(Reminds).filter(Reminds.id_user == current_user.id, Reminds.date == date.today(), Reminds.state == 1).order_by(Reminds.priory).all()
    daily2 = db.session.query(Reminds).filter(Reminds.id_user == current_user.id, Reminds.date == date.today(), Reminds.state == 0).order_by(Reminds.priory).all()
    return render_template('main_menu.html', login=login, daily=daily, daily2=daily2, daily1=daily1)


@app.route('/add/', methods=['POST', 'GET'])
@login_required
def add():
    if request.method == 'POST':
        title = request.form['title']
        comment = request.form['comment']
        dat = request.form['date']
        priory = request.form['priory']
        id_user = current_user.id
        try:
            remind = Reminds(title=title, comment=comment, date=date(int(dat[0:4]), int(dat[5:7]), int(dat[8:10])), priory=priory, id_user=id_user)
            db.session.add(remind)
            db.session.commit()
            return redirect(url_for('menu'))
        except:
            db.session.rollback()
            return 'ERROR'
    return render_template('add.html')


@app.route('/update/<int:id>', methods=['POST', 'GET'])
@login_required
def update(id):
    if request.method == 'POST':
        title = request.form['title']
        comment = request.form['comment']
        dat = request.form['date']
        priory = request.form['priory']
        try:
            db.session.query(Reminds).filter(Reminds.id == id).update({'title': title, 'comment': comment, 'date': date(int(dat[0:4]), int(dat[5:7]), int(dat[8:10])), 'priory': priory}, synchronize_session='fetch')
            db.session.commit()
            return redirect(url_for('show'))
        except:
            db.session.rollback()
            return 'ERROR'

    for_update = db.session.query(Reminds).filter(Reminds.id == id).all()
    return render_template('update.html', for_update=for_update)


@app.route('/show/', methods=['POST', 'GET'])
@login_required
def show():
    if request.method == 'POST':
        try:
            if request.form['search'] == 'Поиск':
                serch_title = request.form['search_title']
                search_rez = db.session.query(Reminds).filter(Reminds.id_user == current_user.id, Reminds.title == serch_title).all()
                if len(search_rez) == 0:
                    remind = db.session.query(Reminds).filter(Reminds.id_user == current_user.id).order_by(Reminds.priory, Reminds.date).all()
                    return render_template('show.html', remind=remind)
                else:
                    return render_template('show.html', remind=search_rez)
        except:
            delete(request.form['id_delete'])
    del_old()
    remind = db.session.query(Reminds).filter(Reminds.id_user == current_user.id).order_by(Reminds.priory, Reminds.date).all()
    return render_template('show.html', remind=remind)


if __name__ == '__main__':
    app.run(debug=True)

#host="192.168.0.17",port=5000
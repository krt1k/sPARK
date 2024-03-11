from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy 
import bcrypt
from flask_login import login_required


app = Flask(__name__)

# db
# bcrypt = Bcrypt(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db = SQLAlchemy(app)
app.config['SECRET_KEY'] = 'ToPsecret'


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    
    def __init__(self, username, email, password):
        self.username = username
        self.email = email
        self.password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        # self.is_admin = is_admin

    def check_password(self, password):
        return bcrypt.checkpw(password.encode('utf-8'), self.password.encode('utf-8'))

class Balance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    balance = db.Column(db.Integer, nullable=False, default=0)

    def __init__(self, username, balance):
        self.username = username
        self.balance = balance

    def add_amount(self, amount):
        self.balance += amount


@app.route('/create_admin', methods=['GET', 'POST'])
def create_admin():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['pwd']
        
        admin = User(username, email, password)
        admin.is_admin = True
        db.session.add(admin)
        db.session.commit()

        if session['is_admin']:
            return "<script>alert('Admin created!'); window.location.href = '/admin';</script>"
        return "<script>alert('Admin created!'); window.location.href = '/login';</script>"

    return render_template('create_admin.html')

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if session['is_admin']:
        user = User.query.filter_by(username=session['username']).first()
        return render_template('admin.html', user=user, email=session['email'])
    return render_template('login.html', error='You are not a admin!')



@app.route('/check_balance', methods=['GET', 'POST'])
def check_balance():
    if session['is_admin']:
        if request.method == 'POST':
            username = request.form['username']
            balance = Balance.query.filter_by(username=username).first()
            return render_template('check_balance.html', balance=balance)
        return render_template('check_balance.html')
    return "You are not an admin!"



@app.route('/add_balance', methods=['GET', 'POST'])
def add_balance():
    if session['is_admin']:
        if request.method == 'POST':
            username = request.form['username']
            amount = request.form['amount']
            # amount to int
            amount = int(amount)

            balance = Balance.query.filter_by(username=username).first()
            balance.balance += amount

            db.session.commit()
            return "<script>alert('Balance added!'); window.location.href = '/admin';</script>"
        
        return render_template('add_balance.html')
    return "You are not an admin!"




@app.route('/reset')
def reset():
    # if session['is_admin']:
        db.drop_all()
        db.create_all()
        return "<script>alert('Database reset!'); window.location.href = '/';</script>"
    # return 'You are not an admin!'


@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        pass
    return render_template('index.html')


@app.route('/logout')
def logout():
    if session['username']:
        session.pop('username', None)
        session.pop('email', None)
        session.pop('is_admin', None)
        return redirect(url_for('login'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['pwd']

        user = User.query.filter_by(username=username).first()
        if user:
            if user.check_password(password):
                session['username'] = user.username
                session['email'] = user.email
                session['is_admin'] = user.is_admin

                if user.is_admin == True:
                    return redirect(url_for('admin'))

                return redirect(url_for('dashboard'))
            else:
                # notify user of invalid password
                return render_template('login.html', error='Invalid username/password')
        else:
            return redirect(url_for('register') )
    
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['pwd']
        
        user = User(username, email, password)
        db.session.add(user)
        db.session.commit()

        print(username, email, password)

        return redirect(url_for('login'))
    
    return render_template('register.html')


@app.route('/dashboard')
def dashboard():
    if session['username']:
        user = User.query.filter_by(username=session['username']).first()
        amount = Balance.query.filter_by(username=session['username']).first()
        return render_template('dashboard.html', user=user, email=session['email'], amount=amount)
    return render_template('login.html', error='You are not logged in')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
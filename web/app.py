import datetime
from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
import bcrypt


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
        balance = Balance(username, 0)
        db.session.add(balance)
        db.session.commit()
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

class EntryLogs(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    time = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
    # entry or exit
    transact = db.Column(db.Boolean, nullable=False)
    
    def __init__(self, username, transact):
        self.username = username
        self.time = datetime.datetime.utcnow
        self.transact = transact
        

@app.route('/transact/<string:transact>')
def entry(transact):
    if session['username']:
        # trans = EntryLogs.query.filter_by(username=session['username']).first()
        if transact == "entry":
            entry = EntryLogs(session['username'], True)
            db.session.add(entry)
            db.session.commit()
            return "<script>alert('Entry logged!'); window.location.href = '/dashboard';</script>"
        elif transact == "exit":
            exit = EntryLogs(session['username'], False)
            db.session.add(exit)
            db.session.commit()
            return "<script>alert('Exit logged!'); window.location.href = '/dashboard';</script>"

    return render_template('login.html', error='You are not logged in')

# TODO: Add amount logs
# class AmountLogs(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     username = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
#     time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
#     amount = db.Column(db.Integer, nullable=False)
    
#     def detect(self, amount):
#         user = User.query.filter_by(username=self.username).first()
#         user.balance = user.balance - amount
#         db.session.add(self, amount)
#         db.session.commit()

@app.route('/list_entry_logs')
def list_entry_logs():
    logs = EntryLogs.query.all()
    # serialize the data
    logs = list(map(lambda log: {'username': log.username, 'time': log.time, 'transact': log.transact}, logs))
    return logs

@app.route('/list_users')
def list_users(): 
    users = User.query.all()
    # serialize the data
    users = list(map(lambda user: {'username': user.username, 'email': user.email, 'is_admin': user.is_admin}, users))
    return users

@app.route('/list_balances')
def list_balances():
    balances = Balance.query.all()
    # serialize the data
    balances = list(map(lambda balance: {'username': balance.username, 'balance': balance.balance}, balances))
    return balances

# @event.listens_for(User, 'after_insert')
# def add_records(mapper, connection, target):
#     balance = Balance(username=target.id, balance=0)
#     db.session.add(balance)
#     db.session.commit()
#     db.session.close()


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
            # balance.balance += amount

            balance.add_amount(amount)

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
    if not session.get('username'):
        return render_template('index.html')

    if session['username']:
        if session['is_admin']:
            return redirect(url_for('admin'))
        return redirect(url_for('dashboard'))


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
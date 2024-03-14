import datetime
import random
import string
from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
import bcrypt
from waitress import serve

# basic http auth
from flask_httpauth import HTTPBasicAuth
auth = HTTPBasicAuth()
http_user = "krth1k"
pw = "Broject@1234"

@auth.verify_password
def verify_password(username, password):
    if username == http_user and password == pw:
        return True
    return False


app = Flask(__name__)

dev = True

# db
# bcrypt = Bcrypt(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db = SQLAlchemy(app)
app.config['SECRET_KEY'] = 'ToPsecret'
one_hr_rate = 30

entry_count = 0
exit_count = 0

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
    
    def detect_amount(self, amount):
        self.balance = self.balance - amount
        return self.balance

class EntryLogs(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    time = db.Column(db.DateTime, nullable=False, default=datetime.datetime.now)
    # entry or exit
    transact = db.Column(db.Boolean, nullable=False, default=True)
    
    def __init__(self, username, transact):
        self.username = username
        self.time = datetime.datetime.now()
        self.transact = transact


# parking slot availability
# slot number A1-A10, B1-B10, C1-C10
# slot status: True or False
class ParkingSlots(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # slot_number = db.Column(db.String(10), nullable=False)
    slot_number = db.Column(db.String(10), nullable=False)
    status = db.Column(db.Boolean, nullable=False, default='True')
    username = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    def __init__(self, slot_number):
        self.slot_number = slot_number
        self.status = True
    
    def get_status(self):
        return self.status
    
    def change_status(self, status):
        self.status = status
        if not status:
            self.username = session['username']
        else:
            self.username = None
        return self.status

@app.route('/slot_init')
def slot_init():
    # user = User('testing', 'testing@gmail.com', 'testing')
    # db.session.add(user)
    # db.session.commit()
    floors = ['A', 'B', 'C']
    count = [i for i in range(1, 11)]

    for floor in floors:
        for i in count:
            slot = ParkingSlots(f"{floor}{i}")
            db.session.add(slot)
            db.session.commit()
            db.session.close()
    return slot_finder()

@app.route('/slot_finder')
def slot_finder():
    slots = ParkingSlots.query.where(ParkingSlots.status == True).order_by(ParkingSlots.id.asc()).all()

    for slot in slots:
        return slot.slot_number
    
    return "No slots available"

@app.route('/list_slot')
@auth.login_required
def list_slots():
    slots = ParkingSlots.query.all()
    slots = list(map(lambda slot: {'slot_number': slot.slot_number, 'status': slot.status, 'username': slot.username}, slots))
    return slots

current_entry_token = ""
current_exit_token = ""


def gen_token(type):
    token = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(6))
    global current_exit_token
    global current_entry_token
    global entry_count
    global exit_count
    if type == "entry":
        # entry_count = 0
        current_entry_token = token
    elif type == "exit":
        # exit_count = 0
        current_exit_token = token

@app.route('/transact/<string:type>/<string:token>')
def entry(type, token):
    #dynamic url with unique token
    
    global entry_count
    global exit_count

    if session['username']:
        # trans = EntryLogs.query.filter_by(username=session['username']).first()

        if type == "entry":

            if token != current_entry_token:
                return "<script>alert('Token not valid!'); window.location.href = '/dashboard';</script>"
            
            # check if the last entry is an exit
            last_entry = EntryLogs.query.filter_by(username=session['username']).order_by(EntryLogs.time.desc()).first()
            if last_entry and last_entry.transact == True:
                gen_token("entry")
                entry_count = 0
                return "<script>alert('You have not exited yet!'); window.location.href = '/dashboard';</script>"
            
            # check for minimum balance
            balance = Balance.query.filter_by(username=session['username']).first()
            if balance.balance < 30:
                gen_token("entry")
                entry_count = 0
                return "<script>alert('Insufficient minimum balance!'); window.location.href = '/dashboard';</script>"

            entry = EntryLogs(session['username'], True)
            db.session.add(entry)
            db.session.commit()
            slot_num = slot_finder()
            if slot_num != "No slots available":
                slot = ParkingSlots.query.filter_by(slot_number=slot_num).first()
                slot.change_status(False)
                db.session.commit()
                gen_token("entry")
                entry_count = 0
                return render_template('entry.html', slot=slot_num, slot_avail=True)
            
            gen_token("entry")
            entry_count = 0
            return redirect('entry.html', slot_avail=False)
        
        elif type == "exit":

            if token != current_exit_token:
                return "<script>alert('Token not valid!'); window.location.href = '/dashboard';</script>"
            
            # check if the last entry is an entry
            last_exit = EntryLogs.query.filter_by(username=session['username']).order_by(EntryLogs.time.desc()).first()
            if last_exit and last_exit.transact == False:
                gen_token("exit")
                exit_count = 0
                return "<script>alert('You have not entered yet!'); window.location.href = '/dashboard';</script>"
            
            exit = EntryLogs(session['username'], False)
            db.session.add(exit)
            db.session.commit()
            slot = ParkingSlots.query.filter_by(username=session['username']).first()
            slot.change_status(True)
            
            amount = calculate_balance()
            if amount:
                gen_token("exit")
                exit_count = 0
                return f"<script>alert('Amount: {amount[0]} detected for {amount[1]} seconds!'); window.location.href = '/dashboard';</script>"
            gen_token("exit")
            exit_count = 0
            return "<script>alert('You have not entered yet!'); window.location.href = '/dashboard';</script>"

    return render_template('login.html', error='You are not logged in')

# TODO: Add QR code scanner
# @app.route('/scan_qr')
# def scan_qr():
#     return render_template('scan_qr.html')

@app.route('/qr/<string:type>')
@auth.login_required
def qr(type):
    global entry_count
    global exit_count
    if type == "entry":
        if entry_count < 1:
            entry_count += 1
        else:
            gen_token("entry")
            entry_count = 0
        print(f"entry token: {current_entry_token}, count: {entry_count}")
        return render_template('qr.html', type=type, title=type, token=current_entry_token)
    elif type == "exit":
        if exit_count < 2:
            exit_count += 1
        else:
            gen_token("exit")
            exit_count = 0
        print(f"exit token: {current_exit_token}, count: {exit_count}")
        return render_template('qr.html', type=type, title=type, token=current_exit_token)
    return "Invalid type!"


# TODO: Add amount logs
class AmountLogs(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    time = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow())
    amount = db.Column(db.Integer, nullable=False)
    remaining_balance = db.Column(db.Integer, nullable=False)

    def __init__(self, username, amount, remaining_balance):
        self.username = username
        # self.time = datetime.datetime.utcnow()
        self.time = datetime.now(datetime.UTC)
        self.amount = amount
        self.remaining_balance = remaining_balance
    

def calculate_balance():
    last_user_entry = EntryLogs.query.filter_by(username=session['username']).where(EntryLogs.transact == True).order_by(EntryLogs.time.desc()).first()
    last_user_exit = EntryLogs.query.filter_by(username=session['username']).where(EntryLogs.transact == False).order_by(EntryLogs.time.desc()).first()

    print(f"user: {session['username']}, entry: {last_user_entry}, exit: {last_user_exit}")
    
    if last_user_entry and last_user_exit:
        time_diff = last_user_exit.time - last_user_entry.time
        amount = time_diff.seconds * (1/3600) * one_hr_rate
        # minimum amount is 10
        amount = int(round(amount, 0))

        if amount < 10:
            amount = 10

        balance = Balance.query.filter_by(username=session['username']).first()
        rem_bal = balance.detect_amount(amount)
        db.session.commit()

        amt_log = AmountLogs(username=session['username'], amount=amount, remaining_balance=rem_bal)
        db.session.add(amt_log)
        db.session.commit()

        return amount, time_diff.seconds


@app.route('/detect', methods=['GET', 'POST'])
def detect():

    if session.get('username'):

        entry("exit")
        
    
    return render_template('login.html', error='You are not logged in')

@app.route('/list_entry_logs')
@auth.login_required
def list_entry_logs():
    logs = EntryLogs.query.all()
    # serialize the data
    logs = list(map(lambda log: {'username': log.username, 'time': log.time, 'type': log.transact}, logs))
    return logs

@app.route('/list_users')
@auth.login_required
def list_users(): 
    # users = User.query.all()
    users = User.query.where(User.is_admin == False).all()
    # serialize the data
    users = list(map(lambda user: {'username': user.username, 'email': user.email, 'is_admin': user.is_admin}, users))
    return users

@app.route('/list_balances')
@auth.login_required
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
@auth.login_required
def create_admin():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['pwd']
        
        admin = User(username, email, password)
        admin.is_admin = True
        db.session.add(admin)
        db.session.commit()
        
        session['username'] = admin.username
        session['email'] = admin.email
        session['is_admin'] = admin.is_admin

        if not session['is_admin']:
            return "<script>alert('Admin created!'); window.location.href = '/login';</script>"
        elif session['is_admin']:
            return "<script>alert('Admin created!'); window.location.href = '/admin';</script>"
        

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
        balances_list = list_balances()
        
        if request.method == 'POST':
            username = request.form['username']
            balance = Balance.query.filter_by(username=username).first()
            return render_template('check_balance.html', balance=balance.balance, balances=balances_list)
        return render_template('check_balance.html', balances=balances_list)
    return "You are not an admin!"



@app.route('/add_balance', methods=['GET', 'POST'])
def add_balance():
    if session['is_admin']:
        balances_list = list_balances()

        if request.method == 'POST':
            username = request.form['username']
            amount = request.form['amount']
            # amount to int
            amount = int(amount)

            balance = Balance.query.filter_by(username=username).first()
            # balance.balance += amount

            balance.add_amount(amount)

            db.session.commit()
            return "<script>alert('Balance added!'); window.location.href = '/add_balance';</script>"
        
        return render_template('add_balance.html', balances=balances_list)
    return "You are not an admin!"


@app.route('/reset')
@auth.login_required
def reset():
    # if session['is_admin']:
        db.drop_all()
        db.create_all()
        return "<script>alert('Database reset!'); window.location.href = '/';</script>" and slot_init()

    # return 'You are not an admin!'

with app.app_context():
    db.create_all()
    # slot_init()

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
        logs = AmountLogs.query.filter_by(username=session['username']).order_by(AmountLogs.time.desc()).all()
        return render_template('dashboard.html', user=user, email=session['email'], amount=amount, logs=logs)
    return render_template('login.html', error='You are not logged in')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # if slot is empty, initialize slots
        if not ParkingSlots.query.first():
            slot_init()

    if dev:
        app.run(debug=True, host="0.0.0.0", port=5000)
    else:
        serve(app, host="0.0.0.0", port=5000, threads=256)
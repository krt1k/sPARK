from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy 
from flask_bcrypt import Bcrypt


app = Flask(__name__)

# db
bcrypt = Bcrypt(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SECRET_KEY'] = 'ToPsecret'
db = SQLAlchemy(app)
# db.init_app(app)
# class User:



@app.route('/')
def home():
    # return "<h1>Hello World!</h1><script>alert('Hello World!')</script>"
    return render_template('index.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/register')
def register():

    return render_template('register.html')

if __name__ == '__main__':
    app.run(debug=True)
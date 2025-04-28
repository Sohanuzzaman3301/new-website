from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fullname = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    items = db.Column(db.Text, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(150), nullable=False)
    address = db.Column(db.String(300), nullable=False)
    order_type = db.Column(db.String(20), nullable=False)
    delivery_time = db.Column(db.String(50), nullable=False)

    user = db.relationship('User', backref='orders')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.before_first_request
def create_tables():
    db.create_all()
    # seed a default test user
    if not User.query.filter_by(email='test@test.com').first():
        test_user = User(fullname='Test', email='test@test.com')
        test_user.set_password('test')
        db.session.add(test_user)
        db.session.commit()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/menu')
def menu():
    return render_template('menu.html')

@app.route('/signup', methods=['GET','POST'])
def signup():
    if request.method == 'POST':
        fullname = request.form.get('fullname')
        email = request.form.get('email')
        password = request.form.get('password')
        existing = User.query.filter_by(email=email).first()
        if existing:
            # if seeded test user, allow login
            if email == 'test@test.com' and existing.check_password(password):
                login_user(existing)
                return redirect(url_for('order'))
            return redirect(url_for('signup'))
        user = User(fullname=fullname, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        return redirect(url_for('order'))
    return render_template('signup.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user, remember=remember)
            return redirect(url_for('order'))
        return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/order', methods=['GET','POST'])
@login_required
def order():
    if request.method == 'POST':
        items = request.form.to_dict(flat=False)
        # convert items to string or JSON
        order = Order(
            user_id=current_user.id,
            items=str(items),
            name=request.form.get('name'),
            phone=request.form.get('phone'),
            email=request.form.get('email'),
            address=request.form.get('address'),
            order_type=request.form.get('orderType'),
            delivery_time=request.form.get('deliveryTime')
        )
        db.session.add(order)
        db.session.commit()
        return redirect(url_for('orders'))
    return render_template('order.html')

# add orders view to display user orders
@app.route('/orders')
@login_required
def orders():
    user_orders = Order.query.filter_by(user_id=current_user.id).all()
    # parse stored items and attach filtered list for display
    special_fields = {'name','phone','email','address','orderType','deliveryTime','specialInstructions','payment'}
    for o in user_orders:
        try:
            data = json.loads(o.items)
        except (TypeError, json.JSONDecodeError):
            data = {}
        item_list = []
        for key, val in data.items():
            if key not in special_fields:
                qty = int(val[0]) if isinstance(val, list) and val and val[0].isdigit() else 0
                if qty > 0:
                    # format key to readable name
                    name = key.replace('_',' ').title()
                    item_list.append((name, qty))
        o.item_list = item_list
    return render_template('orders.html', orders=user_orders)

# Profile view: show and edit user info
@app.route('/profile', methods=['GET','POST'])
@login_required
def profile():
    if request.method == 'POST':
        fullname = request.form.get('fullname')
        email = request.form.get('email')
        current_user.fullname = fullname
        current_user.email = email
        new_pw = request.form.get('password')
        if new_pw:
            current_user.set_password(new_pw)
        db.session.commit()
        return redirect(url_for('profile'))
    return render_template('profile.html')

if __name__ == '__main__':
    app.run(debug=True)

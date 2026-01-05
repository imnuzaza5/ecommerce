from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from models import db, User, Product, Cart, Order, OrderItem
from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed
from wtforms import StringField, PasswordField, TextAreaField, FloatField, IntegerField, SubmitField, FileField
from wtforms.validators import DataRequired, Email, Length, NumberRange
from werkzeug.utils import secure_filename
from flask_socketio import SocketIO, emit
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/images'

db.init_app(app)
socketio = SocketIO(app)

# Forms
class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=80)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    role = StringField('Role', validators=[DataRequired()], default='customer')
    submit = SubmitField('Register')

class ProductForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[DataRequired()])
    price = FloatField('Price', validators=[DataRequired(), NumberRange(min=0)])
    stock = IntegerField('Stock', validators=[DataRequired(), NumberRange(min=0)])
    image = FileField('Image', validators=[FileAllowed(['jpg', 'png', 'jpeg'], 'Images only!')])
    submit = SubmitField('Add Product')

# Routes
@app.route('/')
def index():
    products = Product.query.all()
    return render_template('index.html', products=products)

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    return render_template('product.html', product=product)

@app.route('/cart')
def cart():
    if 'user_id' not in session:
        flash('Please login to view cart')
        return redirect(url_for('login'))
    cart_items = Cart.query.filter_by(user_id=session['user_id']).all()
    total = sum(item.product.price * item.quantity for item in cart_items)
    return render_template('cart.html', cart_items=cart_items, total=total)

@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    if 'user_id' not in session:
        flash('Please login to add to cart')
        return redirect(url_for('login'))
    quantity = int(request.form.get('quantity', 1))
    cart_item = Cart.query.filter_by(user_id=session['user_id'], product_id=product_id).first()
    if cart_item:
        cart_item.quantity += quantity
    else:
        cart_item = Cart(user_id=session['user_id'], product_id=product_id, quantity=quantity)
        db.session.add(cart_item)
    db.session.commit()
    flash('Added to cart')
    return redirect(url_for('cart'))

@app.route('/remove_from_cart/<int:cart_id>')
def remove_from_cart(cart_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    cart_item = Cart.query.get_or_404(cart_id)
    if cart_item.user_id == session['user_id']:
        db.session.delete(cart_item)
        db.session.commit()
    return redirect(url_for('cart'))

@app.route('/checkout', methods=['POST'])
def checkout():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    cart_items = Cart.query.filter_by(user_id=session['user_id']).all()
    if not cart_items:
        flash('Cart is empty')
        return redirect(url_for('cart'))
    total = sum(item.product.price * item.quantity for item in cart_items)
    order = Order(user_id=session['user_id'], total_price=total)
    db.session.add(order)
    db.session.commit()
    for item in cart_items:
        order_item = OrderItem(order_id=order.id, product_id=item.product_id, quantity=item.quantity, price=item.product.price)
        db.session.add(order_item)
        # Reduce stock
        item.product.stock -= item.quantity
        db.session.delete(item)
    db.session.commit()
    flash('Order placed successfully')
    return redirect(url_for('orders'))

@app.route('/orders')
def orders():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_orders = Order.query.filter_by(user_id=session['user_id']).all()
    return render_template('orders.html', orders=user_orders)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            flash('Logged in successfully')
            return redirect(url_for('index'))
        flash('Invalid credentials')
    return render_template('login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        if User.query.filter_by(username=form.username.data).first():
            flash('Username already exists')
            return redirect(url_for('register'))
        if User.query.filter_by(email=form.email.data).first():
            flash('Email already exists')
            return redirect(url_for('register'))
        user = User(username=form.username.data, email=form.email.data, role=form.role.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Registered successfully')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out')
    return redirect(url_for('index'))

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Admin access required')
        return redirect(url_for('login'))
    form = ProductForm()
    if form.validate_on_submit():
        filename = None
        if form.image.data:
            filename = secure_filename(form.image.data.filename)
            form.image.data.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        product = Product(name=form.name.data, description=form.description.data,
                          price=form.price.data, stock=form.stock.data, image_url=filename,
                          seller_id=session['user_id'])
        db.session.add(product)
        db.session.commit()
        # Emit real-time event
        socketio.emit('product_created', {
            'id': product.id,
            'name': product.name,
            'description': product.description,
            'price': product.price,
            'stock': product.stock,
            'image_url': url_for('static', filename='images/' + product.image_url, _external=True) if product.image_url else None,
            'seller_id': product.seller_id
        })
        flash('Product added')
        return redirect(url_for('admin'))
    products = Product.query.all()
    return render_template('admin.html', form=form, products=products)

@app.route('/admin/delete/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
    product = Product.query.get_or_404(product_id)
    # Delete associated cart items and order items
    Cart.query.filter_by(product_id=product_id).delete()
    OrderItem.query.filter_by(product_id=product_id).delete()
    db.session.delete(product)
    db.session.commit()
    # Emit real-time event
    socketio.emit('product_deleted', {'id': product_id})
    flash('Product deleted')
    return redirect(url_for('admin'))

@app.route('/seller/products', methods=['GET', 'POST'])
def seller_products():
    if 'user_id' not in session or session.get('role') != 'seller':
        flash('Seller access required')
        return redirect(url_for('login'))
    form = ProductForm()
    if form.validate_on_submit():
        filename = None
        if form.image.data:
            filename = secure_filename(form.image.data.filename)
            form.image.data.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        product = Product(name=form.name.data, description=form.description.data,
                          price=form.price.data, stock=form.stock.data, image_url=filename,
                          seller_id=session['user_id'])
        db.session.add(product)
        db.session.commit()
        # Emit real-time event
        socketio.emit('product_created', {
            'id': product.id,
            'name': product.name,
            'description': product.description,
            'price': product.price,
            'stock': product.stock,
            'image_url': url_for('static', filename='images/' + product.image_url, _external=True) if product.image_url else None,
            'seller_id': product.seller_id
        })
        flash('Product added')
        return redirect(url_for('seller_products'))
    products = Product.query.filter_by(seller_id=session['user_id']).all()
    return render_template('seller_products.html', form=form, products=products)

@app.route('/seller/edit/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    if 'user_id' not in session or session.get('role') != 'seller':
        flash('Seller access required')
        return redirect(url_for('login'))
    product = Product.query.get_or_404(product_id)
    if product.seller_id != session['user_id']:
        flash('Unauthorized')
        return redirect(url_for('seller_products'))
    form = ProductForm()
    form.submit.label.text = 'Update Product'
    if request.method == 'GET':
        form.name.data = product.name
        form.description.data = product.description
        form.price.data = product.price
        form.stock.data = product.stock
    if form.validate_on_submit():
        product.name = form.name.data
        product.description = form.description.data
        product.price = form.price.data
        product.stock = form.stock.data
        if form.image.data:
            filename = secure_filename(form.image.data.filename)
            form.image.data.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            product.image_url = filename
        db.session.commit()
        flash('Product updated')
        return redirect(url_for('seller_products'))
    return render_template('edit_product.html', form=form, product=product)

@app.route('/seller/delete/<int:product_id>', methods=['POST'])
def seller_delete_product(product_id):
    if 'user_id' not in session or session.get('role') != 'seller':
        return redirect(url_for('login'))
    product = Product.query.get_or_404(product_id)
    if product.seller_id != session['user_id']:
        flash('Unauthorized')
        return redirect(url_for('seller_products'))
    # Delete associated cart items and order items
    Cart.query.filter_by(product_id=product_id).delete()
    OrderItem.query.filter_by(product_id=product_id).delete()
    db.session.delete(product)
    db.session.commit()
    # Emit real-time event
    socketio.emit('product_deleted', {'id': product_id})
    flash('Product deleted')
    return redirect(url_for('seller_products'))

# API Endpoints
@app.route('/api/products')
def api_products():
    products = Product.query.all()
    return jsonify([{
        'id': p.id,
        'name': p.name,
        'description': p.description,
        'price': p.price,
        'stock': p.stock,
        'image_url': url_for('static', filename='images/' + p.image_url, _external=True) if p.image_url else None,
        'seller_id': p.seller_id
    } for p in products])

@app.route('/api/add_to_cart', methods=['POST'])
def api_add_to_cart():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    data = request.get_json()
    product_id = data.get('product_id')
    quantity = data.get('quantity', 1)
    cart_item = Cart.query.filter_by(user_id=session['user_id'], product_id=product_id).first()
    if cart_item:
        cart_item.quantity += quantity
    else:
        cart_item = Cart(user_id=session['user_id'], product_id=product_id, quantity=quantity)
        db.session.add(cart_item)
    db.session.commit()
    return jsonify({'message': 'Added to cart'})

@app.route('/api/cart')
def api_cart():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    cart_items = Cart.query.filter_by(user_id=session['user_id']).all()
    total = sum(item.product.price * item.quantity for item in cart_items)
    return jsonify({
        'items': [{
            'id': item.id,
            'product_id': item.product_id,
            'name': item.product.name,
            'price': item.product.price,
            'quantity': item.quantity,
            'subtotal': item.product.price * item.quantity
        } for item in cart_items],
        'total': total
    })

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Create admin user if not exists
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', email='admin@example.com', role='admin')
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
     socketio.run(app, host="0.0.0.0", port=5000, debug=True, use_reloader=False)

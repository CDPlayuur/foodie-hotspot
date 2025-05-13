from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime
from flask_cors import CORS  # Import CORS


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL',
                                                     'postgresql://postgres:aQigGXxWbTiiIBdbTYIFmPBXkJgypWBL@postgres.railway.internal:5432/railway')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'your_secret_key') #  Use a secure, random key in production

# Enable CORS for all routes and all origins
CORS(app, supports_credentials=True)


# Define the User model (if using SQLAlchemy)
class User(db.Model):
    __tablename__ = 'users'
    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    role = db.Column(db.String(20), nullable=False)
    display_name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.TIMESTAMP, default=datetime.utcnow)
    vendor = db.relationship('Vendor', uselist=False, back_populates='user')

    def __init__(self, username, password, email, role, display_name):
        self.username = username
        self.password = password
        self.email = email
        self.role = role
        self.display_name = display_name



# Define the Vendor model (if using SQLAlchemy)
class Vendor(db.Model):
    __tablename__ = 'vendors'
    vendor_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), unique=True, nullable=False)
    shop_name = db.Column(db.String(200))
    shop_description = db.Column(db.Text)
    app_status = db.Column(db.String(20), nullable=False)
    approved_at = db.Column(db.TIMESTAMP)
    shop_logo = db.Column(db.String(255))  # New column to store the logo URL or path
    user = db.relationship('User', back_populates='vendor')
    products = db.relationship('Product', back_populates='vendor')

    def __init__(self, user_id, shop_name, shop_description, app_status):
        self.user_id = user_id
        self.shop_name = shop_name
        self.shop_description = shop_description
        self.app_status = app_status



# Define the Product model
class Product(db.Model):
    __tablename__ = 'products'
    product_id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer, db.ForeignKey('vendors.vendor_id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    stock = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.TIMESTAMP, default=datetime.utcnow)
    vendor = db.relationship('Vendor', back_populates='products')
    categories = db.relationship('Category', secondary='product_categories',
                                 back_populates='products')

    def __init__(self, vendor_id, name, description, price, stock):
        self.vendor_id = vendor_id
        self.name = name
        self.description = description
        self.price = price
        self.stock = stock



class Order(db.Model):
    __tablename__ = 'orders'
    order_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    order_status = db.Column(db.String(20), nullable=False)
    order_date = db.Column(db.TIMESTAMP, default=datetime.utcnow)
    total_amount = db.Column(db.Numeric(10, 2), nullable=False)
    user = db.relationship('User')
    items = db.relationship('OrderItem', back_populates='order')



class OrderItem(db.Model):
    __tablename__ = 'order_items'
    order_id = db.Column(db.Integer, db.ForeignKey('orders.order_id'), primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.product_id'), primary_key=True)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    order = db.relationship('Order', back_populates='items')
    product = db.relationship('Product')



class ProductKeyword(db.Model):
    __tablename__ = 'product_keywords'
    product_id = db.Column(db.Integer, db.ForeignKey('products.product_id'), primary_key=True)
    keyword = db.Column(db.String(50), primary_key=True)
    product = db.relationship('Product', backref='keywords')



# Define the Category model
class Category(db.Model):
    __tablename__ = 'categories'
    category_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    products = db.relationship('Product', secondary='product_categories',
                                 back_populates='categories')

    def __init__(self, name, description):
        self.name = name
        self.description = description



# Define the Product_Categories association table
product_categories = db.Table(
    'product_categories',
    db.Column('product_id', db.Integer, db.ForeignKey('products.product_id'), primary_key=True),
    db.Column('category_id', db.Integer, db.ForeignKey('categories.category_id'), primary_key=True)
)


#  Flask route to handle user login
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    # Input validation
    if not username or not password:
        return jsonify({'success': False, 'message': 'Username and password are required.'}), 400

    user = User.query.filter_by(username=username).first()
    if user:
        # **IMPORTANT:  PRODUCTION/SECURE VERSION**
        if check_password_hash(user.password, password):
            # Store user information in the session
            session['user_id'] = user.user_id
            session['username'] = user.username
            session['role'] = user.role
            session['display_name'] = user.display_name # Store display name
            return jsonify({
                'success': True,
                'message': 'Login successful!',
                'username': user.username,
                'role': user.role,
                'display_name': user.display_name
            }), 200
        else:
            return jsonify({'success': False, 'message': 'Invalid credentials.'}), 401
    else:
        return jsonify({'success': False, 'message': 'Invalid credentials.'}), 401



# Flask route to handle user registration
@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    email = data.get('email')
    role = data.get('role')
    display_name = data.get('displayName')

    # Input validation
    if not username or not password or not email or not role or not display_name:
        return jsonify({'success': False, 'message': 'All fields are required.'}), 400
    if role not in ('customer', 'vendor', 'admin'):
        return jsonify({'success': False, 'message': 'Invalid role.'}), 400

    # Check if username or email already exists
    if User.query.filter_by(username=username).first():
        return jsonify({'success': False, 'message': 'Username already exists.'}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({'success': False, 'message': 'Email already exists.'}), 400

    hashed_password = generate_password_hash(password, method='sha256')
    new_user = User(username, hashed_password, email, role, display_name)
    db.session.add(new_user)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Registration successful!', 'username': username, 'role': role, 'displayName': display_name}), 201



def fetch_products_by_vendor(vendor_id):
    """Fetches products for a given vendor_id from the database."""
    products = Product.query.join(Vendor).filter(Product.vendor_id == vendor_id).all()

    # Convert the results to a list of dictionaries for easier use in the template
    product_list = []
    for product in products:
        product_list.append(
            {
                "product_id": product.product_id,
                "name": product.name,
                "description": product.description,
                "price": str(product.price),  # Convert to string for JSON
                "stock": product.stock,
                "shop_name": product.vendor.shop_name,
                "vendor_id": product.vendor_id
            }
        )
    return product_list



@app.route('/api/products/vendor/<int:vendor_id>', methods=['GET'])
def get_vendor_products(vendor_id):
    products = fetch_products_by_vendor(vendor_id)  # Fetch products from the database
    if products:
        return jsonify({'success': True, 'products': products}), 200
    else:
        return jsonify({'success': False, 'message': 'No products found for this vendor.'}), 404



@app.route('/browse', methods=['GET'])
def browse_shops():
    """
    Handles the display of shops based on user role.
    """
    if 'user_id' not in session:
        # If the user is not logged in, display the default browse shops page
        shops = Vendor.query.all()
        return render_template('browse_shops.html', shops=shops, user_role=None)  # Pass shops data

    user_role = session['role']
    user_id = session['user_id']

    if user_role == 'vendor':
        # Check if the vendor has a shop.
        vendor_shop = Vendor.query.filter_by(user_id=user_id).first()
        if vendor_shop:
            # If the vendor has a shop, show the shop's products or shop management page.
            products = fetch_products_by_vendor(vendor_shop.vendor_id)
            return render_template('shop_products.html', shop=vendor_shop, products=products, user_role=user_role)  # Show vendor's shop
        else:
            #if vendor doesn't have a shop, show the page to create a new shop.
            return render_template('vendor_create_shop.html', user_role=user_role) #render the new template
    elif user_role == 'admin':
        # If the user is an admin, show the admin page to approve/deny shops.
        pending_shops = Vendor.query.filter_by(app_status='pending').all()
        return render_template('admin_approve_shops.html', pending_shops=pending_shops, user_role=user_role)  # different template for admin
    else:
        # For customers or other roles, show the default browse shops page.
        shops = Vendor.query.all()
        return render_template('browse_shops.html', shops=shops, user_role=user_role)  # Pass shops data


@app.route('/api/create_shop', methods=['POST'])
def create_shop():
    """
    Handles the creation of a new vendor shop.
    """
    if 'user_id' not in session or session['role'] != 'vendor':
        return jsonify({'success': False, 'message': 'Unauthorized access.'}), 403

    user_id = session['user_id']
    shop_name = request.form.get('shop_name')  # Use request.form for form data
    shop_description = request.form.get('shop_description')

    if not shop_name or not shop_description:
        return jsonify({'success': False, 'message': 'Shop name and description are required.'}), 400

    # Check if the user already has a shop
    if Vendor.query.filter_by(user_id=user_id).first():
        return jsonify({'success': False, 'message': 'You already have a shop.'}), 400

    new_shop = Vendor(user_id=user_id, shop_name=shop_name, shop_description=shop_description, app_status='pending')
    db.session.add(new_shop)
    db.session.commit()

    return jsonify({'success': True, 'message': 'Shop created successfully!  Your application is pending approval.'}), 200


@app.route('/api/approve_shop/<int:vendor_id>', methods=['POST'])
def approve_shop(vendor_id):
    """
    Handles the approval of a vendor shop by an admin.
    """
    if 'user_id' not in session or session['role'] != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized access.'}), 403

    shop = Vendor.query.get(vendor_id)
    if not shop:
        return jsonify({'success': False, 'message': 'Shop not found.'}), 404

    if shop.app_status != 'pending':
        return jsonify({'success': False, 'message': 'Shop is not pending approval.'}), 400

    shop.app_status = 'approved'
    shop.approved_at = datetime.utcnow()
    db.session.commit()

    return jsonify({'success': True, 'message': 'Shop approved successfully.'}), 200

@app.route('/api/deny_shop/<int:vendor_id>', methods=['POST'])
def deny_shop(vendor_id):
    """Handles the denial of a vendor shop by an admin."""
    if 'user_id' not in session or session['role'] != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized access.'}), 403

    shop = Vendor.query.get(vendor_id)
    if not shop:
        return jsonify({'success': False, 'message': 'Shop not found.'}), 404

    if shop.app_status != 'pending':
        return jsonify({'success': False, 'message': 'Shop is not pending approval.'}), 400

    shop.app_status = 'denied'  #  set status
    db.session.commit()
    return jsonify({'success': True, 'message': 'Shop denied successfully.'}), 200



@app.route('/logout')
def logout():
    """
    Handles user logout.  Clears the session.
    """
    session.clear()
    return redirect(url_for('browse_shops'))  # Redirect to the browse page after logout



if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=5000, debug=False)

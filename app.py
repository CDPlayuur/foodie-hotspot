from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime
from flask_cors import CORS


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'postgresql://postgres:aQigGXxWbTiiIBdbTYIFmPBXkJgypWBL@postgres.railway.internal:5432/railway')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

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
    vendor = db.relationship('Vendor', uselist=False, back_populates='user') # Added for relationship

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
    shop_logo = db.Column(db.String(255))
    user = db.relationship('User', back_populates='vendor') # Added relationship
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
    categories = db.relationship('Category', secondary='product_categories', back_populates='categories')

    def __init__(self, vendor_id, name, description, price, stock):
        self.vendor_id = vendor_id
        self.name = name
        self.description = description
        self.price = price
        self.stock = stock


# Define the Category model
class Category(db.Model):
    __tablename__ = 'categories'
    category_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    products = db.relationship('Product', secondary='product_categories', back_populates='categories')

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
    print("Inside /api/login route") #Added for debugging
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    # Input validation
    if not username or not password:
        return jsonify({'success': False, 'message': 'Username and password are required.'}), 400

    user = User.query.filter_by(username=username).first()
    if user and check_password_hash(user.password, password):
        return jsonify({
            'success': True,
            'message': 'Login successful!',
            'username': user.username,
            'role': user.role
        }), 200
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
    return jsonify({'success': True, 'message': 'Registration successful!', 'username': username, 'role': role}), 201

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



if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    #  app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
    app.run(host="0.0.0.0", port=5000, debug=True)

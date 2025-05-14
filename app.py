from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime
from flask_cors import CORS
import uuid


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'postgresql://postgres:aQigGXxWbTiiIBdbTYIFmPBXkJgypWBL@postgres.railway.internal:5432/railway')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Enable CORS for all routes and all origins
CORS(app, supports_credentials=True)

# Define the User model
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
    shop_logo = db.Column(db.String(255))
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
    categories = db.relationship('Category', secondary='product_categories', back_populates='products')

    def __init__(self, vendor_id, name, description, price, stock):
        self.vendor_id = vendor_id
        self.name = name
        self.description = description
        self.price = price
        self.stock = stock


class Order(db.Model):
    __tablename__ = 'orders'
    order_id = db.Column(db.String(36), primary_key=True, default=str(uuid.uuid4)) # Use UUID for order ID
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    order_status = db.Column(db.String(20), nullable=False, default='Placed')
    order_date = db.Column(db.TIMESTAMP, default=datetime.utcnow)
    total_amount = db.Column(db.Numeric(10, 2), nullable=False)
    delivery_address = db.Column(db.String(255))
    payment_method = db.Column(db.String(50))
    user = db.relationship('User', back_populates='orders')
    items = db.relationship('OrderItem', back_populates='order')

    def __init__(self, user_id, total_amount, delivery_address, payment_method):
        self.user_id = user_id
        self.total_amount = total_amount
        self.delivery_address = delivery_address
        self.payment_method = payment_method


class OrderItem(db.Model):
    __tablename__ = 'order_items'
    order_item_id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(36), db.ForeignKey('orders.order_id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.product_id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False) # Price at the time of order
    order = db.relationship('Order', back_populates='items')
    product = db.relationship('Product')

    def __init__(self, order_id, product_id, quantity, price):
        self.order_id = order_id
        self.product_id = product_id
        self.quantity = quantity
        self.price = price


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
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    # Input validation
    if not username or not password:
        return jsonify({'success': False, 'message': 'Username and password are required.'}), 400

    user = User.query.filter_by(username=username).first()
    if user:
        # *********************************************************************************
        # WARNING:  THIS IS INSECURE!  DO NOT USE THIS IN PRODUCTION!
        #          This code bypasses password hashing and compares plain text passwords.
        #          It is ONLY appropriate for a school project with no real-world use.
        # *********************************************************************************
        if user.password == password:
            return jsonify({
                'success': True,
                'message': 'Login successful!',
                'username': user.username,
                'role': user.role
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

    # *********************************************************************************
    # WARNING:  THIS IS INSECURE!  DO NOT USE THIS IN PRODUCTION!
    #          For a real application, you MUST hash the password here:
    #          hashed_password = generate_password_hash(password, method='sha256')
    #          new_user = User(username, hashed_password, email, role, display_name)
    # *********************************************************************************
    new_user = User(username, password, email, role, display_name)
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
    print(f"Fetching products for vendor_id: {vendor_id}")
    products = fetch_products_by_vendor(vendor_id)
    print("Fetched products:", products)
    if products:
        return jsonify({'products': products}), 200
    else:
        return jsonify({'success': False, 'message': 'No products found for this vendor.'}), 404


@app.route('/api/vendors', methods=['GET'])
def get_vendors():
    """
    Retrieves all vendors from the database and returns them as a JSON list.
    """
    vendors = Vendor.query.all()
    vendor_list = []
    for vendor in vendors:
        pickup = vendor.approved_at is not None
        delivery = True

        vendor_list.append({
            'vendor_id': vendor.vendor_id,
            'shop_name': vendor.shop_name,
            'shop_description': vendor.shop_description,
            'app_status': vendor.app_status,
            'shop_logo': vendor.shop_logo,
            'pickup': pickup,
            'delivery': delivery,
        })

    return jsonify(vendor_list), 200

# New route to get vendor data along with products
@app.route('/api/vendor/<int:vendor_id>', methods=['GET'])
def get_vendor_data_with_products(vendor_id):
    """
    Retrieves a single vendor's data along with their products.
    """
    vendor = Vendor.query.get(vendor_id)  # Fetch the vendor by ID
    if not vendor:
        return jsonify({'success': False, 'message': 'Vendor not found.'}), 404

    # Fetch products for the vendor
    products = fetch_products_by_vendor(vendor_id)

    # Prepare the vendor data
    vendor_data = {
        'vendor_id': vendor.vendor_id,
        'shop_name': vendor.shop_name,
        'shop_description': vendor.shop_description,
        'app_status': vendor.app_status,
        'shop_logo': vendor.shop_logo,
        'pickup': vendor.approved_at is not None,
        'delivery': True, # Assuming delivery is true.  You may have this in your model.
        'products': products  # Include the products in the response
    }

    return jsonify(vendor_data), 200

@app.route('/api/place-order', methods=['POST'])
def place_order():
    """
    Handles the placement of a new order.
    """
    data = request.get_json()

    # Validate the incoming data
    if not data or 'user_id' not in data or 'items' not in data or 'total_amount' not in data or 'delivery_address' not in data or 'payment_method' not in data:
        return jsonify({'success': False, 'message': 'Invalid order data.  Missing required fields.'}), 400

    user_id = data['user_id']
    items = data['items']
    total_amount = data['total_amount']
    delivery_address = data['delivery_address']
    payment_method = data['payment_method']

    # Check if the user exists
    user = User.query.get(user_id)
    if not user:
        return jsonify({'success': False, 'message': 'User not found.'}), 404

    try:
        # 1. Create the Order
        new_order = Order(
            user_id=user_id,
            total_amount=total_amount,
            delivery_address=delivery_address,
            payment_method=payment_method
        )
        db.session.add(new_order)
        db.session.flush()  # Need to flush to get the order_id

        order_id = new_order.order_id

        # 2. Create the OrderItems
        for item in items:
            product_id = item['product_id']
            quantity = item['quantity']
            price = item['price']  # Important: Use the price from the cart item, not the current product price

            # Check if the product exists
            product = Product.query.get(product_id)
            if not product:
                db.session.rollback()
                return jsonify({'success': False, 'message': f'Product with ID {product_id} not found.'}), 400

             # Check if there is enough stock.
            if product.stock < quantity:
                db.session.rollback()
                return jsonify({'success': False, 'message': f'Insufficient stock for product {product.name}.'}), 400
            
            new_order_item = OrderItem(
                order_id=order_id,
                product_id=product_id,
                quantity=quantity,
                price=price
            )
            db.session.add(new_order_item)

            # 3. Reduce product stock.  Do this *after* creating the OrderItem
            product.stock -= quantity
            db.session.add(product)

        # Commit the transaction
        db.session.commit()

        return jsonify({'success': True, 'message': 'Order placed successfully!', 'order_id': order_id}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Failed to place order.', 'error': str(e)}), 500

#debuggin
@app.route('/api/products/all', methods=['GET'])
def get_all_products():
    products = Product.query.all()
    product_list = [{
        "product_id": p.product_id,
        "vendor_id": p.vendor_id,
        "name": p.name
    } for p in products]
    return jsonify(product_list), 200


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=5000, debug=False)

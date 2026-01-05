# E-commerce Business Logic Design

## Overview
This document outlines the business logic for the e-commerce application built with Flask and SQLite. The system handles user authentication, product management, shopping cart, and order processing.

## Module Structure

### 1. User Module
Handles user registration, authentication, and session management.

### 2. Product Module
Manages product catalog, inventory, and product details.

### 3. Cart Module
Handles shopping cart operations including add, remove, and quantity updates.

### 4. Order Module
Manages order creation, processing, and history.

## Data Structures

### Database Models

#### User
- id: Integer (Primary Key)
- username: String (Unique)
- email: String (Unique)
- password_hash: String
- role: String (Default: 'customer')  # 'customer', 'seller', 'admin'

#### Product
- id: Integer (Primary Key)
- name: String
- description: Text
- price: Float
- image_url: String (Optional)
- stock: Integer (Default: 0)
- seller_id: Integer (Foreign Key to User)

#### Cart
- id: Integer (Primary Key)
- user_id: Integer (Foreign Key to User)
- product_id: Integer (Foreign Key to Product)
- quantity: Integer

#### Order
- id: Integer (Primary Key)
- user_id: Integer (Foreign Key to User)
- total_price: Float
- status: String (Default: 'pending')
- created_at: DateTime

#### OrderItem
- id: Integer (Primary Key)
- order_id: Integer (Foreign Key to Order)
- product_id: Integer (Foreign Key to Product)
- quantity: Integer
- price: Float (Price at time of order)

### Session Data
- user_id: Integer
- username: String
- is_admin: Boolean

## Function Flows

### 1. User Registration
**Input:** username, email, password, role ('customer' or 'seller')
**Process:**
1. Validate input data
2. Check if username exists
3. Check if email exists
4. Hash password
5. Create user record with selected role
6. Commit to database
**Output:** Success message or error
**Edge Cases:**
- Duplicate username/email
- Invalid email format
- Weak password
- Invalid role selection

### 2. User Login
**Input:** username, password
**Process:**
1. Find user by username
2. Verify password
3. Set session data
4. Redirect to home
**Output:** Success or invalid credentials
**Edge Cases:**
- User not found
- Wrong password
- Account locked (future enhancement)

### 3. Display Products
**Route:** GET /
**Process:**
1. Query all products from database
2. Render product list template
**Output:** Product listing page

### 4. View Product Details
**Route:** GET /product/<product_id>
**Process:**
1. Query product by ID
2. Handle 404 if not found
3. Render product detail template
**Output:** Product detail page
**Edge Cases:** Product not found

### 5. Add to Cart
**Route:** POST /add_to_cart/<product_id>
**Input:** quantity
**Process:**
1. Check user authentication
2. Validate quantity
3. Check if item already in cart
4. Update quantity or create new cart item
5. Commit to database
**Output:** Success message
**Edge Cases:**
- Not logged in
- Invalid quantity
- Insufficient stock (future enhancement)

### 6. View Cart
**Route:** GET /cart
**Process:**
1. Check authentication
2. Query user's cart items
3. Calculate total price
4. Render cart template
**Output:** Cart page with items and total

### 7. Remove from Cart
**Route:** GET /remove_from_cart/<cart_id>
**Process:**
1. Check authentication
2. Verify cart item belongs to user
3. Delete cart item
4. Commit changes
**Output:** Redirect to cart
**Edge Cases:** Cart item not found or not owned by user

### 8. Checkout
**Route:** POST /checkout
**Process:**
1. Check authentication
2. Get cart items
3. Check cart not empty
4. Calculate total
5. Create order record
6. Create order items
7. Reduce product stock
8. Clear cart
9. Commit transaction
**Output:** Success message, redirect to orders
**Edge Cases:**
- Empty cart
- Insufficient stock during checkout
- Database transaction failure

### 9. View Orders
**Route:** GET /orders
**Process:**
1. Check authentication
2. Query user's orders with items
3. Render orders template
**Output:** Order history page

### 10. Seller Add Product
**Route:** POST /seller/products
**Input:** Product data
**Process:**
1. Check seller permission
2. Validate form data
3. Create product record with seller_id
4. Commit to database
**Output:** Success message
**Edge Cases:** Non-seller access, invalid data

### 11. Seller Manage Products
**Route:** GET /seller/products
**Process:**
1. Check seller permission
2. Query products by seller_id
3. Render seller product management page
**Output:** Product list for seller

### 12. Seller Delete Product
**Route:** GET /seller/delete/<product_id>
**Process:**
1. Check seller permission
2. Verify product belongs to seller
3. Delete product (consider cart/order implications)
4. Commit changes
**Output:** Success message
**Edge Cases:** Product not owned by seller, product in active carts/orders

### 13. Admin Panel (Global Management)
**Route:** GET/POST /admin
**Process:**
1. Check admin permission
2. Allow global product/user management
**Output:** Admin dashboard

## Routes/Endpoints

| Route | Method | Description | Authentication |
|-------|--------|-------------|----------------|
| / | GET | Home page with products | None |
| /product/<id> | GET | Product details | None |
| /login | GET/POST | User login | None |
| /register | GET/POST | User registration | None |
| /logout | GET | User logout | Required |
| /cart | GET | View cart | Required |
| /add_to_cart/<id> | POST | Add item to cart | Required |
| /remove_from_cart/<id> | GET | Remove cart item | Required |
| /checkout | POST | Process order | Required |
| /orders | GET | Order history | Required |
| /seller/products | GET/POST | Seller product management | Seller |
| /seller/delete/<id> | GET | Seller delete product | Seller |
| /admin | GET/POST | Admin panel | Admin |
| /admin/delete/<id> | GET | Admin delete product | Admin |

## Error Handling and Edge Cases

### Authentication
- Redirect to login for protected routes
- Flash messages for access denied

### Validation
- Form validation using WTForms
- Database constraints (unique fields)
- Business logic validation (stock checks)

### Database Operations
- Use transactions for multi-step operations (checkout)
- Handle database errors gracefully
- Rollback on failures

### Stock Management
- Check stock before adding to cart
- Reduce stock on successful checkout
- Prevent overselling

### Security
- Password hashing
- Session management
- Admin permission checks
- CSRF protection via Flask-WTF

## Role-Based Access Control

### Customer
- Register as customer
- View products
- Add to cart
- Checkout and view orders
- Cannot add/modify products

### Seller
- Register as seller
- All customer permissions
- Add/manage own products
- Set prices and stock
- View sales/orders for own products

### Admin
- All permissions
- Manage all users and products
- Global system administration

## Future Enhancements
- Order status updates
- Payment integration
- Email notifications
- Product categories
- Search and filtering
- Inventory alerts
- User profiles
- Order cancellation
- Product reviews
- Seller dashboards with analytics
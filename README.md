# 🛒 Lucky Cart - Modern E-Commerce Platform

![Lucky Cart Banner](https://images.unsplash.com/photo-1557821552-17105176677c?auto=format&fit=crop&q=80&w=1600&h=400)

[![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.0+-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![SQLite](https://img.shields.io/badge/SQLite-3-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

**Lucky Cart** is a robust, full-stack e-commerce application built with Flask. It provides a seamless experience for both consumers and sellers, featuring secure authentication, real-time inventory management, and a premium user interface.

---

## 🌟 Key Features

### 🛍️ For Consumers
- **Smart Marketplace**: Browse products with advanced filtering by category, price, and name.
- **Dynamic Shopping Cart**: Real-time stock revalidation and 30-minute item reservation.
- **Loyalty Program**: Earn points on every purchase and unlock exclusive badges.
- **Secure Checkout**: Simulated wallet system with address management and order receipts.
- **Wishlist**: Save items for later or move them from your cart to your wishlist.
- **Notifications**: Get instant alerts for order confirmations and status updates.

### 🏪 For Sellers
- **Inventory Dashboard**: List new products with image uploads and track stock levels.
- **Sales Analytics**: Monitor orders and track earnings directly from the seller portal.
- **Order Management**: View and process customer orders efficiently.

### 🛡️ Security & Performance
- **JWT & Session Auth**: Multi-layered authentication for maximum security.
- **Rate Limiting**: Protection against brute-force attacks and spam.
- **CSP & CSRF Protection**: Hardened against common web vulnerabilities using Flask-Talisman.
- **PWA Ready**: Mobile-optimized with Service Worker support for an app-like experience.

---

## 🛠️ Tech Stack

- **Backend**: Python, Flask, SQLAlchemy
- **Frontend**: HTML5, CSS3 (Tailwind CSS), Vanilla JavaScript
- **Security**: Flask-Bcrypt, Flask-JWT-Extended, Flask-Limiter, Flask-Talisman
- **Database**: SQLite (Development)
- **Forms**: Flask-WTF

---

## 🚀 Getting Started

### Prerequisites
- Python 3.8 or higher
- pip (Python package installer)

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/kartikeya7609/Flask_Ecommerce.git
   cd Lucky_Cart
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
   *(Note: Ensure you have `Flask`, `Flask-SQLAlchemy`, `Flask-Bcrypt`, `Flask-Login`, `Flask-WTF`, `Flask-Limiter`, `Flask-Talisman`, and `Flask-JWT-Extended` installed.)*

4. **Initialize the database**:
   ```bash
   python init_db.py
   ```

5. **Run the application**:
   ```bash
   python app.py
   ```
   Access the app at `http://127.0.0.1:5000`

---

## 🖥️ Admin Access
For testing purposes, a global administrator account is available:
- **Username**: `admin1234`
- **Password**: `admin`

---

## 📁 Project Structure

```text
├── app.py              # Main application logic and routes
├── forms.py            # WTForms definitions
├── init_db.py          # Database initialization script
├── static/             # CSS, JS, and uploaded images
│   ├── uploads/        # Product images
│   ├── sw.js           # Service Worker for PWA
│   └── manifest.json   # PWA manifest
├── templates/          # Jinja2 HTML templates
└── instance/           # SQLite database file
```

---

## 🤝 Contributing
Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---
*Created with ❤️ by [Kartikeya](https://github.com/kartikeya7609)*

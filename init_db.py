# init_db.py

# We import the 'app', 'db', and 'Item' from your main app.py file
from app import app, db, Item

# This is the data you want to add
items_to_add = [
    {
        'name': 'Phone', 
        'barcode': '893212299897', 
        'price': 500,
        'description': 'A high-quality smartphone.',  # Added description
        'image_file': 'phone.jpg'                  # Added image_file
    },
    {
        'name': 'Laptop', 
        'barcode': '123985473165', 
        'price': 900,
        'description': 'A powerful laptop for work.', # Added description
        'image_file': 'laptop.jpg'                 # Added image_file
    },
    {
        'name': 'Keyboard', 
        'barcode': '231985128446', 
        'price': 150,
        'description': 'A mechanical keyboard.',      # Added description
        'image_file': 'keyboard.jpg'               # Added image_file
    }
]

# --- This is the important part ---
# This "with" block sets up the application context
# so that db commands can work.
with app.app_context():
    print("Dropping all tables...")
    db.drop_all()  # Deletes all existing tables (for a fresh start)
    
    print("Creating all tables...")
    db.create_all()  # Creates new tables based on your models

    print("Adding items to the database...")
    for item_data in items_to_add:
        # Create an Item object
        item = Item(
            name=item_data['name'],
            price=item_data['price'],
            barcode=item_data['barcode'],
            description=item_data['description'],
            image_file=item_data['image_file']
        )
        # Add it to the session
        db.session.add(item)
    
    # Commit all the new items to the database
    db.session.commit()
    print("Database setup complete!")
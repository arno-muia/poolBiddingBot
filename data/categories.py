import psycopg2
import os

# Get the database URL from environment variables (Render PostgreSQL)
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://study_pool_bidding_bot_user:AcLQMhzKAjgPWDXu5pS0HR8Lzj2cdsP2@dpg-cv28is56l47c73flv18g-a/study_pool_bidding_bot")

# Update database connection to PostgreSQL (Render)
def get_db_connection():
    try:
        connection = psycopg2.connect(DATABASE_URL, sslmode='require')
        return connection
    except psycopg2.Error as e:
        print(f"Error connecting to PostgreSQL database: {e}")
        return None

# Load valid categories from PostgreSQL database
def load_valid_categories_from_db():
    conn = get_db_connection()  # Get PostgreSQL connection
    if not conn:
        return []

    try:
        cursor = conn.cursor()
        cursor.execute('SELECT category FROM valid_categories')
        rows = cursor.fetchall()
        valid_categories = [row[0] for row in rows]
        return valid_categories
    except psycopg2.Error as e:
        print(f"Error fetching categories: {e}")
        return []
    finally:
        conn.close()  # Ensure connection is closed

# Add a new category to the database if it does not already exist
def add_category_to_db(category):
    conn = get_db_connection()  # Get PostgreSQL connection
    if not conn:
        return

    try:
        cursor = conn.cursor()

        # Check if the category already exists in the database
        cursor.execute('SELECT COUNT(*) FROM valid_categories WHERE LOWER(category) = LOWER(%s)', (category,))
        count = cursor.fetchone()[0]
        
        if count == 0:  # Category does not exist, so insert it
            cursor.execute('INSERT INTO valid_categories (category) VALUES (%s)', (category,))
            conn.commit()
            print(f"Category '{category}' added to database.")  # Debugging message
    except psycopg2.Error as e:
        print(f"Error inserting category: {e}")
    finally:
        conn.close()  # Ensure connection is closed

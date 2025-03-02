import psycopg2

# Update database connection to PostgreSQL
def get_db_connection():
    try:
        connection = psycopg2.connect(
            dbname="avitor",  # Replace with your database name
            user="postgres",   # Replace with your username
            password="arno", # Replace with your password
            host="localhost",        # Use the appropriate host
            port="5432"              # Default PostgreSQL port
        )
        return connection
    except psycopg2.Error as e:
        print(f"Error connecting to PostgreSQL database: {e}")
        return None

# Load valid categories from PostgreSQL database
def load_valid_categories_from_db():
    conn = get_db_connection()  # Get PostgreSQL connection
    if not conn:
        return []

    cursor = conn.cursor()
    cursor.execute('SELECT category FROM valid_categories')
    rows = cursor.fetchall()

    valid_categories = [row[0] for row in rows]
    conn.close()

    return valid_categories

# Add a new category to the database if it does not already exist
def add_category_to_db(category):
    conn = get_db_connection()  # Get PostgreSQL connection
    if not conn:
        return

    cursor = conn.cursor()

    # Check if the category already exists in the database
    cursor.execute('SELECT COUNT(*) FROM valid_categories WHERE LOWER(category) = LOWER(%s)', (category,))
    count = cursor.fetchone()[0]
    
    if count == 0:  # Category does not exist, so insert it
        cursor.execute('INSERT INTO valid_categories (category) VALUES (%s)', (category,))
        conn.commit()
        print(f"Category '{category}' added to database.")  # Debugging message

    conn.close()



    
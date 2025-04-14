#!/usr/bin/env python
"""Script to reset the SQLite database and migration records."""
import os
import shutil


def reset_db():
    """Reset the SQLite database and migration records."""
    # Path to the db.sqlite3 file
    db_path = os.path.join(os.getcwd(), 'db.sqlite3')
    
    # Delete the database file if it exists
    if os.path.exists(db_path):
        print(f"Deleting database file: {db_path}")
        os.remove(db_path)
        print("Database file deleted successfully.")
    else:
        print("Database file does not exist.")
    
    # Reset migration records for all apps
    apps = [
        'users', 'accounts', 'accountants', 'connections', 
        'financials', 'integrations', 'notifications'
    ]
    
    for app in apps:
        migrations_dir = os.path.join(os.getcwd(), 'apps', app, 'migrations')
        if os.path.exists(migrations_dir):
            # Preserve __init__.py and 0001_initial.py
            init_file = os.path.join(migrations_dir, '__init__.py')
            initial_file = os.path.join(migrations_dir, '0001_initial.py')
            
            # Make sure __init__.py exists
            if not os.path.exists(init_file):
                with open(init_file, 'w') as f:
                    pass
            
            # Delete all migration files except __init__.py and 0001_initial.py
            for filename in os.listdir(migrations_dir):
                file_path = os.path.join(migrations_dir, filename)
                if os.path.isfile(file_path) and filename != '__init__.py' and filename != '0001_initial.py':
                    print(f"Deleting migration file: {file_path}")
                    os.remove(file_path)
            
            print(f"Reset migration records for app: {app}")
    
    print("Database and migration records reset successfully.")


if __name__ == "__main__":
    reset_db() 
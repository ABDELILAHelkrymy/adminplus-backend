#!/usr/bin/env python
"""Script to fix encoding in settings files."""
import os
import codecs

def fix_file_encoding(filepath):
    """Fix the encoding of a file from UTF-16 to UTF-8."""
    print(f"Fixing encoding for {filepath}")
    try:
        # First try to read as UTF-16
        try:
            with codecs.open(filepath, 'r', encoding='utf-16-le') as f:
                content = f.read()
        except UnicodeError:
            # If that fails, try UTF-16-BE
            with codecs.open(filepath, 'r', encoding='utf-16-be') as f:
                content = f.read()
        
        # Write as UTF-8
        with codecs.open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"Successfully fixed encoding for {filepath}")
        return True
    except Exception as e:
        print(f"Error fixing encoding for {filepath}: {e}")
        return False

def main():
    """Main function."""
    settings_dir = os.path.join('core', 'settings')
    settings_files = [
        os.path.join(settings_dir, '__init__.py'),
        os.path.join(settings_dir, 'base.py'),
        os.path.join(settings_dir, 'development.py'),
        os.path.join(settings_dir, 'production.py'),
    ]
    
    for filepath in settings_files:
        fix_file_encoding(filepath)

if __name__ == "__main__":
    main() 
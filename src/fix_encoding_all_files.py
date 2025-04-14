#!/usr/bin/env python
"""Script to fix encoding in all Python files."""
import os
import codecs
import sys

def fix_file_encoding(filepath):
    """Fix the encoding of a file from UTF-16 to UTF-8 or remove null bytes."""
    print(f"Checking encoding for {filepath}")
    try:
        # First check if file has null bytes and fix it
        with open(filepath, 'rb') as f:
            content = f.read()
        
        if b'\x00' in content:
            # Found null bytes, fix the file
            print(f"Found null bytes in {filepath}, fixing...")
            try:
                # Try to read as UTF-16
                decoded = None
                try:
                    decoded = content.decode('utf-16-le')
                except UnicodeDecodeError:
                    try:
                        decoded = content.decode('utf-16-be')
                    except UnicodeDecodeError:
                        # Remove null bytes directly if decode fails
                        decoded = content.replace(b'\x00', b'').decode('utf-8', errors='ignore')
                
                # Write as UTF-8
                with codecs.open(filepath, 'w', encoding='utf-8') as f:
                    f.write(decoded)
                
                print(f"Successfully fixed encoding for {filepath}")
                return True
            except Exception as e:
                print(f"Error fixing encoding for {filepath}: {e}")
                return False
    except Exception as e:
        print(f"Error checking encoding for {filepath}: {e}")
        return False
    
    return True  # No need to fix

def find_py_files(directory):
    """Find all Python files in the given directory recursively."""
    py_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                py_files.append(os.path.join(root, file))
    return py_files

def main():
    """Main function."""
    # Get source directory from command line or use current directory
    source_dir = sys.argv[1] if len(sys.argv) > 1 else '.'
    
    # Find all Python files
    py_files = find_py_files(source_dir)
    print(f"Found {len(py_files)} Python files")
    
    # Fix encoding for each file
    fixed_count = 0
    for filepath in py_files:
        if fix_file_encoding(filepath):
            fixed_count += 1
    
    print(f"Fixed encoding for {fixed_count} files")

if __name__ == "__main__":
    main() 
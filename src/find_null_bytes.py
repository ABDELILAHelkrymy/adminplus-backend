#!/usr/bin/env python
"""Script to find null bytes in Python files."""
import os

def check_file_for_null_bytes(filepath):
    """Check if a file contains null bytes."""
    print(f"Checking {filepath}")
    try:
        with open(filepath, 'rb') as f:
            content = f.read()
            if b'\x00' in content:
                print(f"Found null bytes in {filepath}")
                # Find positions of null bytes
                positions = [i for i, byte in enumerate(content) if byte == 0]
                print(f"Null bytes found at positions: {positions}")
                
                # Print context around the null byte
                for pos in positions:
                    start = max(0, pos - 20)
                    end = min(len(content), pos + 20)
                    context = content[start:end]
                    print(f"Context around position {pos}:")
                    print(repr(context))
                return True
            else:
                print(f"No null bytes found in {filepath}")
                return False
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return False

def fix_file(filepath):
    """Remove null bytes from a file."""
    print(f"Fixing {filepath}")
    try:
        with open(filepath, 'rb') as f:
            content = f.read()
        
        # Remove null bytes
        fixed_content = content.replace(b'\x00', b'')
        
        with open(filepath, 'wb') as f:
            f.write(fixed_content)
        
        print(f"Fixed {filepath}")
        return True
    except Exception as e:
        print(f"Error fixing {filepath}: {e}")
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
        if check_file_for_null_bytes(filepath):
            fix_file(filepath)

if __name__ == "__main__":
    main() 
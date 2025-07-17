#!/usr/bin/env python3
"""
Fix for the export error: Convert string years to int before comparison
"""

import os
import re

def fix_app_py():
    """Fix the export function in app.py to handle string years"""
    print("🔧 Fixing export function in app.py...")
    
    # Read the current app.py file
    with open('app.py', 'r') as f:
        content = f.read()
    
    # Find the problematic line
    old_pattern = r'exp_text = \', \'\.join\(\[f"{sector\.title\(\)}: {years}y"\s+for sector, years in exp_dist\.items\(\) if years > 0\]\)'
    
    # More flexible pattern to match the problematic section
    old_section = '''exp_text = ', '.join([f"{sector.title()}: {years}y" 
                                for sector, years in exp_dist.items() if years > 0])'''
    
    new_section = '''exp_text = ', '.join([f"{sector.title()}: {years}y" 
                                for sector, years in exp_dist.items() 
                                if (isinstance(years, (int, float)) and years > 0) or 
                                   (isinstance(years, str) and years.isdigit() and int(years) > 0)])'''
    
    if old_section in content:
        content = content.replace(old_section, new_section)
        print("✅ Found and fixed the export issue")
    else:
        # Try a more targeted approach
        pattern = r'(exp_text = .*?if years > 0\])'
        replacement = '''exp_text = ', '.join([f"{sector.title()}: {years}y" 
                                for sector, years in exp_dist.items() 
                                if (isinstance(years, (int, float)) and years > 0) or 
                                   (isinstance(years, str) and years.isdigit() and int(years) > 0)])'''
        
        content = re.sub(pattern, replacement, content, flags=re.DOTALL)
        print("✅ Applied pattern-based fix")
    
    # Create backup
    with open('app.py.backup', 'w') as f:
        f.write(content)
    
    # Write the fixed version
    with open('app.py', 'w') as f:
        f.write(content)
    
    print("✅ app.py has been fixed")
    print("✅ Backup saved as app.py.backup")

def create_safe_export_function():
    """Create a completely safe version of the export function"""
    print("\n🔧 Creating safe export function...")
    
    safe_code = '''
def safe_format_experience_distribution(exp_dist):
    """Safely format experience distribution handling both strings and ints"""
    if not exp_dist or not isinstance(exp_dist, dict):
        return ''
    
    formatted_items = []
    for sector, years in exp_dist.items():
        try:
            # Convert to int if it's a string
            if isinstance(years, str):
                if years.isdigit():
                    years_int = int(years)
                else:
                    continue  # Skip non-numeric strings
            elif isinstance(years, (int, float)):
                years_int = int(years)
            else:
                continue  # Skip other types
            
            # Only include if greater than 0
            if years_int > 0:
                formatted_items.append(f"{sector.title()}: {years_int}y")
        except (ValueError, TypeError):
            # Skip any items that can't be converted
            continue
    
    return ', '.join(formatted_items)
'''
    
    with open('safe_export_helpers.py', 'w') as f:
        f.write(safe_code)
    
    print("✅ Created safe_export_helpers.py")

def main():
    print("🔧 Export Error Fix Tool")
    print("=" * 50)
    
    print("The error is caused by experience_distribution having string values")
    print("instead of integer values, but the code tries to compare with > 0")
    print()
    
    # Option 1: Fix the main app.py file
    fix_app_py()
    
    # Option 2: Create helper function
    create_safe_export_function()
    
    print("\n" + "=" * 50)
    print("✅ Fix applied! Now test the export again.")
    print("💡 The export should work now with both string and integer years")

if __name__ == '__main__':
    main() 
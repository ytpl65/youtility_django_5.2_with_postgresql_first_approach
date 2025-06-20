#!/usr/bin/env python3
"""
Script to add safe JSON parsing utility to all manager files
and fix JSON parsing issues across the codebase.
"""

import os
import re

# Utility function to add to each manager file
UTILITY_FUNCTION = '''
import json
import logging
import urllib.parse
from datetime import datetime, date, timedelta

def safe_json_parse_params(request_get, param_name='params'):
    """
    Safely parse JSON parameters from request.GET.
    Returns empty dict if parsing fails.
    """
    logger = logging.getLogger(__name__)
    
    params_raw = request_get.get(param_name, '{}')
    
    if params_raw in ['null', None, '']:
        return {}
    
    try:
        # URL decode if necessary
        if params_raw.startswith('%'):
            params_raw = urllib.parse.unquote(params_raw)
        return json.loads(params_raw)
    except (json.JSONDecodeError, TypeError) as e:
        # Fallback to empty dict if JSON parsing fails
        logger.warning(f"Failed to parse {param_name} JSON: {params_raw}, error: {e}")
        return {}
'''

def fix_manager_file(file_path):
    """Fix JSON parsing issues in a manager file."""
    print(f"Fixing {file_path}...")
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Check if utility function already exists
    if 'safe_json_parse_params' in content:
        print(f"  - Utility function already exists in {file_path}")
        return
    
    # Add imports if not present
    if 'import urllib.parse' not in content:
        content = content.replace(
            'import json',
            'import json\nimport urllib.parse'
        )
    
    # Add utility function after imports
    import_section_end = content.find('\nclass ')
    if import_section_end != -1:
        before_imports = content[:import_section_end]
        after_imports = content[import_section_end:]
        
        # Add utility function
        utility_func = '''
def safe_json_parse_params(request_get, param_name='params'):
    """
    Safely parse JSON parameters from request.GET.
    Returns empty dict if parsing fails.
    """
    import json
    import urllib.parse
    import logging
    logger = logging.getLogger(__name__)
    
    params_raw = request_get.get(param_name, '{}')
    
    if params_raw in ['null', None, '']:
        return {}
    
    try:
        # URL decode if necessary
        if params_raw.startswith('%'):
            params_raw = urllib.parse.unquote(params_raw)
        return json.loads(params_raw)
    except (json.JSONDecodeError, TypeError) as e:
        # Fallback to empty dict if JSON parsing fails
        logger.warning(f"Failed to parse {param_name} JSON: {params_raw}, error: {e}")
        return {}
'''
        
        content = before_imports + utility_func + after_imports
    
    # Fix JSON parsing patterns
    patterns_to_fix = [
        (r"P = json\.loads\(R\.get\('params'\)\)", "P = safe_json_parse_params(R)"),
        (r"P = json\.loads\(request\.GET\.get\('params'\)\)", "P = safe_json_parse_params(request.GET)"),
        (r"P = json\.loads\(request\.GET\['params'\]\)", "P = safe_json_parse_params(request.GET)"),
        (r"json\.loads\(P\)", "safe_json_parse_params({'params': P}, 'params')"),
    ]
    
    for pattern, replacement in patterns_to_fix:
        content = re.sub(pattern, replacement, content)
    
    # Write back
    with open(file_path, 'w') as f:
        f.write(content)
    
    print(f"  - Fixed JSON parsing in {file_path}")

def main():
    """Main function to fix all manager files."""
    manager_files = [
        '/home/satyam/Documents/YOUTILITY-MIGRATION-FROM-4-5/YOUTILITY3/apps/attendance/managers.py',
        '/home/satyam/Documents/YOUTILITY-MIGRATION-FROM-4-5/YOUTILITY3/apps/y_helpdesk/managers.py',
        '/home/satyam/Documents/YOUTILITY-MIGRATION-FROM-4-5/YOUTILITY3/apps/work_order_management/managers.py',
    ]
    
    print("🔧 Fixing JSON parsing issues in manager files...")
    
    for file_path in manager_files:
        if os.path.exists(file_path):
            try:
                fix_manager_file(file_path)
            except Exception as e:
                print(f"  ❌ Error fixing {file_path}: {e}")
        else:
            print(f"  ⚠️ File not found: {file_path}")
    
    print("✅ JSON parsing fixes completed!")
    print("\n💡 Manual check required:")
    print("   - Restart Django server")
    print("   - Test DataTable pages that were failing")
    print("   - Check logs for any remaining JSON parsing errors")

if __name__ == "__main__":
    main()
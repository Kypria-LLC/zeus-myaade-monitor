with open('myaade_monitor_zeus.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the HEADLESS_MODE parsing (it was looking for wrong var name)
import re

# Find and fix HEADLESS parsing
pattern = r'HEADLESS:\s*bool\s*=\s*os\.getenv\([^)]+\)'
old_match = re.search(pattern, content)

if old_match:
    old_line = old_match.group(0)
    print(f'Found: {old_line}')
    
    # Replace with proper boolean parsing
    new_line = 'HEADLESS: bool = os.getenv("HEADLESS_MODE", "true").lower() not in ["false", "0", "no"]'
    content = content.replace(old_line, new_line)
    print(f'Replaced with: {new_line}')

with open('myaade_monitor_zeus.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('\n✅ Fixed HEADLESS_MODE parsing')

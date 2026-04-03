# Fix HEADLESS environment variable parsing

with open('myaade_monitor_zeus.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the HEADLESS config line and fix it
old_line = 'HEADLESS: bool = os.getenv(\"HEADLESS\", \"true\")'
new_line = 'HEADLESS: bool = os.getenv(\"HEADLESS\", \"true\").lower() not in [\"false\", \"0\", \"no\"]'

if old_line in content:
    content = content.replace(old_line, new_line)
    print('✅ Fixed HEADLESS parsing - now correctly interprets false/0/no')
else:
    # Try alternative patterns
    import re
    pattern = r'HEADLESS:\s*bool\s*=\s*os\.getenv\([^)]+\)'
    matches = re.findall(pattern, content)
    if matches:
        print(f'Found HEADLESS line: {matches[0]}')
        content = re.sub(
            r'(HEADLESS:\s*bool\s*=\s*)os\.getenv\(\"HEADLESS\",\s*\"true\"\)',
            r'\1os.getenv(\"HEADLESS\", \"true\").lower() not in [\"false\", \"0\", \"no\"]',
            content
        )
        print('✅ Fixed HEADLESS parsing')
    else:
        print('⚠️ Could not find HEADLESS line')

with open('myaade_monitor_zeus.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Run: python myaade_monitor_zeus.py --once')

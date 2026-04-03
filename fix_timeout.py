# Fix the WebDriverWait.until() timeout bug

with open('myaade_monitor_zeus.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Remove timeout parameter from wait.until() call
# The timeout is set in WebDriverWait() constructor, not .until()
content = content.replace(
    'timeout=45\n                )',
    ')'
)

with open('myaade_monitor_zeus.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('✅ Fixed: Removed invalid timeout parameter from wait.until()')
print('Run: python myaade_monitor_zeus.py --once')

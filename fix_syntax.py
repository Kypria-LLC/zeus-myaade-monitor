with open('myaade_monitor_zeus.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find and fix the broken HEADLESS line
for i, line in enumerate(lines):
    if 'HEADLESS: bool' in line and 'HEADLESS_MODE' in line:
        # Replace the entire broken line
        lines[i] = '    HEADLESS: bool = os.getenv(\"HEADLESS_MODE\", \"true\").lower() not in [\"false\", \"0\", \"no\"]\n'
        print(f'Fixed line {i+1}: Removed syntax error')
        break

with open('myaade_monitor_zeus.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('✅ Syntax error fixed')

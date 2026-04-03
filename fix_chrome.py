import sys

# Read the file
with open('myaade_monitor_zeus.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find and fix CHROME_BINARY line
for i, line in enumerate(lines):
    if 'CHROME_BINARY: str = os.getenv("CHROME_BINARY"' in line:
        lines[i] = '    CHROME_BINARY: str = os.getenv("CHROME_BINARY", "")\n'
        print(f'Fixed line {i+1}: CHROME_BINARY now defaults to empty string')
        break

# Find and remove the if config.CHROME_BINARY block
i = 0
while i < len(lines):
    if 'if config.CHROME_BINARY:' in lines[i]:
        print(f'Removing lines {i+1}-{i+2}: if config.CHROME_BINARY block')
        del lines[i:i+2]
    else:
        i += 1

# Write back
with open('myaade_monitor_zeus.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('\n✅ File fixed successfully!')
print('\nRun: python myaade_monitor_zeus.py --once')

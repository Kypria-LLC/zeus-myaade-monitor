import re

with open('myaade_monitor_zeus.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
for i, line in enumerate(lines):
    # Add ChromeDriverManager import after selenium import
    if 'from selenium import webdriver' in line and 'webdriver_manager' not in line:
        new_lines.append(line)
        indent = line[:len(line) - len(line.lstrip())]
        new_lines.append(indent + 'from webdriver_manager.chrome import ChromeDriverManager\n')
        continue
    # Fix hardcoded Linux chromedriver path
    if 'CHROMEDRIVER_PATH' in line and '/usr/bin/chromedriver' in line:
        indent = line[:len(line) - len(line.lstrip())]
        new_lines.append(indent + 'CHROMEDRIVER_PATH: str = ""\n')
        continue
    # Fix Service line to use ChromeDriverManager
    if 'Service(executable_path=config.CHROMEDRIVER_PATH)' in line:
        indent = line[:len(line) - len(line.lstrip())]
        new_lines.append(indent + 'service = Service(ChromeDriverManager().install())\n')
        continue
    new_lines.append(line)

with open('myaade_monitor_zeus.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print('Patched 3 lines successfully')

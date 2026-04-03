import re

filepath = 'myaade_monitor_zeus.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add webdriver_manager import before dotenv block
wdm_block = '''try:
    from webdriver_manager.chrome import ChromeDriverManager
except ImportError:
    ChromeDriverManager = None

'''
if 'ChromeDriverManager' not in content:
    content = content.replace(
        'try:\n    from dotenv import load_dotenv',
        wdm_block + 'try:\n    from dotenv import load_dotenv'
    )

# 2. Fix CHROME_BINARY to empty string (auto-detect)
content = re.sub(
    r'CHROME_BINARY: str = os\.getenv\("CHROME_BINARY", "[^"]*"\)',
    'CHROME_BINARY: str = os.getenv("CHROME_BINARY", "")',
    content
)

# 3. Fix CHROMEDRIVER_PATH to empty string (auto-detect)
content = re.sub(
    r'CHROMEDRIVER_PATH: str = os\.getenv\("CHROMEDRIVER_PATH", "[^"]*"\)',
    'CHROMEDRIVER_PATH: str = os.getenv("CHROMEDRIVER_PATH", "")',
    content
)

# 4. Fix DB_PATH to relative Windows path
content = re.sub(
    r'DB_PATH: Path = Path\(os\.getenv\("MYAADE_DB_PATH", "[^"]*"\)\)',
    'DB_PATH: Path = Path(os.getenv("MYAADE_DB_PATH", "data/myaade_monitor.db"))',
    content
)

# 5. Fix SCREENSHOT_DIR to relative path
content = re.sub(
    r'SCREENSHOT_DIR: Path = Path\(os\.getenv\("SCREENSHOT_DIR", "[^"]*"\)\)',
    'SCREENSHOT_DIR: Path = Path(os.getenv("SCREENSHOT_DIR", "screenshots"))',
    content
)

# 6. Fix LOG_DIR to relative path
content = re.sub(
    r'LOG_DIR: Path = Path\(os\.getenv\("LOG_DIR", "[^"]*"\)\)',
    'LOG_DIR: Path = Path(os.getenv("LOG_DIR", "logs"))',
    content
)

# 7. Replace service creation to use ChromeDriverManager
old_service = '        service = Service(executable_path=config.CHROMEDRIVER_PATH)'
new_service = '        if config.CHROMEDRIVER_PATH:\n            service = Service(executable_path=config.CHROMEDRIVER_PATH)\n        elif ChromeDriverManager:\n            service = Service(executable_path=ChromeDriverManager().install())\n        else:\n            service = Service()'
content = content.replace(old_service, new_service)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("PATCH APPLIED SUCCESSFULLY")
print()

# Syntax check
import ast
with open(filepath, 'r') as f:
    source = f.read()
try:
    ast.parse(source)
    print("SYNTAX CHECK: PASSED")
except SyntaxError as e:
    print(f"SYNTAX CHECK: FAILED - {e}")

# Show patched lines
for term in ['CHROME_BINARY', 'CHROMEDRIVER_PATH', 'ChromeDriverManager', 'DB_PATH', 'SCREENSHOT_DIR']:
    lines = [(i+1, line.rstrip()) for i, line in enumerate(source.split('\n')) if term in line]
    for num, line in lines[:2]:
        print(f"  Line {num}: {line.strip()[:90]}")

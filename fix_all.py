with open('myaade_monitor_zeus.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix 1: Change login entry URL to trigger proper GSIS redirect
content = content.replace(
    'MYAADE_LOGIN_ENTRY: str = "https://login.gsis.gr/mylogin/login.jsp"',
    'MYAADE_LOGIN_ENTRY: str = "https://www1.aade.gr/taxisnet/mytaxisnet"'
)

# Fix 2: Remove hardcoded Linux Chrome path
content = content.replace(
    'CHROME_BINARY: str = os.getenv("CHROME_BINARY", "/usr/bin/chromium")',
    'CHROME_BINARY: str = os.getenv("CHROME_BINARY", "")'
)

# Fix 3: Fix HEADLESS parsing
content = content.replace(
    'HEADLESS: bool = os.getenv("HEADLESS_MODE", "true").lower() == "true"',
    'HEADLESS: bool = os.getenv("HEADLESS_MODE", "true").lower() not in ["false", "0", "no"]'
)

with open('myaade_monitor_zeus.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Fixed: Login URL, Chrome binary, HEADLESS parsing')

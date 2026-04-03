filepath = 'myaade_monitor_zeus.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Increase login WebDriverWait from 30s to 60s
content = content.replace(
    'wait = WebDriverWait(self.driver, 30)',
    'wait = WebDriverWait(self.driver, 60)',
    1
)

# 2. Broaden the redirect check after login
old_wait = 'wait.until(lambda d: "taxisnet" in d.current_url or "myaade" in d.current_url)'
new_wait = 'wait.until(lambda d: "taxisnet" in d.current_url or "myaade" in d.current_url or "aade" in d.current_url)'
content = content.replace(old_wait, new_wait)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

import ast
with open(filepath, 'r', encoding='utf-8') as f:
    src = f.read()
try:
    ast.parse(src)
    print("SYNTAX CHECK: PASSED")
except SyntaxError as e:
    print(f"SYNTAX CHECK: FAILED - {e}")

print("Login timeout: 60s")
print("Redirect check: broadened to include aade")

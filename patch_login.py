filepath = 'myaade_monitor_zeus.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix 1: Replace loginBtn with CSS selector for submit button
content = content.replace(
    'submit_btn = self.driver.find_element(By.ID, "loginBtn")',
    'submit_btn = self.driver.find_element(By.CSS_SELECTOR, "#loginDiv button[type=\'submit\']")'
)

# Fix 2: Also add a small wait before clicking submit (GSIS can be slow)
content = content.replace(
    'submit_btn = self.driver.find_element(By.CSS_SELECTOR, "#loginDiv button[type=\'submit\']")\n            submit_btn.click()',
    'submit_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#loginDiv button[type=\'submit\']")))\n            submit_btn.click()'
)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

# Verify
import ast
with open(filepath, 'r', encoding='utf-8') as f:
    source = f.read()
try:
    ast.parse(source)
    print("SYNTAX CHECK: PASSED")
except SyntaxError as e:
    print(f"SYNTAX CHECK: FAILED - {e}")

for i, line in enumerate(source.split('\n')):
    if 'loginDiv' in line or 'loginBtn' in line or 'submit_btn' in line:
        print(f"  Line {i+1}: {line.strip()[:90]}")

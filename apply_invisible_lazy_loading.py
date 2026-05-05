import os
import shutil
import re

# 1. Restore app.py from the backup that had lazy loading
shutil.copy('app.py.bak', 'app.py')

# 2. Read app.py to remove the Lite Mode toggle UI
with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Remove the Lite Mode Toggle section from sidebar
toggle_regex = r'# Lite Mode Toggle for performance optimization.*?else:\n    os\.environ\["DISABLE_HEAVY_FEATURES"\] = "false"\n'
content = re.sub(toggle_regex, '', content, flags=re.DOTALL)

# Also remove any other DISABLE_HEAVY_FEATURES warnings in app.py
content = re.sub(r'st\.warning\("⚠️ Deep Learning features are disabled.*?"\)', 'pass', content)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)

# Script cleanup: deep_learning_forecasting.py was removed.
print("App.py restored with invisible lazy loading.")

import re
import shutil

shutil.copy('app.py.bak', 'app.py')

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

imports = """
import plotly.express as px
import plotly.graph_objects as go
from ai_models import SmartReordering, ExpiryPredictor
from advanced_analytics import AdvancedAnalytics, WastageAnalyzer, CostOptimizer, DrugUtilizationReview, AutomatedInsightsGenerator
import io
import zipfile
from qr_code_utils import generate_qr_code_for_item, qr_code_to_base64, generate_qr_code_data, parse_qr_code_data, generate_qr_code_for_bulk, get_local_ip_address, get_all_local_ip_addresses
"""

# Add imports at the top
content = content.replace("from database import DatabaseManager\n", "from database import DatabaseManager\n" + imports)

# Remove the Lite Mode Toggle
content = re.sub(r'# Lite Mode Toggle.*?\nelse:\n    os\.environ\["DISABLE_HEAVY_FEATURES"\] = "false"\n+', '', content, flags=re.DOTALL)

# Replace the lazy loading functions
content = re.sub(r'def lazy_import_plotly\(\):.*?return st\.session_state\[\'px\'\], st\.session_state\[\'go\'\]\n+', 'def lazy_import_plotly():\n    return px, go\n\n', content, flags=re.DOTALL)

content = re.sub(r'def lazy_import_analytics\(\):.*?return \([\s\S]*?\)\n+', 'def lazy_import_analytics():\n    return AdvancedAnalytics, WastageAnalyzer, CostOptimizer, DrugUtilizationReview, AutomatedInsightsGenerator\n\n', content, flags=re.DOTALL)

content = re.sub(r'def lazy_import_qr_utils\(\):.*?return \([\s\S]*?\)\n+', 'def lazy_import_qr_utils():\n    return io, zipfile, generate_qr_code_for_item, get_local_ip_address, generate_qr_code_data, generate_qr_code_for_bulk\n\n', content, flags=re.DOTALL)

content = re.sub(r'# Lazy load AI models.*?def init_ai_models\(\):.*?return reordering, expiry_predictor\n+', 'def init_ai_models():\n    return SmartReordering(), ExpiryPredictor()\n\n', content, flags=re.DOTALL)


with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Restored and simplified app.py")

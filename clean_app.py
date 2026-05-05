import re
import os

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Remove the lazy import function definitions
content = re.sub(r'def lazy_import_plotly\(\):.*?return st\.session_state\[\'px\'\], st\.session_state\[\'go\'\]\n+', '', content, flags=re.DOTALL)
content = re.sub(r'def lazy_import_analytics\(\):.*?return \([\s\S]*?\)\n+', '', content, flags=re.DOTALL)
content = re.sub(r'def lazy_import_qr_utils\(\):.*?return \([\s\S]*?\)\n+', '', content, flags=re.DOTALL)

# 2. Add imports at the top
imports = """
import plotly.express as px
import plotly.graph_objects as go
from ai_models import SmartReordering, ExpiryPredictor
from advanced_analytics import AdvancedAnalytics, WastageAnalyzer, CostOptimizer, DrugUtilizationReview, AutomatedInsightsGenerator
import io
import zipfile
from qr_code_utils import generate_qr_code_for_item, qr_code_to_base64, generate_qr_code_data, parse_qr_code_data, generate_qr_code_for_bulk, get_local_ip_address, get_all_local_ip_addresses
"""
content = content.replace("from database import DatabaseManager\n", "from database import DatabaseManager\n" + imports)

# 3. Replace usages
content = re.sub(r'[ \t]*px, go = lazy_import_plotly\(\)\n', '', content)
content = re.sub(r'[ \t]*AdvancedAnalytics, WastageAnalyzer, CostOptimizer, DrugUtilizationReview, AutomatedInsightsGenerator = lazy_import_analytics\(\)\n', '', content)
content = re.sub(r'[ \t]*io, zipfile, generate_qr_code_for_item, get_local_ip_address, generate_qr_code_data, generate_qr_code_for_bulk = lazy_import_qr_utils\(\)\n', '', content)
content = re.sub(r'[ \t]*_, _, _, get_local_ip_address, _, _ = lazy_import_qr_utils\(\)\n', '', content)
content = re.sub(r'[ \t]*io, _, _, _, _, _ = lazy_import_qr_utils\(\)\n', '', content)
content = re.sub(r'[ \t]*_, _, _, _, _, generate_qr_code_for_bulk = lazy_import_qr_utils\(\)\n', '', content)

# 4. Remove ai_models init stuff
content = re.sub(r'# Lazy load AI models.*?def init_ai_models\(\):.*?return reordering, expiry_predictor\n+', '', content, flags=re.DOTALL)
content = content.replace("reordering = None\nexpiry_predictor = None", "reordering = SmartReordering()\nexpiry_predictor = ExpiryPredictor()")
content = re.sub(r'[ \t]*if reordering is None:\n[ \t]*reordering, expiry_predictor = init_ai_models\(\)\n', '', content)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Done cleaning app.py")

import sqlite3
import random
from datetime import datetime, timedelta
import numpy as np

db_path = "pharma_inventory.db"

pharmaceutical_drugs = [
    ("Paracetamol", "Analgesics", "Generic Pharma", 500, 10.50),
    ("Ibuprofen", "Analgesics", "Pain Relief Co", 400, 15.75),
    ("Aspirin", "Analgesics", "Cardio Pharma", 300, 8.25),
    ("Amoxicillin", "Antibiotics", "BioCure Ltd", 500, 45.00),
    ("Ciprofloxacin", "Antibiotics", "MediCorp", 200, 65.50),
    ("Azithromycin", "Antibiotics", "PharmaTech", 250, 85.00),
    ("Metformin", "Antidiabetics", "DiaCare", 500, 25.50),
    ("Glipizide", "Antidiabetics", "Sugar Control Inc", 100, 35.75),
    ("Insulin Glargine", "Antidiabetics", "EndoPharm", 50, 450.00),
    ("Atenolol", "Cardiovascular", "HeartCare", 300, 28.50),
    ("Lisinopril", "Cardiovascular", "BP Pharma", 250, 42.00),
    ("Amlodipine", "Cardiovascular", "Cardio Plus", 400, 38.25),
    ("Omeprazole", "Gastrointestinal", "Gastro Med", 500, 32.00),
    ("Ranitidine", "Gastrointestinal", "Digestive Care", 300, 18.50),
    ("Cetirizine", "Antihistamines", "Allergy Free", 200, 12.75),
    ("Loratadine", "Antihistamines", "AntiAllergy Co", 250, 15.00),
    ("Prednisolone", "Steroids", "Steroid Pharma", 100, 55.00),
    ("Dexamethasone", "Steroids", "Anti-Inflam Inc", 80, 68.50),
    ("Salbutamol", "Respiratory", "Breathe Easy", 150, 125.00),
    ("Montelukast", "Respiratory", "Lung Care", 200, 95.50),
    ("Atorvastatin", "Cholesterol", "LipidCare", 400, 52.00),
    ("Simvastatin", "Cholesterol", "Cardio Lipid", 350, 45.75),
    ("Levothyroxine", "Thyroid", "ThyroMed", 200, 38.00),
    ("Warfarin", "Anticoagulants", "Blood Thin Co", 100, 72.50),
    ("Clopidogrel", "Anticoagulants", "Clot Prevention", 150, 88.00),
    ("Diazepam", "Sedatives", "Calm Pharma", 50, 42.00),
    ("Alprazolam", "Sedatives", "Anxiety Relief", 60, 55.50),
    ("Morphine", "Opioids", "Pain Control Ltd", 30, 250.00),
    ("Tramadol", "Opioids", "Pain Management", 100, 95.00),
    ("Gabapentin", "Neuropathic", "Neuro Care", 150, 65.00),
    ("Pregabalin", "Neuropathic", "Nerve Relief", 120, 78.50),
    ("Fluoxetine", "Antidepressants", "Mind Care", 100, 48.00),
    ("Sertraline", "Antidepressants", "Mood Balance", 120, 52.50),
    ("Metronidazole", "Antibiotics", "Infection Control", 200, 35.00),
    ("Doxycycline", "Antibiotics", "Broad Spectrum", 180, 42.75),
    ("Pantoprazole", "Gastrointestinal", "Acid Control", 300, 36.50),
    ("Domperidone", "Gastrointestinal", "Digestive Aid", 250, 22.00),
    ("Losartan", "Cardiovascular", "BP Manager", 300, 46.50),
    ("Furosemide", "Diuretics", "Fluid Control", 200, 18.75),
    ("Spironolactone", "Diuretics", "Heart Diuretic", 150, 32.50),
    ("Vitamin D3", "Vitamins", "Sunshine Pharma", 500, 15.00),
    ("Calcium Carbonate", "Minerals", "Bone Health", 400, 12.50),
    ("Iron Supplement", "Minerals", "Blood Builder", 300, 18.00),
    ("Multivitamin", "Vitamins", "Complete Care", 600, 25.00),
    ("Folic Acid", "Vitamins", "Prenatal Care", 250, 10.50),
]

categories = ["Analgesics", "Antibiotics", "Antidiabetics", "Cardiovascular", 
              "Gastrointestinal", "Antihistamines", "Steroids", "Respiratory",
              "Cholesterol", "Thyroid", "Anticoagulants", "Sedatives", "Opioids",
              "Neuropathic", "Antidepressants", "Diuretics", "Vitamins", "Minerals"]

manufacturers = ["Generic Pharma", "MediCorp", "PharmaTech", "BioCure Ltd", 
                 "Cardio Pharma", "Pain Relief Co", "DiaCare", "HeartCare",
                 "Gastro Med", "Allergy Free", "Steroid Pharma", "Breathe Easy",
                 "LipidCare", "ThyroMed", "Blood Thin Co", "Calm Pharma",
                 "Pain Control Ltd", "Neuro Care", "Mind Care", "Infection Control",
                 "Sunshine Pharma", "Bone Health", "Complete Care"]

suppliers = ["MedSupply International", "PharmaDirect", "HealthCare Distributors",
             "Global Med Solutions", "QuickMed Supply", "PharmaHub",
             "MediSource Pro", "HealthFirst Suppliers", "CarePlus Distribution"]

def generate_batch_number(year, month, drug_name):
    prefix = ''.join([c for c in drug_name if c.isupper()])[:3]
    if not prefix:
        prefix = drug_name[:3].upper()
    return f"{prefix}{year}{month:02d}{random.randint(1000, 9999)}"

def populate_database():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("Starting database population...")
    
    cursor.execute("DELETE FROM transactions")
    cursor.execute("DELETE FROM inventory")
    conn.commit()
    print("Cleared existing inventory and transactions")
    
    drugs_to_add = []
    all_drugs = []
    
    base_drugs_count = len(pharmaceutical_drugs)
    repetitions = (200 + base_drugs_count - 1) // base_drugs_count
    
    years = list(range(2020, 2026))
    
    for rep in range(repetitions):
        for drug_name, category, manufacturer, base_stock, base_price in pharmaceutical_drugs:
            if len(all_drugs) >= 200:
                break
            
            year = random.choice(years)
            month = random.randint(1, 12)
            
            variation_factor = random.uniform(0.8, 1.2)
            current_stock = int(base_stock * variation_factor)
            minimum_stock = max(10, int(current_stock * 0.2))
            
            price_variation = random.uniform(0.9, 1.15)
            unit_price = round(base_price * price_variation, 2)
            
            days_until_expiry = random.randint(30, 1095)
            expiry_date = (datetime.now() + timedelta(days=days_until_expiry)).strftime("%Y-%m-%d")
            
            batch_number = generate_batch_number(year, month, drug_name)
            supplier = random.choice(suppliers)
            
            description = f"{drug_name} tablets/capsules - {category}"
            
            all_drugs.append((
                drug_name,
                category,
                manufacturer,
                batch_number,
                current_stock,
                minimum_stock,
                unit_price,
                expiry_date,
                supplier,
                description,
                f"{year}-{month:02d}-01 00:00:00",
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))
        
        if len(all_drugs) >= 200:
            break
    
    all_drugs = all_drugs[:200]
    
    cursor.executemany('''
        INSERT INTO inventory (
            drug_name, category, manufacturer, batch_number,
            current_stock, minimum_stock, unit_price, expiry_date,
            supplier_name, description, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', all_drugs)
    
    conn.commit()
    print(f"Added {len(all_drugs)} pharmaceutical items to inventory")
    
    cursor.execute("SELECT id, drug_name, current_stock, unit_price FROM inventory")
    inventory_items = cursor.fetchall()
    
    transaction_types = ["Purchase", "Sale", "Return", "Adjustment", "Damage", "Expired"]
    departments = ["Pharmacy", "Emergency", "Cardiology", "Pediatrics", "General Ward", "ICU"]
    
    transactions = []
    for item_id, drug_name, stock, price in inventory_items:
        num_transactions = random.randint(5, 15)
        
        for _ in range(num_transactions):
            trans_type = random.choice(transaction_types)
            
            if trans_type == "Purchase":
                quantity = random.randint(50, 500)
            elif trans_type == "Sale":
                quantity = random.randint(1, 100)
            else:
                quantity = random.randint(1, 50)
            
            total_amount = quantity * price
            
            days_ago = random.randint(1, 730)
            created_at = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d %H:%M:%S")
            
            ref_number = f"REF{random.randint(100000, 999999)}"
            department = random.choice(departments)
            
            notes = f"{trans_type} transaction for {drug_name}"
            
            transactions.append((
                item_id,
                trans_type,
                quantity,
                price,
                total_amount,
                ref_number,
                notes,
                department,
                "admin",
                created_at
            ))
    
    cursor.executemany('''
        INSERT INTO transactions (
            drug_id, transaction_type, quantity, unit_price, total_amount,
            reference_number, notes, department, user_id, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', transactions)
    
    conn.commit()
    print(f"Added {len(transactions)} transactions")
    
    for supplier in suppliers:
        cursor.execute('''
            INSERT OR IGNORE INTO suppliers (
                name, contact_person, phone, email, address,
                lead_time_days, reliability_score, cost_rating
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            supplier,
            f"{supplier.split()[0]} Manager",
            f"+91-{random.randint(7000000000, 9999999999)}",
            f"contact@{supplier.lower().replace(' ', '')}.com",
            f"{random.randint(1, 999)} Medical Plaza, Mumbai, India",
            random.randint(3, 14),
            round(random.uniform(3.5, 5.0), 1),
            round(random.uniform(3.0, 5.0), 1)
        ))
    
    conn.commit()
    print(f"Added {len(suppliers)} suppliers")
    
    cursor.execute("SELECT COUNT(*) FROM inventory")
    total_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM transactions")
    total_transactions = cursor.fetchone()[0]
    
    cursor.execute("SELECT SUM(current_stock * unit_price) FROM inventory")
    total_value = cursor.fetchone()[0]
    
    print("\n" + "="*50)
    print("DATABASE POPULATION COMPLETE")
    print("="*50)
    print(f"Total Inventory Items: {total_count}")
    print(f"Total Transactions: {total_transactions}")
    print(f"Total Inventory Value: ₹{total_value:,.2f}")
    print("="*50)
    
    conn.close()

if __name__ == "__main__":
    populate_database()

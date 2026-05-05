import sqlite3
import random
from datetime import datetime, timedelta
import numpy as np

conn = sqlite3.connect('pharma_inventory.db')
cursor = conn.cursor()

print("Starting comprehensive data generation...")
print("=" * 70)

# Get all drugs
drugs = cursor.execute("SELECT id, drug_name, category, unit_price FROM inventory").fetchall()
print(f"Found {len(drugs)} drugs in inventory")

departments = ["Emergency", "ICU", "General Ward", "Pediatrics", "Surgery", "Cardiology", "Neurology", "Orthopedics", "Oncology", "Outpatient"]
users = ["admin", "pharmacist1", "pharmacist2", "staff1", "staff2", "staff3"]

# Transaction types with realistic distributions
transaction_types = {
    "dispense": 0.55,  # 55% dispensing
    "purchase": 0.20,  # 20% purchases
    "return": 0.10,    # 10% returns
    "adjustment": 0.10,  # 10% adjustments
    "transfer": 0.05   # 5% transfers
}

print("\n📦 Generating transaction history (2020-2025)...")
transactions_added = 0
start_date = datetime(2020, 1, 1)
end_date = datetime.now()

# Generate transactions with realistic patterns
for drug_id, drug_name, category, unit_price in drugs:
    # Different categories have different demand patterns
    if category in ["Cardiovascular", "Antidiabetics", "Respiratory"]:
        avg_monthly_transactions = random.randint(30, 80)
    elif category in ["Antibiotics", "Analgesics"]:
        avg_monthly_transactions = random.randint(40, 100)
    elif category in ["Antipsychotics", "Gastrointestinal"]:
        avg_monthly_transactions = random.randint(20, 60)
    else:
        avg_monthly_transactions = random.randint(10, 40)
    
    # Generate transactions for each month from 2020 to now
    current_date = start_date
    while current_date < end_date:
        # Number of transactions this month (with some randomness)
        num_transactions = max(1, int(np.random.poisson(avg_monthly_transactions)))
        
        for _ in range(num_transactions):
            # Random date within the month
            days_in_month = 30
            if current_date.month in [1, 3, 5, 7, 8, 10, 12]:
                days_in_month = 31
            elif current_date.month == 2:
                days_in_month = 28 if current_date.year % 4 != 0 else 29
            
            transaction_date = current_date + timedelta(days=random.randint(0, days_in_month - 1))
            
            # Select transaction type based on distribution
            rand_val = random.random()
            cumulative_prob = 0
            selected_type = "dispense"
            for trans_type, prob in transaction_types.items():
                cumulative_prob += prob
                if rand_val <= cumulative_prob:
                    selected_type = trans_type
                    break
            
            # Generate realistic quantity based on transaction type
            if selected_type == "purchase":
                quantity = random.randint(50, 500)
            elif selected_type == "dispense":
                quantity = -random.randint(1, 50)
            elif selected_type == "return":
                quantity = random.randint(1, 20)
            elif selected_type == "adjustment":
                quantity = random.randint(-10, 10)
            else:  # transfer
                quantity = -random.randint(5, 30)
            
            total_amount = abs(quantity) * unit_price
            department = random.choice(departments)
            user = random.choice(users)
            
            reference_number = f"TXN-{transaction_date.year}{transaction_date.month:02d}-{random.randint(1000, 9999)}"
            
            try:
                cursor.execute('''
                    INSERT INTO transactions 
                    (drug_id, transaction_type, quantity, unit_price, total_amount, 
                     reference_number, department, user_id, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (drug_id, selected_type, quantity, unit_price, total_amount,
                      reference_number, department, user, transaction_date.strftime('%Y-%m-%d %H:%M:%S')))
                
                transactions_added += 1
                
                if transactions_added % 1000 == 0:
                    print(f"  Generated {transactions_added} transactions...")
                    conn.commit()
                    
            except sqlite3.IntegrityError:
                continue
        
        # Move to next month
        if current_date.month == 12:
            current_date = datetime(current_date.year + 1, 1, 1)
        else:
            current_date = datetime(current_date.year, current_date.month + 1, 1)

conn.commit()
print(f"✅ Generated {transactions_added} transactions!")

# Generate consumption patterns
print("\n📊 Generating consumption patterns...")
consumption_added = 0

for drug_id, drug_name, category, unit_price in drugs:
    # Determine consumption frequency based on category
    if category in ["Cardiovascular", "Antidiabetics"]:
        daily_base_consumption = random.randint(5, 25)
    elif category in ["Antibiotics", "Analgesics"]:
        daily_base_consumption = random.randint(10, 40)
    elif category in ["Gastrointestinal", "Respiratory"]:
        daily_base_consumption = random.randint(8, 30)
    else:
        daily_base_consumption = random.randint(2, 15)
    
    # Generate daily consumption for past 2 years
    consumption_start = datetime.now() - timedelta(days=730)
    
    for day_offset in range(730):
        consumption_date = consumption_start + timedelta(days=day_offset)
        
        # Add seasonal variations
        month = consumption_date.month
        seasonal_factor = 1.0
        
        # Respiratory drugs peak in winter
        if category == "Respiratory":
            if month in [11, 12, 1, 2]:
                seasonal_factor = 1.5
            elif month in [6, 7, 8]:
                seasonal_factor = 0.7
        
        # Gastrointestinal drugs vary in summer
        if category == "Gastrointestinal":
            if month in [6, 7, 8]:
                seasonal_factor = 1.3
        
        # Add day-of-week variation (weekdays higher than weekends)
        weekday_factor = 1.0
        if consumption_date.weekday() >= 5:  # Weekend
            weekday_factor = 0.6
        
        # Calculate consumption with noise
        base_consumption = daily_base_consumption * seasonal_factor * weekday_factor
        noise = np.random.normal(0, base_consumption * 0.2)
        daily_consumption = max(0, int(base_consumption + noise))
        
        if daily_consumption > 0:
            department = random.choice(departments)
            
            try:
                cursor.execute('''
                    INSERT INTO consumption_patterns 
                    (drug_id, date, quantity_consumed, department, created_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (drug_id, consumption_date.strftime('%Y-%m-%d'), 
                      daily_consumption, department, 
                      consumption_date.strftime('%Y-%m-%d %H:%M:%S')))
                
                consumption_added += 1
                
                if consumption_added % 5000 == 0:
                    print(f"  Generated {consumption_added} consumption records...")
                    conn.commit()
                    
            except sqlite3.IntegrityError:
                continue

conn.commit()
print(f"✅ Generated {consumption_added} consumption pattern records!")

# Update statistics
total_transactions = cursor.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
total_consumption = cursor.execute("SELECT COUNT(*) FROM consumption_patterns").fetchone()[0]
total_inventory = cursor.execute("SELECT COUNT(*) FROM inventory").fetchone()[0]

print("\n" + "=" * 70)
print("📈 Database Statistics:")
print(f"  Total Inventory Items: {total_inventory}")
print(f"  Total Transactions: {total_transactions}")
print(f"  Total Consumption Records: {total_consumption}")

# Show transaction breakdown
print("\n📊 Transaction Breakdown by Type:")
trans_breakdown = cursor.execute('''
    SELECT transaction_type, COUNT(*) as count, SUM(total_amount) as total_value
    FROM transactions
    GROUP BY transaction_type
    ORDER BY count DESC
''').fetchall()

for trans_type, count, total_value in trans_breakdown:
    print(f"  {trans_type.capitalize()}: {count} transactions (₹{total_value:,.2f})")

# Show consumption by category
print("\n📊 Top 10 Categories by Consumption:")
category_consumption = cursor.execute('''
    SELECT i.category, SUM(cp.quantity_consumed) as total_consumed
    FROM consumption_patterns cp
    JOIN inventory i ON cp.drug_id = i.id
    GROUP BY i.category
    ORDER BY total_consumed DESC
    LIMIT 10
''').fetchall()

for category, total in category_consumption:
    print(f"  {category}: {total:,} units")

# Add more items to reach 700
print("\n" + "=" * 70)
print("📦 Adding final items to reach 700 total...")

additional_drugs = [
    ("Pregabalin 150mg", "Neuropathic", "Pfizer", "Neuropathic pain", "PharmaCorp"),
    ("Gabapentin 600mg", "Neuropathic", "Pfizer", "Neuropathic pain", "Global Medical Supply"),
    ("Amitriptyline 50mg", "Antidepressants", "Sandoz", "Tricyclic antidepressant", "Wellness Distributors"),
    ("Levothyroxine 100mcg", "Thyroid", "Abbott", "Thyroid hormone", "HealthFirst Suppliers"),
    ("Levothyroxine 50mcg", "Thyroid", "Abbott", "Thyroid hormone", "Amoxil Pharma"),
    ("Levothyroxine 25mcg", "Thyroid", "Abbott", "Thyroid hormone", "MedLife Suppliers"),
    ("Doxazosin 4mg", "Cardiovascular", "Pfizer", "Alpha blocker", "PharmaCorp"),
    ("Tamsulosin 0.4mg", "Urological", "Boehringer", "Alpha blocker", "Global Medical Supply"),
    ("Finasteride 5mg", "Urological", "Merck", "5-alpha reductase inhibitor", "Wellness Distributors"),
    ("Dutasteride 0.5mg", "Urological", "GlaxoSmithKline", "5-alpha reductase inhibitor", "HealthFirst Suppliers"),
    ("Sildenafil 50mg", "Urological", "Pfizer", "PDE5 inhibitor", "Amoxil Pharma"),
    ("Tadalafil 20mg", "Urological", "Lilly", "PDE5 inhibitor", "MedLife Suppliers"),
    ("Vardenafil 10mg", "Urological", "Bayer", "PDE5 inhibitor", "PharmaCorp"),
    ("Avanafil 100mg", "Urological", "Vivus", "PDE5 inhibitor", "Global Medical Supply"),
    ("Solifenacin 5mg", "Urological", "Astellas", "Anticholinergic", "Wellness Distributors"),
    ("Tolterodine 2mg", "Urological", "Pfizer", "Anticholinergic", "HealthFirst Suppliers"),
    ("Oxybutynin 5mg", "Urological", "Alza", "Anticholinergic", "Amoxil Pharma"),
    ("Mirabegron 50mg", "Urological", "Astellas", "Beta-3 agonist", "MedLife Suppliers"),
    ("Desmopressin 0.2mg", "Urological", "Ferring", "Antidiuretic", "PharmaCorp"),
    ("Alfuzosin 10mg", "Urological", "Sanofi", "Alpha blocker", "Global Medical Supply"),
]

# Continue adding more drugs to reach 70 total
more_drugs = [
    ("Tizanidine 2mg", "Muscle Relaxants", "Acorda", "Muscle relaxant", "Wellness Distributors"),
    ("Baclofen 10mg", "Muscle Relaxants", "Novartis", "Muscle relaxant", "HealthFirst Suppliers"),
    ("Cyclobenzaprine 10mg", "Muscle Relaxants", "McNeil", "Muscle relaxant", "Amoxil Pharma"),
    ("Methocarbamol 500mg", "Muscle Relaxants", "Valeant", "Muscle relaxant", "MedLife Suppliers"),
    ("Carisoprodol 350mg", "Muscle Relaxants", "Meda", "Muscle relaxant", "PharmaCorp"),
    ("Orphenadrine 100mg", "Muscle Relaxants", "Sandoz", "Muscle relaxant", "Global Medical Supply"),
    ("Chlorzoxazone 500mg", "Muscle Relaxants", "Various", "Muscle relaxant", "Wellness Distributors"),
    ("Dantrolene 25mg", "Muscle Relaxants", "JHP", "Muscle relaxant", "HealthFirst Suppliers"),
    ("Metaxalone 800mg", "Muscle Relaxants", "Pfizer", "Muscle relaxant", "Amoxil Pharma"),
    ("Allopurinol 300mg", "Anti-gout", "Mylan", "Xanthine oxidase inhibitor", "MedLife Suppliers"),
    ("Colchicine 0.6mg", "Anti-gout", "Takeda", "Anti-gout", "PharmaCorp"),
    ("Febuxostat 80mg", "Anti-gout", "Takeda", "Xanthine oxidase inhibitor", "Global Medical Supply"),
    ("Probenecid 500mg", "Anti-gout", "Various", "Uricosuric", "Wellness Distributors"),
    ("Pegloticase 8mg", "Anti-gout", "Horizon", "Uricase", "HealthFirst Suppliers"),
    ("Alendronate 70mg", "Osteoporosis", "Merck", "Bisphosphonate", "Amoxil Pharma"),
    ("Risedronate 35mg", "Osteoporosis", "Procter & Gamble", "Bisphosphonate", "MedLife Suppliers"),
    ("Ibandronate 150mg", "Osteoporosis", "Roche", "Bisphosphonate", "PharmaCorp"),
    ("Zoledronic Acid 5mg", "Osteoporosis", "Novartis", "Bisphosphonate", "Global Medical Supply"),
    ("Denosumab 60mg", "Osteoporosis", "Amgen", "RANK ligand inhibitor", "Wellness Distributors"),
    ("Raloxifene 60mg", "Osteoporosis", "Lilly", "SERM", "HealthFirst Suppliers"),
    ("Teriparatide 20mcg", "Osteoporosis", "Lilly", "PTH analog", "Amoxil Pharma"),
    ("Calcitonin 200IU", "Osteoporosis", "Novartis", "Calcitonin", "MedLife Suppliers"),
    ("Methylprednisolone 4mg", "Steroids", "Pfizer", "Corticosteroid", "PharmaCorp"),
    ("Prednisone 5mg", "Steroids", "Roxane", "Corticosteroid", "Global Medical Supply"),
    ("Prednisolone 5mg", "Steroids", "Teva", "Corticosteroid", "Wellness Distributors"),
    ("Dexamethasone 0.5mg", "Steroids", "Various", "Corticosteroid", "HealthFirst Suppliers"),
    ("Hydrocortisone 20mg", "Steroids", "Pfizer", "Corticosteroid", "Amoxil Pharma"),
    ("Triamcinolone 4mg", "Steroids", "Bristol-Myers", "Corticosteroid", "MedLife Suppliers"),
    ("Betamethasone 0.5mg", "Steroids", "Merck", "Corticosteroid", "PharmaCorp"),
    ("Fludrocortisone 0.1mg", "Steroids", "Various", "Corticosteroid", "Global Medical Supply"),
    ("Acyclovir 400mg", "Antivirals", "GlaxoSmithKline", "Antiviral", "Wellness Distributors"),
    ("Valacyclovir 500mg", "Antivirals", "GlaxoSmithKline", "Antiviral", "HealthFirst Suppliers"),
    ("Famciclovir 250mg", "Antivirals", "Novartis", "Antiviral", "Amoxil Pharma"),
    ("Oseltamivir 75mg", "Antivirals", "Roche", "Antiviral", "MedLife Suppliers"),
    ("Zanamivir 5mg", "Antivirals", "GlaxoSmithKline", "Antiviral", "PharmaCorp"),
    ("Ribavirin 200mg", "Antivirals", "Merck", "Antiviral", "Global Medical Supply"),
    ("Ganciclovir 500mg", "Antivirals", "Roche", "Antiviral", "Wellness Distributors"),
    ("Valganciclovir 450mg", "Antivirals", "Roche", "Antiviral", "HealthFirst Suppliers"),
    ("Cidofovir 75mg", "Antivirals", "Gilead", "Antiviral", "Amoxil Pharma"),
    ("Foscarnet 24mg/ml", "Antivirals", "AstraZeneca", "Antiviral", "MedLife Suppliers"),
    ("Fluconazole 150mg", "Antifungals", "Pfizer", "Antifungal", "PharmaCorp"),
    ("Itraconazole 100mg", "Antifungals", "Janssen", "Antifungal", "Global Medical Supply"),
    ("Voriconazole 200mg", "Antifungals", "Pfizer", "Antifungal", "Wellness Distributors"),
    ("Posaconazole 100mg", "Antifungals", "Merck", "Antifungal", "HealthFirst Suppliers"),
    ("Amphotericin B 50mg", "Antifungals", "Bristol-Myers", "Antifungal", "Amoxil Pharma"),
    ("Caspofungin 50mg", "Antifungals", "Merck", "Antifungal", "MedLife Suppliers"),
    ("Micafungin 50mg", "Antifungals", "Astellas", "Antifungal", "PharmaCorp"),
    ("Anidulafungin 100mg", "Antifungals", "Pfizer", "Antifungal", "Global Medical Supply"),
    ("Nystatin 500000U", "Antifungals", "Various", "Antifungal", "Wellness Distributors"),
    ("Griseofulvin 500mg", "Antifungals", "Various", "Antifungal", "HealthFirst Suppliers"),
]

batch_start = 2000
final_drugs = additional_drugs + more_drugs

added_final = 0
for idx, (drug_name, category, manufacturer, description, supplier) in enumerate(final_drugs, start=1):
    if added_final >= 70:
        break
        
    batch_number = f"BATCH-{batch_start + idx:05d}"
    
    current_stock = random.randint(20, 300)
    minimum_stock = random.randint(10, 50)
    
    base_price = random.uniform(10, 400)
    unit_price = round(base_price, 2)
    
    days_until_expiry = random.randint(90, 1095)
    expiry_date = (datetime.now() + timedelta(days=days_until_expiry)).strftime('%Y-%m-%d')
    
    try:
        cursor.execute('''
            INSERT INTO inventory (drug_name, category, manufacturer, batch_number, 
                                  current_stock, minimum_stock, unit_price, expiry_date, 
                                  supplier_name, description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (drug_name, category, manufacturer, batch_number, current_stock, 
              minimum_stock, unit_price, expiry_date, supplier, description))
        added_final += 1
    except sqlite3.IntegrityError:
        continue

conn.commit()

final_count = cursor.execute("SELECT COUNT(*) FROM inventory").fetchone()[0]
print(f"✅ Added {added_final} more items!")
print(f"📦 Final inventory count: {final_count}")

conn.close()
print("\n" + "=" * 70)
print("✅ All data generation complete!")
print("=" * 70)

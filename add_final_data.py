import sqlite3
import random
from datetime import datetime, timedelta
import numpy as np

conn = sqlite3.connect('pharma_inventory.db')
cursor = conn.cursor()

print("Adding final data...")
print("=" * 70)

# Get current inventory count
current_inv_count = cursor.execute("SELECT COUNT(*) FROM inventory").fetchone()[0]
print(f"Current inventory items: {current_inv_count}")

# Add 70 more drugs to reach 700
if current_inv_count < 700:
    needed = 700 - current_inv_count
    print(f"\n📦 Adding {needed} more items to reach 700...")
    
    additional_drugs = [
        ("Tamsulosin 0.4mg", "Urological", "Boehringer", "Alpha blocker", "Global Medical Supply"),
        ("Finasteride 5mg", "Urological", "Merck", "5-alpha reductase inhibitor", "Wellness Distributors"),
        ("Dutasteride 0.5mg", "Urological", "GlaxoSmithKline", "5-alpha reductase inhibitor", "HealthFirst Suppliers"),
        ("Sildenafil 50mg", "Urological", "Pfizer", "PDE5 inhibitor", "Amoxil Pharma"),
        ("Tadalafil 20mg", "Urological", "Lilly", "PDE5 inhibitor", "MedLife Suppliers"),
        ("Vardenafil 10mg", "Urological", "Bayer", "PDE5 inhibitor", "PharmaCorp"),
        ("Solifenacin 5mg", "Urological", "Astellas", "Anticholinergic", "Wellness Distributors"),
        ("Tolterodine 2mg", "Urological", "Pfizer", "Anticholinergic", "HealthFirst Suppliers"),
        ("Oxybutynin 5mg", "Urological", "Alza", "Anticholinergic", "Amoxil Pharma"),
        ("Mirabegron 50mg", "Urological", "Astellas", "Beta-3 agonist", "MedLife Suppliers"),
        ("Tizanidine 2mg", "Muscle Relaxants", "Acorda", "Muscle relaxant", "Wellness Distributors"),
        ("Baclofen 10mg", "Muscle Relaxants", "Novartis", "Muscle relaxant", "HealthFirst Suppliers"),
        ("Cyclobenzaprine 10mg", "Muscle Relaxants", "McNeil", "Muscle relaxant", "Amoxil Pharma"),
        ("Methocarbamol 500mg", "Muscle Relaxants", "Valeant", "Muscle relaxant", "MedLife Suppliers"),
        ("Carisoprodol 350mg", "Muscle Relaxants", "Meda", "Muscle relaxant", "PharmaCorp"),
        ("Allopurinol 300mg", "Anti-gout", "Mylan", "Xanthine oxidase inhibitor", "MedLife Suppliers"),
        ("Colchicine 0.6mg", "Anti-gout", "Takeda", "Anti-gout", "PharmaCorp"),
        ("Febuxostat 80mg", "Anti-gout", "Takeda", "Xanthine oxidase inhibitor", "Global Medical Supply"),
        ("Alendronate 70mg", "Osteoporosis", "Merck", "Bisphosphonate", "Amoxil Pharma"),
        ("Risedronate 35mg", "Osteoporosis", "Procter & Gamble", "Bisphosphonate", "MedLife Suppliers"),
        ("Methylprednisolone 4mg", "Steroids", "Pfizer", "Corticosteroid", "PharmaCorp"),
        ("Prednisone 5mg", "Steroids", "Roxane", "Corticosteroid", "Global Medical Supply"),
        ("Prednisolone 5mg", "Steroids", "Teva", "Corticosteroid", "Wellness Distributors"),
        ("Dexamethasone 0.5mg", "Steroids", "Various", "Corticosteroid", "HealthFirst Suppliers"),
        ("Hydrocortisone 20mg", "Steroids", "Pfizer", "Corticosteroid", "Amoxil Pharma"),
        ("Acyclovir 400mg", "Antivirals", "GlaxoSmithKline", "Antiviral", "Wellness Distributors"),
        ("Valacyclovir 500mg", "Antivirals", "GlaxoSmithKline", "Antiviral", "HealthFirst Suppliers"),
        ("Famciclovir 250mg", "Antivirals", "Novartis", "Antiviral", "Amoxil Pharma"),
        ("Oseltamivir 75mg", "Antivirals", "Roche", "Antiviral", "MedLife Suppliers"),
        ("Zanamivir 5mg", "Antivirals", "GlaxoSmithKline", "Antiviral", "PharmaCorp"),
        ("Fluconazole 150mg", "Antifungals", "Pfizer", "Antifungal", "PharmaCorp"),
        ("Itraconazole 100mg", "Antifungals", "Janssen", "Antifungal", "Global Medical Supply"),
        ("Voriconazole 200mg", "Antifungals", "Pfizer", "Antifungal", "Wellness Distributors"),
        ("Posaconazole 100mg", "Antifungals", "Merck", "Antifungal", "HealthFirst Suppliers"),
        ("Terbinafine 250mg Oral", "Antifungals", "Novartis", "Antifungal", "Amoxil Pharma"),
        ("Levothyroxine 100mcg", "Thyroid", "Abbott", "Thyroid hormone", "HealthFirst Suppliers"),
        ("Levothyroxine 50mcg", "Thyroid", "Abbott", "Thyroid hormone", "Amoxil Pharma"),
        ("Liothyronine 5mcg", "Thyroid", "Pfizer", "Thyroid hormone", "MedLife Suppliers"),
        ("Methimazole 5mg", "Thyroid", "Various", "Antithyroid", "PharmaCorp"),
        ("Propylthiouracil 50mg", "Thyroid", "Various", "Antithyroid", "Global Medical Supply"),
        ("Calcitriol 0.25mcg", "Vitamins", "Roche", "Active Vitamin D", "Wellness Distributors"),
        ("Alfacalcidol 0.25mcg", "Vitamins", "Teva", "Vitamin D analog", "HealthFirst Suppliers"),
        ("Cholecalciferol 60000IU", "Vitamins", "Various", "Vitamin D3", "Amoxil Pharma"),
        ("Methylcobalamin 1500mcg", "Vitamins", "Various", "Active B12", "MedLife Suppliers"),
        ("Hydroxocobalamin 1mg", "Vitamins", "Various", "Vitamin B12", "PharmaCorp"),
        ("Melatonin 3mg", "Sleep Aid", "Various", "Sleep regulator", "Global Medical Supply"),
        ("Zolpidem 10mg", "Sleep Aid", "Sanofi", "Sedative", "Wellness Distributors"),
        ("Eszopiclone 3mg", "Sleep Aid", "Sunovion", "Sedative", "HealthFirst Suppliers"),
        ("Ramelteon 8mg", "Sleep Aid", "Takeda", "Melatonin agonist", "Amoxil Pharma"),
        ("Suvorexant 10mg", "Sleep Aid", "Merck", "Orexin antagonist", "MedLife Suppliers"),
        ("Doxylamine 25mg Sleep", "Sleep Aid", "Various", "Antihistamine", "PharmaCorp"),
        ("Temazepam 15mg", "Sleep Aid", "Mallinckrodt", "Benzodiazepine", "Global Medical Supply"),
        ("Triazolam 0.25mg", "Sleep Aid", "Pfizer", "Benzodiazepine", "Wellness Distributors"),
        ("Estazolam 1mg", "Sleep Aid", "Abbott", "Benzodiazepine", "HealthFirst Suppliers"),
        ("Quazepam 15mg", "Sleep Aid", "Various", "Benzodiazepine", "Amoxil Pharma"),
        ("Midazolam 7.5mg", "Sedatives", "Roche", "Benzodiazepine", "MedLife Suppliers"),
        ("Chlordiazepoxide 10mg", "Sedatives", "ICN", "Benzodiazepine", "PharmaCorp"),
        ("Clorazepate 7.5mg", "Sedatives", "Abbott", "Benzodiazepine", "Global Medical Supply"),
        ("Oxazepam 15mg", "Sedatives", "Wyeth", "Benzodiazepine", "Wellness Distributors"),
        ("Buspirone 10mg", "Anxiolytics", "Bristol-Myers", "Anxiolytic", "HealthFirst Suppliers"),
        ("Hydroxyzine 25mg Oral", "Anxiolytics", "Pfizer", "Antihistamine anxiolytic", "Amoxil Pharma"),
        ("Propranolol 10mg Anxiety", "Anxiolytics", "AstraZeneca", "Beta blocker", "MedLife Suppliers"),
        ("Clonidine 0.1mg", "Antihypertensives", "Boehringer", "Alpha-2 agonist", "PharmaCorp"),
        ("Hydralazine 25mg", "Antihypertensives", "Novartis", "Vasodilator", "Global Medical Supply"),
        ("Minoxidil 10mg Oral", "Antihypertensives", "Pfizer", "Vasodilator", "Wellness Distributors"),
        ("Methyldopa 250mg", "Antihypertensives", "Merck", "Alpha-2 agonist", "HealthFirst Suppliers"),
        ("Labetalol 100mg", "Antihypertensives", "Prometheus", "Alpha/Beta blocker", "Amoxil Pharma"),
        ("Doxazosin 4mg", "Antihypertensives", "Pfizer", "Alpha blocker", "MedLife Suppliers"),
        ("Prazosin 1mg", "Antihypertensives", "Pfizer", "Alpha blocker", "PharmaCorp"),
        ("Terazosin 2mg", "Antihypertensives", "Abbott", "Alpha blocker", "Global Medical Supply"),
    ]
    
    batch_start = 3000
    added = 0
    
    for idx, (drug_name, category, manufacturer, description, supplier) in enumerate(additional_drugs):
        if added >= needed:
            break
            
        batch_number = f"BATCH-{batch_start + idx:05d}"
        current_stock = random.randint(20, 400)
        minimum_stock = random.randint(10, 50)
        unit_price = round(random.uniform(10, 500), 2)
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
            added += 1
        except sqlite3.IntegrityError:
            continue
    
    conn.commit()
    print(f"✅ Added {added} items!")

# Generate consumption patterns for all drugs
print("\n📊 Generating consumption patterns (optimized)...")

# Get all drugs
drugs = cursor.execute("SELECT id, drug_name, category FROM inventory").fetchall()
print(f"Processing {len(drugs)} drugs...")

consumption_added = 0
batch_size = 1000

# Generate 1 year of data instead of 2 years (faster)
consumption_start = datetime.now() - timedelta(days=365)

for drug_id, drug_name, category in drugs:
    # Determine daily consumption based on category
    if category in ["Cardiovascular", "Antidiabetics"]:
        daily_base = random.randint(3, 15)
    elif category in ["Antibiotics", "Analgesics"]:
        daily_base = random.randint(5, 25)
    elif category in ["Gastrointestinal", "Respiratory"]:
        daily_base = random.randint(4, 20)
    else:
        daily_base = random.randint(1, 10)
    
    # Generate daily consumption for past year (every 3 days to reduce volume)
    for day_offset in range(0, 365, 3):  # Every 3 days
        consumption_date = consumption_start + timedelta(days=day_offset)
        month = consumption_date.month
        
        # Seasonal variations
        seasonal_factor = 1.0
        if category == "Respiratory" and month in [11, 12, 1, 2]:
            seasonal_factor = 1.5
        elif category == "Gastrointestinal" and month in [6, 7, 8]:
            seasonal_factor = 1.3
        
        # Weekend factor
        weekday_factor = 0.7 if consumption_date.weekday() >= 5 else 1.0
        
        # Calculate consumption
        base_consumption = daily_base * seasonal_factor * weekday_factor
        noise = np.random.normal(0, base_consumption * 0.15)
        daily_consumption = max(0, int(base_consumption + noise))
        
        if daily_consumption > 0:
            department = random.choice(["Emergency", "ICU", "General Ward", "Pediatrics", "Surgery", "Outpatient"])
            
            try:
                cursor.execute('''
                    INSERT INTO consumption_patterns 
                    (drug_id, date, quantity_consumed, department, created_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (drug_id, consumption_date.strftime('%Y-%m-%d'), 
                      daily_consumption, department, 
                      consumption_date.strftime('%Y-%m-%d %H:%M:%S')))
                
                consumption_added += 1
                
                if consumption_added % batch_size == 0:
                    conn.commit()
                    print(f"  {consumption_added} patterns added...")
                    
            except sqlite3.IntegrityError:
                continue

conn.commit()
print(f"✅ Generated {consumption_added} consumption patterns!")

# Final statistics
final_inv = cursor.execute("SELECT COUNT(*) FROM inventory").fetchone()[0]
final_trans = cursor.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
final_cons = cursor.execute("SELECT COUNT(*) FROM consumption_patterns").fetchone()[0]

print("\n" + "=" * 70)
print("📈 FINAL DATABASE STATISTICS:")
print(f"  Inventory Items: {final_inv}")
print(f"  Transactions: {final_trans:,}")
print(f"  Consumption Patterns: {final_cons:,}")
print("=" * 70)

conn.close()
print("✅ All data generation complete!")

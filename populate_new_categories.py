import sqlite3
import random
from datetime import datetime, timedelta

def populate_baby_care_products(db_path="pharma_inventory.db"):
    """Populate database with 500 unique Baby Care Products"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # First, rename existing non-Drugs categories to Drugs
    cursor.execute("""
        UPDATE inventory 
        SET category = 'Drugs' 
        WHERE category NOT IN ('Drugs', 'Baby Care Products', 'Surgical Items')
    """)
    
    baby_care_items = []
    manufacturers = ["Johnson & Johnson", "Pampers", "Huggies", "Chicco", "Pigeon", 
                    "Mee Mee", "Himalaya Baby", "Mothercare", "Sebamed", "Cetaphil Baby"]
    suppliers = ["PharmaCorp Inc", "MediSupply Co", "HealthDist Ltd"]
    
    # Baby Care Product Categories
    categories_dict = {
        "Diapers": [f"Premium Diapers Size {size}" for size in ["Newborn", "S", "M", "L", "XL", "XXL"]] * 15,
        "Baby Wipes": [f"{brand} Baby Wipes {variant}" for brand in ["Gentle", "Sensitive", "Aloe Vera", "Lavender"] for variant in ["Pack", "Refill", "Travel Pack"]] * 10,
        "Baby Lotion": [f"Baby Moisturizing Lotion {ml}ml" for ml in [100, 200, 400]] * 20,
        "Baby Shampoo": [f"Tear-Free Baby Shampoo {ml}ml" for ml in [100, 200, 400]] * 20,
        "Baby Soap": [f"Gentle Baby Soap {variant}" for variant in ["Bar", "Liquid", "Foam"]] * 20,
        "Baby Oil": [f"Baby Massage Oil {ml}ml" for ml in [100, 200, 500]] * 20,
        "Baby Powder": [f"Talc-Free Baby Powder {gm}gm" for gm in [100, 200, 400]] * 20,
        "Feeding Bottles": [f"BPA-Free Feeding Bottle {ml}ml" for ml in [125, 250, 330]] * 15,
        "Bottle Nipples": [f"Silicone Nipple {flow} Flow" for flow in ["Slow", "Medium", "Fast"]] * 20,
        "Pacifiers": [f"Orthodontic Pacifier {age}" for age in ["0-6m", "6-18m", "18m+"]] * 20,
        "Baby Formula": [f"Infant Formula Stage {stage}" for stage in [1, 2, 3, 4]] * 15,
        "Baby Cereal": [f"Baby Cereal {flavor}" for flavor in ["Rice", "Wheat", "Multi-grain", "Oats"]] * 15,
        "Baby Food": [f"Baby Food {flavor} {stage}+" for flavor in ["Apple", "Banana", "Carrot", "Mixed Fruit"] for stage in ["4m", "6m", "8m"]] * 8,
        "Teething Gel": ["Soothing Teething Gel"] * 30,
        "Baby Gripe Water": ["Herbal Gripe Water 100ml"] * 30,
        "Vitamin Drops": [f"Baby Vitamin D3 Drops {ml}ml" for ml in [15, 30]] * 25,
    }
    
    item_id = 0
    for category, products in categories_dict.items():
        for product_name in products[:50]:
            item_id += 1
            if item_id > 500:
                break
            
            manufacturer = random.choice(manufacturers)
            supplier = random.choice(suppliers)
            batch_number = f"BC{item_id:05d}"
            current_stock = random.randint(50, 500)
            minimum_stock = random.randint(20, 50)
            
            # Price ranges based on product type
            if "Diaper" in product_name:
                per_tablet_price = round(random.uniform(8.0, 25.0), 2)
                tablets_per_sheet = random.choice([20, 30, 40, 50])
            elif "Wipes" in product_name:
                per_tablet_price = round(random.uniform(0.5, 2.0), 2)
                tablets_per_sheet = random.choice([40, 80, 120])
            elif "Bottle" in product_name or "Pacifier" in product_name:
                per_tablet_price = round(random.uniform(150.0, 500.0), 2)
                tablets_per_sheet = 1
            elif "Formula" in product_name or "Cereal" in product_name:
                per_tablet_price = round(random.uniform(300.0, 800.0), 2)
                tablets_per_sheet = 1
            else:
                per_tablet_price = round(random.uniform(50.0, 300.0), 2)
                tablets_per_sheet = 1
            
            per_sheet_price = round(per_tablet_price * tablets_per_sheet, 2)
            unit_price = per_tablet_price
            
            expiry_date = (datetime.now() + timedelta(days=random.randint(180, 730))).strftime("%Y-%m-%d")
            description = f"{product_name} - {category}"
            
            baby_care_items.append((
                product_name, "Baby Care Products", manufacturer, batch_number,
                current_stock, minimum_stock, unit_price, per_tablet_price,
                per_sheet_price, tablets_per_sheet, expiry_date, supplier, description
            ))
    
    # Insert all baby care items
    cursor.executemany('''
        INSERT INTO inventory (drug_name, category, manufacturer, batch_number,
                             current_stock, minimum_stock, unit_price, per_tablet_price,
                             per_sheet_price, tablets_per_sheet, expiry_date, supplier_name, description)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', baby_care_items)
    
    conn.commit()
    print(f"Added {len(baby_care_items)} Baby Care Products")
    return len(baby_care_items)

def populate_surgical_items(db_path="pharma_inventory.db"):
    """Populate database with 500 unique Surgical Items"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    surgical_items = []
    manufacturers = ["Ethicon", "Medtronic", "B.Braun", "Smith & Nephew", "Stryker",
                    "Johnson & Johnson Medical", "Covidien", "Becton Dickinson", "Cardinal Health", "3M Healthcare"]
    suppliers = ["PharmaCorp Inc", "MediSupply Co", "HealthDist Ltd"]
    
    # Surgical Item Categories
    categories_dict = {
        "Gloves": [f"Sterile Surgical Gloves Size {size}" for size in ["6.0", "6.5", "7.0", "7.5", "8.0", "8.5"]] * 15,
        "Syringes": [f"Disposable Syringe {ml}ml" for ml in [1, 2, 3, 5, 10, 20, 50]] * 15,
        "Needles": [f"Hypodermic Needle {gauge}G" for gauge in [18, 20, 21, 22, 23, 25, 27]] * 15,
        "IV Cannula": [f"IV Cannula {size}G {color}" for size, color in [(14, "Orange"), (16, "Grey"), (18, "Green"), (20, "Pink"), (22, "Blue"), (24, "Yellow")]] * 17,
        "Sutures": [f"{material} Suture {size}" for material in ["Silk", "Nylon", "Vicryl", "Chromic"] for size in ["2-0", "3-0", "4-0", "5-0"]] * 8,
        "Surgical Blades": [f"Surgical Blade No. {num}" for num in [10, 11, 12, 15, 20, 22, 23]] * 15,
        "Gauze": [f"Sterile Gauze {size}cm x {size}cm" for size in [5, 7.5, 10]] * 30,
        "Bandages": [f"Elastic Bandage {width}cm" for width in [5, 7.5, 10, 15]] * 25,
        "Surgical Masks": [f"{type} Surgical Mask" for type in ["3-Ply", "N95", "KN95", "FFP2"]] * 25,
        "Catheters": [f"Foley Catheter {size}Fr" for size in [12, 14, 16, 18, 20]] * 20,
        "Drainage Tubes": [f"Surgical Drain {size}Fr" for size in [10, 12, 14, 16]] * 25,
        "Surgical Drapes": [f"Sterile Surgical Drape {size}cm" for size in [50, 75, 100]] * 30,
        "Scalpels": [f"Disposable Scalpel No. {num}" for num in [10, 11, 15, 20, 22]] * 20,
        "Forceps": [f"Surgical Forceps {type}" for type in ["Tissue", "Hemostatic", "Artery", "Splinter"]] * 25,
        "Scissors": [f"Surgical Scissors {type}" for type in ["Mayo", "Metzenbaum", "Iris", "Bandage"]] * 25,
        "Retractors": [f"Surgical Retractor {type}" for type in ["Army-Navy", "Deaver", "Richardson", "Weitlaner"]] * 25,
    }
    
    item_id = 0
    for category, products in categories_dict.items():
        for product_name in products[:50]:
            item_id += 1
            if item_id > 500:
                break
            
            manufacturer = random.choice(manufacturers)
            supplier = random.choice(suppliers)
            batch_number = f"SG{item_id:05d}"
            current_stock = random.randint(100, 1000)
            minimum_stock = random.randint(50, 100)
            
            # Price ranges based on product type
            if "Glove" in product_name:
                per_tablet_price = round(random.uniform(5.0, 15.0), 2)
                tablets_per_sheet = 100
            elif "Syringe" in product_name or "Needle" in product_name:
                per_tablet_price = round(random.uniform(2.0, 10.0), 2)
                tablets_per_sheet = random.choice([50, 100])
            elif "Cannula" in product_name:
                per_tablet_price = round(random.uniform(15.0, 40.0), 2)
                tablets_per_sheet = 50
            elif "Suture" in product_name:
                per_tablet_price = round(random.uniform(50.0, 200.0), 2)
                tablets_per_sheet = 12
            elif "Blade" in product_name or "Scalpel" in product_name:
                per_tablet_price = round(random.uniform(8.0, 25.0), 2)
                tablets_per_sheet = 100
            elif "Gauze" in product_name or "Bandage" in product_name:
                per_tablet_price = round(random.uniform(3.0, 12.0), 2)
                tablets_per_sheet = random.choice([10, 20, 50])
            elif "Mask" in product_name:
                per_tablet_price = round(random.uniform(2.0, 50.0), 2)
                tablets_per_sheet = random.choice([50, 100])
            elif "Catheter" in product_name or "Drain" in product_name:
                per_tablet_price = round(random.uniform(50.0, 200.0), 2)
                tablets_per_sheet = 10
            elif "Drape" in product_name:
                per_tablet_price = round(random.uniform(20.0, 80.0), 2)
                tablets_per_sheet = 20
            elif "Forceps" in product_name or "Scissors" in product_name or "Retractor" in product_name:
                per_tablet_price = round(random.uniform(200.0, 800.0), 2)
                tablets_per_sheet = 1
            else:
                per_tablet_price = round(random.uniform(10.0, 100.0), 2)
                tablets_per_sheet = random.choice([1, 10, 20])
            
            per_sheet_price = round(per_tablet_price * tablets_per_sheet, 2)
            unit_price = per_tablet_price
            
            expiry_date = (datetime.now() + timedelta(days=random.randint(365, 1095))).strftime("%Y-%m-%d")
            description = f"{product_name} - {category}"
            
            surgical_items.append((
                product_name, "Surgical Items", manufacturer, batch_number,
                current_stock, minimum_stock, unit_price, per_tablet_price,
                per_sheet_price, tablets_per_sheet, expiry_date, supplier, description
            ))
    
    # Insert all surgical items
    cursor.executemany('''
        INSERT INTO inventory (drug_name, category, manufacturer, batch_number,
                             current_stock, minimum_stock, unit_price, per_tablet_price,
                             per_sheet_price, tablets_per_sheet, expiry_date, supplier_name, description)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', surgical_items)
    
    conn.commit()
    print(f"Added {len(surgical_items)} Surgical Items")
    return len(surgical_items)

if __name__ == "__main__":
    print("Starting population of new categories...")
    baby_count = populate_baby_care_products()
    surgical_count = populate_surgical_items()
    print(f"\nPopulation complete!")
    print(f"Total Baby Care Products: {baby_count}")
    print(f"Total Surgical Items: {surgical_count}")
    print(f"Total new items added: {baby_count + surgical_count}")

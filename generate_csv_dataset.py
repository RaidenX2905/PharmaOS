"""Deterministic generator for pharma_dataset_12000.csv.

Schema matches the CSV import path in app.py:
  drug_name, category, manufacturer, batch_number, current_stock,
  minimum_stock, unit_price, per_tablet_price, per_sheet_price,
  tablets_per_sheet, expiry_date, supplier_name, description

Seed fixed for reproducibility. All values are synthetic and explicitly
labelled as generated demonstration data, not real clinical records.
"""

import csv
import random
from datetime import datetime, timedelta

SEED = 42
N_ROWS = 12000
random.seed(SEED)

DRUG_CATALOG = [
    ("Paracetamol 500mg", "Analgesics", "Generic Pharma", 10.50),
    ("Ibuprofen 400mg", "Analgesics", "Pain Relief Co", 15.75),
    ("Aspirin 75mg", "Analgesics", "Cardio Pharma", 8.25),
    ("Amoxicillin 250mg", "Antibiotics", "BioCure Ltd", 45.00),
    ("Ciprofloxacin 500mg", "Antibiotics", "MediCorp", 65.50),
    ("Azithromycin 250mg", "Antibiotics", "PharmaTech", 85.00),
    ("Metformin 500mg", "Diabetes", "DiaCare", 25.50),
    ("Glipizide 5mg", "Diabetes", "Sugar Control Inc", 35.75),
    ("Insulin Rapid", "Diabetes", "EndoPharm", 450.00),
    ("Atenolol 50mg", "Cardiovascular", "HeartCare", 28.50),
    ("Lisinopril 10mg", "Cardiovascular", "BP Pharma", 42.00),
    ("Amlodipine 5mg", "Cardiovascular", "Cardio Plus", 38.25),
    ("Omeprazole 20mg", "Gastrointestinal", "Gastro Med", 32.00),
    ("Cetirizine 10mg", "Allergy", "Allergy Free", 12.75),
    ("Prednisolone 5mg", "Steroids", "Steroid Pharma", 55.00),
    ("Salbutamol Inhaler", "Respiratory", "Breathe Easy", 125.00),
    ("Atorvastatin 20mg", "Cardiovascular", "LipidCare", 52.00),
    ("Warfarin 5mg", "Cardiovascular", "Blood Thin Co", 72.50),
    ("Tramadol 50mg", "Analgesics", "Pain Control Ltd", 95.00),
    ("Diazepam 5mg", "Sedatives", "Calm Pharma", 42.00),
]

SUPPLIERS = [
    "MedSupply International", "PharmaDirect", "HealthCare Distributors",
    "Global Med Solutions", "QuickMed Supply", "PharmaHub",
    "MediSource Pro", "HealthFirst Suppliers", "CarePlus Distribution",
]

CATEGORIES = {c for _, c, _, _ in DRUG_CATALOG}


def gen_row(idx):
    drug_name, category, manufacturer, base_price = DRUG_CATALOG[idx % len(DRUG_CATALOG)]
    batch_number = f"B{idx+1:07d}"
    current_stock = random.randint(0, 500)
    minimum_stock = random.randint(5, 50)
    unit_price = round(base_price * random.uniform(0.9, 1.15), 2)
    tablets_per_sheet = random.choice([10, 100, 500])
    per_tablet_price = unit_price
    per_sheet_price = round(unit_price * tablets_per_sheet, 2)
    days_until_expiry = random.randint(30, 1095)
    expiry_date = (datetime.now() + timedelta(days=days_until_expiry)).strftime("%Y-%m-%d")
    supplier = random.choice(SUPPLIERS)
    description = f"{drug_name} - {category} medication"
    return [
        drug_name, category, manufacturer, batch_number, current_stock,
        minimum_stock, unit_price, per_tablet_price, per_sheet_price,
        tablets_per_sheet, expiry_date, supplier, description,
    ]


def main():
    with open("pharma_dataset_12000.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "drug_name", "category", "manufacturer", "batch_number",
            "current_stock", "minimum_stock", "unit_price",
            "per_tablet_price", "per_sheet_price", "tablets_per_sheet",
            "expiry_date", "supplier_name", "description",
        ])
        for i in range(N_ROWS):
            writer.writerow(gen_row(i))
    print(f"Wrote {N_ROWS} rows to pharma_dataset_12000.csv (seed={SEED})")


if __name__ == "__main__":
    main()
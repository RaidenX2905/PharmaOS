import sqlite3
import random
from datetime import datetime, timedelta

def populate_consumption_patterns(db_path="pharma_inventory.db"):
    """Populate consumption patterns for all inventory items"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all inventory items
    cursor.execute("SELECT id, drug_name, category FROM inventory")
    items = cursor.fetchall()
    
    print(f"Populating consumption data for {len(items)} inventory items...")
    
    # Clear existing consumption patterns to avoid duplicates
    cursor.execute("DELETE FROM consumption_patterns")
    
    consumption_records = []
    
    for item_id, drug_name, category in items:
        # Generate consumption data for last 180 days
        for days_ago in range(180):
            date = datetime.now() - timedelta(days=days_ago)
            
            # Base consumption based on category
            if category == "Drugs":
                base_consumption = random.randint(5, 20)
            elif category == "Baby Care Products":
                base_consumption = random.randint(10, 30)
            elif category == "Surgical Items":
                base_consumption = random.randint(15, 50)
            else:
                base_consumption = random.randint(5, 15)
            
            # Add randomness and weekly patterns
            day_of_week = date.weekday()
            
            # Higher consumption on weekdays
            if day_of_week < 5:  # Monday to Friday
                consumption = base_consumption + random.randint(-2, 5)
            else:  # Weekend
                consumption = int(base_consumption * 0.6) + random.randint(-1, 2)
            
            # Ensure non-negative
            consumption = max(0, consumption)
            
            # Random department
            department = random.choice(['ICU', 'Emergency', 'General Ward', 'Outpatient', 'Pharmacy'])
            
            consumption_records.append((
                item_id,
                date.date(),
                consumption,
                department,
                f"Auto-generated consumption data for {drug_name}"
            ))
    
    # Insert all consumption data
    cursor.executemany('''
        INSERT INTO consumption_patterns (drug_id, date, quantity_consumed, department, notes)
        VALUES (?, ?, ?, ?, ?)
    ''', consumption_records)
    
    conn.commit()
    print(f"Successfully added {len(consumption_records)} consumption records")
    print(f"Total items with consumption history: {len(items)}")
    
    # Verify the data
    cursor.execute("SELECT COUNT(*) FROM consumption_patterns")
    total_records = cursor.fetchone()[0]
    print(f"Total consumption records in database: {total_records}")
    
    conn.close()

if __name__ == "__main__":
    print("Starting consumption data population...")
    populate_consumption_patterns()
    print("\nConsumption data population complete!")

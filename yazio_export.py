import requests
import json
import os
import sys
import sqlite3
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Constants
TOKEN_URL = "https://yzapi.yazio.com/v15/oauth/token"
BASE_URL = "https://yzapi.yazio.com/v15"
CLIENT_ID = "1_4hiybetvfksgw40o0sog4s884kwc840wwso8go4k8c04goo4c"
CLIENT_SECRET = "6rok2m65xuskgkgogw40wkkk8sw0osg84s8cggsc4woos4s8o"

class YazioClient:
    def __init__(self, email, password):
        self.email = email
        self.password = password
        self.access_token = None
        self.session = requests.Session()

    def login(self):
        """Authenticates with Yazio and retrieves an access token."""
        payload = {
            "grant_type": "password",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "username": self.email,
            "password": self.password
        }
        
        response = self.session.post(TOKEN_URL, json=payload)
        if response.status_code != 200:
            print(f"Login failed: {response.status_code}")
            return False
            
        data = response.json()
        self.access_token = data.get("access_token")
        self.session.headers.update({
            "Authorization": f"Bearer {self.access_token}"
        })
        return True

    def discover_dates(self, years_back=5):
        """Discovers all dates that have data."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365 * years_back)
        
        url = f"{BASE_URL}/user/consumed-items/nutrients-daily"
        params = {
            "start": start_date.strftime("%Y-%m-%d"),
            "end": end_date.strftime("%Y-%m-%d")
        }
        
        print(f"Discovering dates from {params['start']} to {params['end']}...")
        response = self.session.get(url, params=params)
        if response.status_code != 200:
            print(f"Discovery failed: {response.status_code}")
            return []
            
        data = response.json()
        # The API returns a list of objects with a 'date' field
        dates = [item['date'] for item in data]
        return sorted(dates)

    def get_daily_summary(self, date_str):
        url = f"{BASE_URL}/user/widgets/daily-summary"
        params = {"date": date_str}
        response = self.session.get(url, params=params)
        return response.json() if response.status_code == 200 else None

    def get_consumed_items(self, date_str):
        url = f"{BASE_URL}/user/consumed-items"
        params = {"date": date_str}
        response = self.session.get(url, params=params)
        return response.json() if response.status_code == 200 else None

    def get_product_info(self, product_id):
        """Fetches detailed information for a specific product."""
        url = f"{BASE_URL}/products/{product_id}"
        response = self.session.get(url)
        if response.status_code == 200:
            return response.json()
        return None

class YazioDatabase:
    def __init__(self, db_path="yazio_data.db"):
        self.conn = sqlite3.connect(db_path)
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        
        # Daily Summary table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_summaries (
                date TEXT PRIMARY KEY,
                activity_energy REAL,
                steps INTEGER,
                water_intake REAL,
                goal_energy REAL,
                goal_water REAL,
                goal_steps INTEGER,
                goal_protein REAL,
                goal_fat REAL,
                goal_carb REAL,
                actual_protein REAL,
                actual_fat REAL,
                actual_carb REAL,
                breakfast_energy REAL,
                breakfast_carb REAL,
                breakfast_fat REAL,
                breakfast_protein REAL,
                lunch_energy REAL,
                lunch_carb REAL,
                lunch_fat REAL,
                lunch_protein REAL,
                dinner_energy REAL,
                dinner_carb REAL,
                dinner_fat REAL,
                dinner_protein REAL,
                snack_energy REAL,
                snack_carb REAL,
                snack_fat REAL,
                snack_protein REAL,
                user_current_weight REAL,
                raw_json TEXT
            )
        ''')
        
        # Products metadata table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id TEXT PRIMARY KEY,
                name TEXT,
                brand TEXT,
                cal_per_unit REAL,
                carb_per_unit REAL,
                fat_per_unit REAL,
                prot_per_unit REAL
            )
        ''')

        # Consumed Items table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS consumed_items (
                id TEXT PRIMARY KEY,
                date TEXT,
                log_time TEXT,
                daytime TEXT,
                type TEXT,
                product_id TEXT,
                name TEXT,
                amount REAL,
                serving TEXT,
                serving_quantity REAL,
                calories REAL,
                carb REAL,
                fat REAL,
                protein REAL,
                is_ai INTEGER DEFAULT 0,
                FOREIGN KEY (date) REFERENCES daily_summaries (date),
                FOREIGN KEY (product_id) REFERENCES products (id)
            )
        ''')
        
        self.conn.commit()

    def get_cached_product(self, product_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT name, cal_per_unit, carb_per_unit, fat_per_unit, prot_per_unit FROM products WHERE id = ?", (product_id,))
        return cursor.fetchone()

    def save_product(self, product_id, name, brand=None, cal=0, carb=0, fat=0, prot=0):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO products (id, name, brand, cal_per_unit, carb_per_unit, fat_per_unit, prot_per_unit) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (product_id, name, brand, cal, carb, fat, prot))
        self.conn.commit()

    def save_day(self, client, date_str, summary, consumed_items):
        cursor = self.conn.cursor()
        
        # Save summary
        if summary:
            goals = summary.get("goals", {})
            user = summary.get("user", {})
            meals = summary.get("meals", {})
            
            # Helper to get meal nutrients
            def get_meal_data(meal_name):
                m = meals.get(meal_name, {}).get("nutrients", {})
                return (
                    m.get("energy.energy", 0),
                    m.get("nutrient.carb", 0),
                    m.get("nutrient.fat", 0),
                    m.get("nutrient.protein", 0)
                )

            b_e, b_c, b_f, b_p = get_meal_data("breakfast")
            l_e, l_c, l_f, l_p = get_meal_data("lunch")
            d_e, d_c, d_f, d_p = get_meal_data("dinner")
            s_e, s_c, s_f, s_p = get_meal_data("snack")

            actual_protein = b_p + l_p + d_p + s_p
            actual_carb = b_c + l_c + d_c + s_c
            actual_fat = b_f + l_f + d_f + s_f

            cursor.execute('''
                INSERT OR REPLACE INTO daily_summaries (
                    date, activity_energy, steps, water_intake,
                    goal_energy, goal_water, goal_steps, goal_protein, goal_fat, goal_carb,
                    actual_protein, actual_fat, actual_carb,
                    breakfast_energy, breakfast_carb, breakfast_fat, breakfast_protein,
                    lunch_energy, lunch_carb, lunch_fat, lunch_protein,
                    dinner_energy, dinner_carb, dinner_fat, dinner_protein,
                    snack_energy, snack_carb, snack_fat, snack_protein,
                    user_current_weight, raw_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                date_str,
                summary.get("activity_energy"),
                summary.get("steps"),
                summary.get("water_intake"),
                goals.get("energy.energy"),
                goals.get("water"),
                goals.get("activity.step"),
                goals.get("nutrient.protein"),
                goals.get("nutrient.fat"),
                goals.get("nutrient.carb"),
                actual_protein,
                actual_fat,
                actual_carb,
                b_e, b_c, b_f, b_p,
                l_e, l_c, l_f, l_p,
                d_e, d_c, d_f, d_p,
                s_e, s_c, s_f, s_p,
                user.get("current_weight"),
                json.dumps(summary)
            ))

        # Save consumed items
        for list_key in ["products", "simple_products", "recipe_portions"]:
            if consumed_items and list_key in consumed_items:
                for item in consumed_items[list_key]:
                    p_id = item.get("product_id") or item.get("recipe_id")
                    name = item.get("name")
                    is_ai = 1 if item.get("is_ai_generated") else 0
                    
                    # Get nutrients if available directly in item (simple_products or specific logs)
                    item_nutrients = item.get("nutrients", {})
                    cal = item_nutrients.get("energy.energy", 0)
                    carb = item_nutrients.get("nutrient.carb", 0)
                    fat = item_nutrients.get("nutrient.fat", 0)
                    prot = item_nutrients.get("nutrient.protein", 0)

                    if p_id:
                        cached = self.get_cached_product(p_id)
                        if cached:
                            name = cached[0] if not name else name
                            # If calories are 0 in item but we have cached per-unit values, calculate them
                            if cal == 0 and cached[1] is not None:
                                amount = item.get("amount", 1) # Fallback to 1 if amount missing
                                cal = cached[1] * amount
                                carb = cached[2] * amount
                                fat = cached[3] * amount
                                prot = cached[4] * amount
                        else:
                            # Fetch from API
                            p_info = client.get_product_info(p_id)
                            if p_info:
                                name = p_info.get("name") if not name else name
                                p_nutrients = p_info.get("nutrients", {})
                                p_cal = p_nutrients.get("energy.energy", 0)
                                p_carb = p_nutrients.get("nutrient.carb", 0)
                                p_fat = p_nutrients.get("nutrient.fat", 0)
                                p_prot = p_nutrients.get("nutrient.protein", 0)
                                
                                self.save_product(p_id, name, p_info.get("brand"), p_cal, p_carb, p_fat, p_prot)
                                
                                if cal == 0:
                                    amount = item.get("amount", 1)
                                    cal = p_cal * amount
                                    carb = p_carb * amount
                                    fat = p_fat * amount
                                    prot = p_prot * amount
                    
                    # Use ID if name still missing
                    if not name:
                        name = f"Unknown {item.get('type', 'item')}"

                    cursor.execute('''
                        INSERT OR REPLACE INTO consumed_items (
                            id, date, log_time, daytime, type, product_id, name, amount, serving, serving_quantity,
                            calories, carb, fat, protein, is_ai
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        item.get("id"),
                        date_str,
                        item.get("date"),
                        item.get("daytime"),
                        item.get("type"),
                        p_id,
                        name,
                        item.get("amount"),
                        item.get("serving"),
                        item.get("serving_quantity"),
                        cal,
                        carb,
                        fat,
                        prot,
                        is_ai
                    ))
        
        self.conn.commit()

    def close(self):
        self.conn.close()

def main():
    load_dotenv()
    email, password = os.getenv("YAZIO_EMAIL"), os.getenv("YAZIO_PASSWORD")
    
    if not email or not password:
        print("Error: YAZIO_EMAIL and YAZIO_PASSWORD must be set in .env file.")
        sys.exit(1)
        
    client = YazioClient(email, password)
    if not client.login():
        sys.exit(1)
        
    db = YazioDatabase()
    
    dates = client.discover_dates()
    print(f"Found {len(dates)} days with data.")
    
    for i, date_str in enumerate(dates):
        print(f"[{i+1}/{len(dates)}] Exporting {date_str}...", end="\r")
        summary = client.get_daily_summary(date_str)
        consumed = client.get_consumed_items(date_str)
        db.save_day(client, date_str, summary, consumed)
        
    print(f"\nExport complete. Data saved to yazio_data.db")
    db.close()

if __name__ == "__main__":
    main()

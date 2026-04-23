import sqlite3
import json
import os

def export_data():
    db_path = "yazio_data.db"
    json_path = "dashboard_data.json"
    
    if not os.path.exists(db_path):
        print(f"Error: {db_path} not found. Run the exporter script first.")
        return

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM daily_summaries 
        ORDER BY date ASC
    ''')
    
    rows = cursor.fetchall()
    data = [dict(row) for row in rows]
    
    with open(json_path, "w") as f:
        json.dump(data, f, indent=4)
        
    print(f"Exported {len(data)} days with full metrics to {json_path}")
    conn.close()

if __name__ == "__main__":
    export_data()

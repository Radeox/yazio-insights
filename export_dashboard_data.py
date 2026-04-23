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
    
    # Get daily summaries
    cursor.execute('SELECT * FROM daily_summaries ORDER BY date ASC')
    summaries = [dict(row) for row in cursor.fetchall()]
    
    # Get consumed items
    cursor.execute('SELECT * FROM consumed_items ORDER BY date ASC, daytime ASC')
    items = [dict(row) for row in cursor.fetchall()]
    
    # Nest items inside summaries for easier frontend access
    items_by_date = {}
    for item in items:
        date = item['date']
        if date not in items_by_date:
            items_by_date[date] = []
        items_by_date[date].append(item)
        
    for summary in summaries:
        summary['food_log'] = items_by_date.get(summary['date'], [])
    
    with open(json_path, "w") as f:
        json.dump(summaries, f, indent=4)
        
    print(f"Exported {len(summaries)} days with full metrics and food logs to {json_path}")
    conn.close()

if __name__ == "__main__":
    export_data()

# db.py
import sqlite3
from datetime import datetime
import json
import os

DB_PATH = "lost_and_found.db"
REPORTS_PATH = "reports/resolutions.json"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database with all tables"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Items table (with user details + image path)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,  -- 'lost' or 'found'
            category TEXT NOT NULL,
            description TEXT NOT NULL,
            location TEXT NOT NULL,
            date_lost_found TEXT NOT NULL,
            name TEXT NOT NULL,
            branch TEXT NOT NULL,
            section TEXT,
            contact TEXT NOT NULL,
            email TEXT,
            image_path TEXT,
            status TEXT DEFAULT 'open',  -- 'open', 'claimed', 'returned'
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Claims table (tracks resolutions)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS claims (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lost_item_id INTEGER NOT NULL,
            found_item_id INTEGER NOT NULL,
            claimant_name TEXT NOT NULL,
            claimant_branch TEXT NOT NULL,
            claimant_section TEXT,
            claimant_contact TEXT NOT NULL,
            verification_note TEXT NOT NULL,
            status TEXT DEFAULT 'pending',  -- 'pending', 'approved', 'rejected'
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            resolved_at TIMESTAMP,
            FOREIGN KEY (lost_item_id) REFERENCES items(id),
            FOREIGN KEY (found_item_id) REFERENCES items(id)
        )
    ''')
    
    conn.commit()
    conn.close()
    
    # Create reports folder if not exists
    os.makedirs("reports", exist_ok=True)

def add_item(item_type, category, description, location, date_lost_found,
             name, branch, section, contact, email, image_path=None):
    """Add a new lost or found item"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO items (type, category, description, location, date_lost_found,
                          name, branch, section, contact, email, image_path)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (item_type, category, description, location, date_lost_found,
          name, branch, section, contact, email, image_path))
    
    item_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return item_id

def get_items(item_type=None, category=None, status='open'):
    """Get items with optional filters"""
    conn = get_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM items WHERE 1=1"
    params = []
    
    if item_type:
        query += " AND type = ?"
        params.append(item_type)
    
    if category:
        query += " AND category = ?"
        params.append(category)
    
    if status:
        query += " AND status = ?"
        params.append(status)
    
    query += " ORDER BY created_at DESC"
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]

def get_item_by_id(item_id):
    """Get single item by ID"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM items WHERE id = ?", (item_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def update_item_status(item_id, status):
    """Update item status (open/claimed/returned)"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE items SET status = ? WHERE id = ?", (status, item_id))
    conn.commit()
    conn.close()

def add_claim(lost_item_id, found_item_id, claimant_name, claimant_branch,
              claimant_section, claimant_contact, verification_note):
    """Add a claim for matching items"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO claims (lost_item_id, found_item_id, claimant_name,
                           claimant_branch, claimant_section, claimant_contact,
                           verification_note)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (lost_item_id, found_item_id, claimant_name, claimant_branch,
          claimant_section, claimant_contact, verification_note))
    
    claim_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return claim_id

def approve_claim(claim_id):
    """Approve a claim and update item statuses"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Get claim details
    cursor.execute("SELECT * FROM claims WHERE id = ?", (claim_id,))
    claim = dict(cursor.fetchone())
    
    # Update claim status
    cursor.execute('''
        UPDATE claims SET status = 'approved', resolved_at = ? WHERE id = ?
    ''', (datetime.now().isoformat(), claim_id))
    
    # Update both items to 'returned'
    cursor.execute("UPDATE items SET status = 'returned' WHERE id = ?",
                  (claim['lost_item_id'],))
    cursor.execute("UPDATE items SET status = 'returned' WHERE id = ?",
                  (claim['found_item_id'],))
    
    # Save to resolution report
    save_resolution(claim)
    
    conn.commit()
    conn.close()

def save_resolution(claim):
    """Save resolution to JSON report"""
    resolutions = []
    
    # Load existing resolutions
    if os.path.exists(REPORTS_PATH):
        with open(REPORTS_PATH, 'r') as f:
            resolutions = json.load(f)
    
    # Add new resolution
    resolution = {
        'claim_id': claim['id'],
        'lost_item_id': claim['lost_item_id'],
        'found_item_id': claim['found_item_id'],
        'claimant_name': claim['claimant_name'],
        'claimant_branch': claim['claimant_branch'],
        'resolved_at': datetime.now().isoformat()
    }
    resolutions.append(resolution)
    
    # Save back
    with open(REPORTS_PATH, 'w') as f:
        json.dump(resolutions, f, indent=2)

def get_stats():
    """Get statistics for dashboard"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Total lost items
    cursor.execute("SELECT COUNT(*) FROM items WHERE type = 'lost'")
    total_lost = cursor.fetchone()[0]
    
    # Total found items
    cursor.execute("SELECT COUNT(*) FROM items WHERE type = 'found'")
    total_found = cursor.fetchone()[0]
    
    # Returned items (half of matched pairs)
    cursor.execute("SELECT COUNT(*) FROM items WHERE status = 'returned' AND type = 'lost'")
    total_returned = cursor.fetchone()[0]
    
    # Pending claims
    cursor.execute("SELECT COUNT(*) FROM claims WHERE status = 'pending'")
    pending_claims = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        'total_lost': total_lost,
        'total_found': total_found,
        'total_returned': total_returned,
        'pending_claims': pending_claims,
        'return_rate': round((total_returned / total_lost * 100), 1) if total_lost > 0 else 0
    }

# Initialize DB on import
init_db()
import sqlite3
from datetime import datetime

db_path = 'investment.db'

# Check existing settings
with sqlite3.connect(db_path) as conn:
    cursor = conn.cursor()
    
    # Query all settings
    cursor.execute('SELECT * FROM settings')
    settings = cursor.fetchall()
    print('Current settings:')
    for s in settings:
        print(f'  {s[0]}: {s[1]}')
    
    # Check if cash_balance exists
    cursor.execute('SELECT value FROM settings WHERE key = ?', ('cash_balance',))
    cash_balance = cursor.fetchone()
    
    if cash_balance:
        cash_value = float(cash_balance[0])
        print(f'\nFound cash_balance: {cash_value}')
        
        # Check if available_asset exists
        cursor.execute('SELECT value FROM settings WHERE key = ?', ('available_asset',))
        available_asset = cursor.fetchone()
        
        if not available_asset:
            # Convert cash_balance to available_asset
            cursor.execute(
                'INSERT INTO settings (key, value, updated_at) VALUES (?, ?, ?)',
                ('available_asset', str(cash_value), datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            )
            print(f'Created available_asset: {cash_value}')
            print('Kept cash_balance for backward compatibility')
        else:
            print(f'available_asset already exists: {available_asset[0]}')
    
    conn.commit()
    
    # Display all settings again
    print('\nUpdated settings:')
    cursor.execute('SELECT * FROM settings')
    for s in cursor.fetchall():
        print(f'  {s[0]}: {s[1]}')

print('\nDatabase update completed!')
"""
Script to export the entire Supabase database schema to a CSV file
"""
import os
import sys
import csv
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).resolve().parent / '.env'
print(f"Loading .env from: {env_path} (exists: {env_path.exists()})")
load_dotenv(dotenv_path=env_path)

from supabase import create_client

# Get Supabase credentials
supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_KEY')

if not supabase_url or not supabase_key:
    print("Missing Supabase credentials in .env file")
    sys.exit(1)

print(f"Connecting to Supabase at {supabase_url}")
client = create_client(supabase_url, supabase_key)

# SQL to get all tables and their columns
schema_sql = """
SELECT
    t.table_name,
    c.column_name,
    c.data_type,
    c.column_default,
    c.is_nullable,
    c.character_maximum_length,
    pg_catalog.col_description(format('%s.%s', c.table_schema, c.table_name)::regclass::oid, c.ordinal_position) as column_description
FROM
    information_schema.tables t
JOIN
    information_schema.columns c ON t.table_name = c.table_name AND t.table_schema = c.table_schema
WHERE
    t.table_schema = 'public'
ORDER BY
    t.table_name,
    c.ordinal_position;
"""

try:
    # Execute the SQL query using RPC
    print("Fetching schema information...")
    response = client.rpc('execute_sql', {'sql': schema_sql}).execute()
    
    if hasattr(response, 'data') and response.data:
        schema_data = response.data
        
        # Write to CSV file
        csv_file_path = Path(__file__).resolve().parent / 'database_schema.csv'
        print(f"Writing schema to {csv_file_path}")
        
        with open(csv_file_path, 'w', newline='') as csvfile:
            fieldnames = ['table_name', 'column_name', 'data_type', 'column_default', 
                         'is_nullable', 'character_maximum_length', 'column_description']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for row in schema_data:
                writer.writerow(row)
        
        print(f"Schema exported successfully to {csv_file_path}")
        
        # Also print a summary of tables
        tables = set(row['table_name'] for row in schema_data)
        print(f"\nFound {len(tables)} tables in the database:")
        for table in sorted(tables):
            columns = [row for row in schema_data if row['table_name'] == table]
            print(f"- {table} ({len(columns)} columns)")
    else:
        print("No schema data returned. Check if you have appropriate permissions.")
        
except Exception as e:
    print(f"Error querying database schema: {str(e)}")
    
    # Try an alternative approach if the RPC fails
    try:
        print("\nTrying alternative query method...")
        tables_response = client.table('pg_tables').select('schemaname,tablename').eq('schemaname', 'public').execute()
        
        if hasattr(tables_response, 'data') and tables_response.data:
            tables = tables_response.data
            
            # Create CSV file
            csv_file_path = Path(__file__).resolve().parent / 'database_schema.csv'
            print(f"Writing schema to {csv_file_path}")
            
            with open(csv_file_path, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['table_name', 'column_name', 'data_type', 'is_nullable', 'column_default'])
                
                # For each table, get its columns
                for table in tables:
                    table_name = table['tablename']
                    print(f"Getting columns for {table_name}...")
                    
                    try:
                        # Get one row to see column names
                        columns_response = client.table(table_name).select('*').limit(1).execute()
                        if hasattr(columns_response, 'data') and columns_response.data:
                            for column in columns_response.data[0].keys():
                                writer.writerow([table_name, column, "N/A", "N/A", "N/A"])
                    except Exception as table_err:
                        print(f"  Error getting columns for {table_name}: {str(table_err)}")
                        writer.writerow([table_name, "ERROR", str(table_err), "", ""])
            
            print(f"Limited schema information exported to {csv_file_path}")
        else:
            print("Could not retrieve table list.")
    except Exception as alt_err:
        print(f"Alternative approach also failed: {str(alt_err)}")
        print("Please check your database permissions or try running SQL directly in the Supabase dashboard.") 
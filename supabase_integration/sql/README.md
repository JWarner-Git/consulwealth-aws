# Database Schema Update Instructions

This directory contains SQL scripts for updating the database schema in Supabase.

## Running the `plaid_schema_update.sql` Script

The `plaid_schema_update.sql` script modifies the `plaid_items` table to add columns required for our enhanced Plaid refresh strategy.

### Steps to Run the Script

1. Log in to your Supabase dashboard at https://app.supabase.com/
2. Select your ConsulWealth project
3. Click on "SQL Editor" in the left navigation menu
4. Click "New Query" button
5. Copy the entire contents of the `plaid_schema_update.sql` file and paste it into the SQL editor
6. Click "Run" to execute the script

### What the Script Does

The script:

1. Creates the `plaid_items` table if it doesn't exist
2. Adds new columns to support the refresh strategy:
   - `last_successful_update`: Timestamp of the last successful data refresh
   - `last_connection_time`: Timestamp of the last time the user connected/reconnected
   - `connection_status`: Status of the connection ('active', 'error', etc.)
   - `update_type`: Type of the last update ('initial', 'soft', 'hard')
   - `next_hard_refresh`: Scheduled time for the next hard refresh
3. Initializes these columns with appropriate values for any existing rows

### Verification

After running the script, you can verify the changes by:

1. Going to the "Table Editor" in the Supabase dashboard
2. Selecting the `plaid_items` table
3. Checking that the new columns exist

## Troubleshooting

If you encounter errors:

- Check if you have the necessary permissions (need admin role)
- Ensure the script is executed in the correct database
- If specific column additions fail, you may need to run those parts of the script individually 
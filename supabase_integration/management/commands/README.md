# Plaid Integration Management Commands

This directory contains management commands for maintaining the Plaid integration.

## `refresh_plaid_data.py`

This command is used to refresh Plaid data for users according to our scheduled refresh strategy.

### Usage

```bash
# Perform a soft refresh for all items that need it (weekly)
python manage.py refresh_plaid_data --type soft

# Check items that need a hard refresh (quarterly)
python manage.py refresh_plaid_data --type hard

# Refresh a specific user's data
python manage.py refresh_plaid_data --user_id <user_id> --type soft
```

### Refresh Strategy

Our Plaid integration uses a cost-efficient refresh strategy:

1. **Soft Refreshes (Weekly)**
   - Automatically fetch new transactions and updated balances
   - Uses existing access tokens without requiring user interaction
   - Scheduled to run weekly to keep data fresh
   - Low cost as it only involves API calls

2. **Hard Refreshes (Quarterly)**
   - Requires user re-authentication through Plaid Link
   - Discovers any new accounts at the institution
   - Refreshes all permissions and ensures continued data access
   - Higher cost, so limited to quarterly schedule
   - Cannot be fully automated (requires user interaction)

### Setting Up a Cron Job

To automatically run the soft refreshes, you can set up a cron job:

```bash
# Weekly soft refresh (every Monday at 3 AM)
0 3 * * 1 cd /path/to/clean_backend && python manage.py refresh_plaid_data --type soft

# Monthly check for items needing hard refresh (1st of each month)
0 4 1 * * cd /path/to/clean_backend && python manage.py refresh_plaid_data --type hard
```

### Handling Hard Refreshes

Since hard refreshes require user interaction, the command with `--type hard` will only identify which items need a hard refresh. You should implement a notification system to:

1. Display a prompt in the UI when a user logs in
2. Send email notifications to users when their connections need a quarterly refresh
3. Add an indicator next to connection status in the UI

## Other Plaid-Related Commands

This directory may include other commands related to Plaid integration, such as:

- Commands to manually sync data for testing
- Database cleanup utilities
- Diagnostic tools for Plaid connections 
XXD-VPN token generator (PC only)
1. Install Python 3 (python.org). 2. Run:  python xxd_token_tool.py   (first run creates xxd_admin_config.json)
3. Fill domain, admin_path (Settings > Very Advanced Settings > Proxy Path for Admins) and admin_uuid (the admin ID in your admin link).
   Hiddify advises a SEPARATE admin (agent) just for the API key.
4. Check create_endpoint in your panel's API docs: https://YOUR_DOMAIN/ADMIN_PATH/api/docs (default: api/v2/admin/user/).
5. Test first with:  python xxd_token_tool.py --dry-run   (sends nothing)
Weekly: python xxd_token_tool.py --expiring 3   (reminders)   |   python xxd_token_tool.py --renewed   (record a renewal)
The tool sends only: name, usage_limit_GB, package_days, mode. NEVER share xxd_admin_config.json (admin key). Customers go to customers.csv.

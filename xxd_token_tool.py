#!/usr/bin/env python3
"""XXD-VPN token generator (for MY PC only - it holds the admin key, never put it in the app).

1) Fill xxd_admin_config.json (created on first run).
2) python xxd_token_tool.py           -> asks name / phone / HWID / days / GB, creates the user in
                                         Hiddify Manager and prints the token (the user's UUID) + a WhatsApp message.
   python xxd_token_tool.py --dry-run -> same, but nothing is sent to the panel (to test).
   python xxd_token_tool.py --expiring [3]  -> who expires within N days + WhatsApp reminder links.
   python xxd_token_tool.py --renewed       -> record a renewal (after you renewed the customer in the panel).
Every customer is also saved in customers.csv (name, phone, HWID, UUID, dates).
Only the Python standard library is used."""
import csv, json, os, sys, uuid, urllib.parse, urllib.request, urllib.error, webbrowser, ssl
from datetime import date, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(HERE, 'xxd_admin_config.json')
DEFAULT = {
    "domain": "xxdvpn.duckdns.org",
    "admin_path": "ADMIN_PROXY_PATH",
    "admin_uuid": "ADMIN_UUID",
    "create_endpoint": "api/v2/admin/user/",
    "customers_csv": "customers.csv",
    "token_prefix": "",
    "message": "Bonjour {name}, voici votre jeton XXD-VPN :\n{token}\nAjoutez un profil dans l'application et collez-le. Valable {days} jours.",
}

def load():
    if not os.path.exists(CONFIG):
        json.dump(DEFAULT, open(CONFIG, 'w', encoding='utf-8'), indent=2, ensure_ascii=False)
        print(f'Created {CONFIG}. Fill it (domain, admin_path, admin_uuid) and run again.'); sys.exit(0)
    cfg = {**DEFAULT, **json.load(open(CONFIG, encoding='utf-8'))}
    return cfg

def ask(label, default=None):
    v = input(f'{label}' + (f' [{default}]' if default not in (None, '') else '') + ': ').strip()
    return v or (default or '')

def create_user(cfg, body, dry):
    url = f"https://{cfg['domain']}/{cfg['admin_path'].strip('/')}/{cfg['create_endpoint'].lstrip('/')}"
    if dry:
        print(f'[dry-run] would POST {url}\n{json.dumps(body, indent=2)}'); return str(uuid.uuid4())
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method='POST', headers={
        'Content-Type': 'application/json', 'Accept': 'application/json', 'Hiddify-API-Key': cfg['admin_uuid']})
    try:
        with urllib.request.urlopen(req, timeout=20, context=ssl.create_default_context()) as r:
            raw = r.read().decode() or '{}'
            print('Panel answered', r.status)
    except urllib.error.HTTPError as e:
        sys.exit(f'Panel refused: HTTP {e.code} {e.read().decode()[:300]}\n-> check admin_path, admin_uuid and create_endpoint (Admin Panel > Settings > API).')
    except Exception as e:
        sys.exit(f'Could not reach the panel: {e}')
    try:
        data = json.loads(raw)
        if isinstance(data, dict) and data.get('uuid'): return data['uuid']
    except Exception:
        pass
    sys.exit('The panel answered, but without a user uuid. Check the API docs of your panel (https://<domain>/<admin path>/api/docs).')

def read_customers(cfg):
    path = os.path.join(HERE, cfg['customers_csv'])
    if not os.path.exists(path): sys.exit('No customers.csv yet.')
    last = {}
    for r in csv.DictReader(open(path, encoding='utf-8')):
        last[r['uuid']] = r           # a later row (renewal) replaces the earlier one
    return path, list(last.values())

def expiring(cfg):
    """python xxd_token_tool.py --expiring [days]  -> customers whose plan ends within N days (default 3)"""
    n = int(sys.argv[sys.argv.index('--expiring') + 1]) if len(sys.argv) > sys.argv.index('--expiring') + 1 else 3
    path, rows = read_customers(cfg); today = date.today(); found = 0
    for r in sorted(rows, key=lambda r: date.fromisoformat(r['date']) + timedelta(days=int(float(r['days'])))):
        end = date.fromisoformat(r['date']) + timedelta(days=int(float(r['days']))); left = (end - today).days
        if left > n: continue
        found += 1
        state = f'EXPIRED {-left} day(s) ago' if left < 0 else f'ends in {left} day(s)'
        print(f"- {r['name']} ({r['phone']}): {state} [{end}]")
        if r['phone'].strip():
            msg = f"Bonjour {r['name']}, votre forfait XXD-VPN {'a expiré' if left < 0 else 'expire le ' + str(end)}. Voulez-vous le renouveler ?"
            print('  https://wa.me/' + ''.join(c for c in r['phone'] if c.isdigit()) + '?text=' + urllib.parse.quote(msg))
    if not found: print(f'Nobody expires within {n} day(s).')

def renewed(cfg):
    """python xxd_token_tool.py --renewed  -> after you renewed a customer in the panel, record it here"""
    path, rows = read_customers(cfg)
    who = ask('Customer name or UUID').lower()
    hit = [r for r in rows if who in (r['name'].lower(), r['uuid'].lower())]
    if len(hit) != 1: sys.exit(f'Found {len(hit)} customers for that name; use the UUID.')
    r = hit[0]; days = int(ask('New days', '30'))
    with open(path, 'a', newline='', encoding='utf-8') as f:
        csv.writer(f).writerow([date.today().isoformat(), r['name'], r['phone'], r['hwid'], r['uuid'], days, r['gb']])
    print(f"Recorded: {r['name']} renewed for {days} days from today.")

def main():
    dry = '--dry-run' in sys.argv
    cfg = load()
    if '--expiring' in sys.argv: return expiring(cfg)
    if '--renewed' in sys.argv: return renewed(cfg)
    name = ask('Customer name')
    phone = ask('Phone (digits, with country code, optional)')
    hwid = ask('HWID sent by the customer')
    days = int(ask('Days', '30'))
    gb = float(ask('Data limit in GB (large number = unlimited)', '100'))
    mode = ask('Reset mode (no_reset/daily/weekly/monthly)', 'no_reset')
    # only the fields documented by Hiddify Manager (API v2): name, usage_limit_GB, package_days, mode
    body = {'name': name, 'usage_limit_GB': gb, 'package_days': days, 'mode': mode}
    uid = create_user(cfg, body, dry)
    token = cfg['token_prefix'] + uid
    path = os.path.join(HERE, cfg['customers_csv']); new = not os.path.exists(path)
    with open(path, 'a', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        if new: w.writerow(['date', 'name', 'phone', 'hwid', 'uuid', 'days', 'gb'])
        w.writerow([date.today().isoformat(), name, phone, hwid, uid, days, gb])
    msg = cfg['message'].format(name=name, token=token, days=days)
    print('\n=== TOKEN ===\n' + token + '\n\n=== MESSAGE ===\n' + msg + f'\n\nSaved in {path}')
    if phone.strip():
        link = f"https://wa.me/{''.join(c for c in phone if c.isdigit())}?text={urllib.parse.quote(msg)}"
        print('\nWhatsApp link:\n' + link)
        try:
            if input('\nOpen WhatsApp now? (y/N): ').lower() == 'y': webbrowser.open(link)
        except EOFError:
            pass

if __name__ == '__main__':
    main()

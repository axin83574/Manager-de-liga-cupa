"""Replace the app_users and app_leagues data from a local liga_baza.json.

Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in .streamlit/secrets.toml.
The legacy public.ligi table is not modified.
"""
from __future__ import annotations
import datetime as dt
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path


def read_settings(project_dir: Path):
    url = os.environ.get("SUPABASE_URL", "").strip()
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    secrets_file = project_dir / ".streamlit" / "secrets.toml"
    if secrets_file.exists() and (not url or not key):
        text = secrets_file.read_text(encoding="utf-8-sig")
        values = dict(re.findall(
            r'^\s*(SUPABASE_URL|SUPABASE_SERVICE_ROLE_KEY)\s*=\s*["\']([^"\']*)["\']',
            text, re.MULTILINE))
        url = url or values.get("SUPABASE_URL", "")
        key = key or values.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key or "..." in url or "..." in key:
        raise RuntimeError(
            "Completează SUPABASE_URL și SUPABASE_SERVICE_ROLE_KEY în "
            f"{secrets_file}. Nu trimite cheia în chat.")
    return url.rstrip("/"), key


def request_json(url, key, method="GET", body=None):
    payload = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    headers = {"apikey": key, "Authorization": f"Bearer {key}", "Accept": "application/json"}
    if payload is not None:
        headers.update({"Content-Type": "application/json", "Prefer": "return=minimal"})
    req = urllib.request.Request(url, data=payload, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=45) as response:
            raw = response.read()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:600]
        raise RuntimeError(f"Supabase HTTP {exc.code}: {detail}") from exc


def table_url(base, table, query=None):
    suffix = "?" + urllib.parse.urlencode(query) if query else ""
    return f"{base}/rest/v1/{table}{suffix}"


def main():
    if len(sys.argv) != 2:
        raise RuntimeError('Utilizare: python migrate_liga_baza_to_supabase.py "C:\\cale\\liga_baza.json"')
    source = Path(sys.argv[1]).expanduser().resolve()
    if not source.is_file():
        raise RuntimeError(f"Nu găsesc fișierul: {source}")
    payload = json.loads(source.read_text(encoding="utf-8-sig"))
    users = payload.get("utilizatori")
    league_groups = payload.get("ligi")
    if not isinstance(users, dict) or not isinstance(league_groups, dict) or not users:
        raise RuntimeError("JSON-ul trebuie să conțină conturi și ligi în câmpurile utilizatori/ligi.")

    user_rows = [{"username": username, "data": record}
                 for username, record in users.items()]
    league_rows = []
    for owner, files in league_groups.items():
        if owner not in users or not isinstance(files, dict):
            raise RuntimeError(f"Liga proprietarului {owner!r} nu are un cont asociat.")
        for filename, record in files.items():
            data = record.get("data") if isinstance(record, dict) else None
            if not isinstance(data, dict) or not isinstance(data.get("echipe"), dict):
                raise RuntimeError(f"Date incomplete pentru liga {filename!r} a contului {owner!r}.")
            league_rows.append({"id": str(uuid.uuid4()), "owner_username": owner,
                                "nume": data.get("nume_liga") or Path(filename).stem,
                                "data": data})
    if not league_rows:
        raise RuntimeError("Nu există ligi de importat.")

    base, key = read_settings(Path(__file__).resolve().parent)
    old_users = request_json(table_url(base, "app_users", {"select": "username,data,updated_at"}), key) or []
    old_leagues = request_json(table_url(base, "app_leagues", {"select": "id,owner_username,nume,data,updated_at"}), key) or []
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = source.with_name(f"{source.stem}_supabase_backup_{stamp}.json")
    backup.write_text(json.dumps({"app_users": old_users, "app_leagues": old_leagues},
                                 ensure_ascii=False, indent=2), encoding="utf-8")

    try:
        request_json(table_url(base, "app_leagues", {"id": "not.is.null"}), key, "DELETE")
        request_json(table_url(base, "app_users", {"username": "not.is.null"}), key, "DELETE")
        request_json(table_url(base, "app_users"), key, "POST", user_rows)
        request_json(table_url(base, "app_leagues"), key, "POST", league_rows)
    except Exception:
        try:
            request_json(table_url(base, "app_leagues", {"id": "not.is.null"}), key, "DELETE")
            request_json(table_url(base, "app_users", {"username": "not.is.null"}), key, "DELETE")
            if old_users:
                request_json(table_url(base, "app_users"), key, "POST", old_users)
            if old_leagues:
                request_json(table_url(base, "app_leagues"), key, "POST", old_leagues)
        except Exception as restore_error:
            print(f"Nu am putut restaura automat datele vechi: {restore_error}", file=sys.stderr)
            print(f"Copia de siguranță este aici: {backup}", file=sys.stderr)
        raise

    print(f"Import reușit: {len(user_rows)} conturi și {len(league_rows)} ligi.")
    print(f"Copie de siguranță a bazei Supabase: {backup}")
    print("Sesiunea activă din JSON a fost omisă; utilizatorii se conectează cu conturile importate.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Import oprit: {exc}", file=sys.stderr)
        raise SystemExit(1)

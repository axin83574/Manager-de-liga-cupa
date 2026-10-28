"""Manager de ligă Streamlit, cu stocare Supabase și fallback local pentru dezvoltare."""
from __future__ import annotations

import copy
import datetime as dt
import hashlib
import hmac
import html
import json
import os
import re
import secrets
import shutil
import uuid
from pathlib import Path

import streamlit as st
import extra_streamlit_components as stx
from supabase import create_client


STATS_ECHIPA = {"meciuri_jucate": 0, "goluri_marcate": 0,
                "goluri_primite": 0, "puncte": 0}
STATS_JUCATOR = {"goluri": 0, "asisturi": 0,
                 "cartonase_galbene": 0, "cartonase_rosii": 0}
TIPURI_GOL = ("Gol Normal", "Gol din Lovitură Liberă", "Penalty")
TIPURI_EVENIMENT = TIPURI_GOL + ("Autogol", "Penalty Ratat",
                                 "Cartonaș Galben", "Cartonaș Roșu")
BASE_DIR = Path(os.environ.get("LIGA_DATA_DIR", Path(__file__).resolve().parent / "ligi"))
APP_DIR = Path(__file__).resolve().parent
USERS_FILE = Path(os.environ.get("LIGA_USERS_FILE", APP_DIR / "utilizatori.json"))
PASSWORD_ITERATIONS = 200_000
RESERVED_USERNAMES = {"con", "prn", "aux", "nul", "admin"} | \
    {f"com{i}" for i in range(1, 10)} | {f"lpt{i}" for i in range(1, 10)}
REMEMBER_COOKIE = "liga_remember_me"
REMEMBER_DAYS = 30


def _supabase_settings():
    try:
        return (str(st.secrets.get("SUPABASE_URL", "")).strip(),
                str(st.secrets.get("SUPABASE_SERVICE_ROLE_KEY", "")).strip())
    except Exception:
        return "", ""


SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY = _supabase_settings()
SUPABASE_ENABLED = bool(SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY)


@st.cache_resource
def supabase_client():
    if not SUPABASE_ENABLED:
        return None
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


def db_league_path(owner, league_id):
    return BASE_DIR / str(owner) / f"{league_id}.json"


def is_db_league_path(path):
    if not SUPABASE_ENABLED:
        return False
    try:
        uuid.UUID(Path(path).stem)
        return True
    except (ValueError, TypeError, AttributeError):
        return False


def db_league_id(path):
    return Path(path).stem


def all_db_league_rows():
    return supabase_client().table("app_leagues").select(
        "id,owner_username,nume,data,updated_at").execute().data or []


def normalizeaza_date(data):
    data.setdefault("nume_liga", "Liga mea")
    for key, default in (("echipe", {}), ("istoric_meciuri", []), ("program", []),
                         ("transferuri", []), ("cupe", []), ("invitatii", []), ("sterse", []),
                         ("membri", []), ("selectii_membri", {}), ("premii_alese", {})):
        if not isinstance(data.get(key), type(default)):
            data[key] = copy.deepcopy(default)
    for team in data["echipe"].values():
        for key, value in STATS_ECHIPA.items():
            team.setdefault(key, value)
        team.setdefault("jucatori", {})
        for player, stats in list(team["jucatori"].items()):
            if not isinstance(stats, dict):
                stats = {}
                team["jucatori"][player] = stats
            for key, value in STATS_JUCATOR.items():
                stats.setdefault(key, value)
            stats.setdefault("pozitie", "")
    for match in data["istoric_meciuri"]:
        match.setdefault("id", uuid.uuid4().hex[:8])
        match.setdefault("etapa", None)
        match.setdefault("evenimente", [])
        match.setdefault("goluri_e1", 0)
        match.setdefault("goluri_e2", 0)
    for fixture in data["program"]:
        fixture.setdefault("id", uuid.uuid4().hex[:8])
        fixture.setdefault("meci_id", None)
    for cup in data["cupe"]:
        cup.setdefault("id", uuid.uuid4().hex[:8])
        cup.setdefault("nume", "Cupa")
        cup.setdefault("runde", [])
        cup.setdefault("status", "în desfășurare")
        cup.setdefault("castigatoare", None)
        for round_data in cup["runde"]:
            round_data.setdefault("nume", "Runda")
            for slot in round_data.get("meciuri", []):
                slot.setdefault("id", uuid.uuid4().hex[:8])
                slot.setdefault("e1", None)
                slot.setdefault("e2", None)
                slot.setdefault("meci", None)
                slot.setdefault("castigator", None)
                slot.setdefault("penalti", False)
    return data


def safe_slug(name):
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "liga"


def load_users():
    if SUPABASE_ENABLED:
        rows = supabase_client().table("app_users").select("username,data").execute().data or []
        return {str(row["username"]).strip().casefold(): row.get("data") or {}
                for row in rows if row.get("username")}
    if not USERS_FILE.exists():
        return {}
    try:
        payload = json.loads(USERS_FILE.read_text(encoding="utf-8"))
        users = payload.get("utilizatori", {}) if isinstance(payload, dict) else {}
        return {str(username).strip().casefold(): record
                for username, record in users.items() if username}
    except (OSError, json.JSONDecodeError):
        return {}


def save_users(users):
    if SUPABASE_ENABLED:
        table = supabase_client().table("app_users")
        # `users` is a snapshot read earlier in this request. Deleting rows that
        # are absent from it can erase accounts created by another session.
        # Account removal is not part of this flow, so only upsert supplied rows.
        if users:
            table.upsert([{"username": username, "data": record}
                          for username, record in users.items()], on_conflict="username").execute()
        return
    temp = USERS_FILE.with_suffix(".json.tmp")
    USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    temp.write_text(json.dumps({"utilizatori": users}, ensure_ascii=False, indent=2), encoding="utf-8")
    if USERS_FILE.exists():
        shutil.copy2(USERS_FILE, USERS_FILE.with_suffix(".json.bak"))
    os.replace(temp, USERS_FILE)


def cookie_is_secure():
    try:
        forwarded = st.context.headers.get("X-Forwarded-Proto", "")
        return "https" in str(forwarded).casefold()
    except Exception:
        return False


def browser_cookie(cookie_manager, name):
    value = cookie_manager.get(name)
    if value is not None:
        return value
    try:
        return st.context.cookies.get(name)
    except Exception:
        return None


def delete_browser_cookie(cookie_manager, name, key_prefix):
    value = browser_cookie(cookie_manager, name)
    if value is None:
        return
    # CookieManager.delete removes the value from its local map before sending
    # the delete request to the browser; seed it if the request cookie loaded first.
    cookies = getattr(cookie_manager, "cookies", None)
    if isinstance(cookies, dict):
        cookies[name] = value
    cookie_manager.delete(name, key=f"{key_prefix}_{uuid.uuid4().hex}")


def remember_account(cookie_manager, username):
    users = load_users()
    record = users.get(username)
    if not record:
        return
    now = int(dt.datetime.now().timestamp())
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    sessions = record.setdefault("remember_tokens", {})
    if not isinstance(sessions, dict):
        sessions = record["remember_tokens"] = {}
    sessions = {key: expiry for key, expiry in sessions.items()
                if isinstance(expiry, (int, float)) and expiry > now}
    sessions[token_hash] = now + REMEMBER_DAYS * 24 * 60 * 60
    while len(sessions) > 10:
        oldest = min(sessions, key=sessions.get)
        sessions.pop(oldest, None)
    record["remember_tokens"] = sessions
    save_users(users)
    cookie_manager.set(REMEMBER_COOKIE, f"{username}.{raw_token}",
        key=f"remember_login_{uuid.uuid4().hex}", path="/",
        expires_at=dt.datetime.now() + dt.timedelta(days=REMEMBER_DAYS),
        max_age=REMEMBER_DAYS * 24 * 60 * 60, secure=cookie_is_secure(), same_site="strict")
    st.session_state["pending_remember_login"] = {
        "username": username, "token_hash": token_hash}


def revoke_remembered_account(cookie_manager):
    username = st.session_state.pop("remembered_username", None)
    token_hash = st.session_state.pop("remembered_token_hash", None)
    if username and token_hash:
        users = load_users()
        record = users.get(username, {})
        sessions = record.get("remember_tokens", {})
        if token_hash in sessions:
            sessions.pop(token_hash, None)
            save_users(users)
    delete_browser_cookie(cookie_manager, REMEMBER_COOKIE, "forget_login")


def restore_remembered_account(cookie_manager):
    value = browser_cookie(cookie_manager, REMEMBER_COOKIE)
    if not value:
        return
    try:
        username, raw_token = str(value).split(".", 1)
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        record = load_users().get(username, {})
        expiry = record.get("remember_tokens", {}).get(token_hash)
        if expiry and float(expiry) > dt.datetime.now().timestamp():
            st.session_state["user_key"] = username
            st.session_state["remembered_username"] = username
            st.session_state["remembered_token_hash"] = token_hash
            return
    except (ValueError, TypeError, AttributeError):
        pass
    delete_browser_cookie(cookie_manager, REMEMBER_COOKIE, "clear_invalid_login")


def finish_pending_remember_login(cookie_manager):
    pending = st.session_state.get("pending_remember_login")
    if not pending:
        return False
    value = browser_cookie(cookie_manager, REMEMBER_COOKIE)
    try:
        username, raw_token = str(value).split(".", 1)
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    except (AttributeError, ValueError):
        return False
    if username != pending.get("username") or not hmac.compare_digest(
            token_hash, str(pending.get("token_hash", ""))):
        return False
    st.session_state["user_key"] = username
    st.session_state["remembered_username"] = username
    st.session_state["remembered_token_hash"] = token_hash
    st.session_state.pop("pending_remember_login", None)
    return True


def password_hash(password, salt=None, iterations=PASSWORD_ITERATIONS):
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return salt.hex(), digest.hex()


def verify_password(record, password):
    try:
        _, digest = password_hash(password, bytes.fromhex(record["sare"]),
                                  int(record.get("iteratii", PASSWORD_ITERATIONS)))
        return hmac.compare_digest(digest, record["hash"])
    except (KeyError, ValueError, TypeError):
        return False


def create_account(username, email, password, name, birthday, plays_professional, position):
    username = username.strip()
    normalized_username = username.lower()
    normalized_email = email.strip().casefold()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{2,23}", username):
        raise ValueError("Utilizatorul trebuie să aibă 3–24 caractere și să conțină litere, cifre, _ sau -.")
    if normalized_username in RESERVED_USERNAMES:
        raise ValueError("Acest nume de utilizator este rezervat.")
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", normalized_email):
        raise ValueError("Introdu o adresă de e-mail validă.")
    if len(password) < 6:
        raise ValueError("Parola trebuie să aibă cel puțin 6 caractere.")
    if not name.strip():
        raise ValueError("Introdu numele și prenumele.")
    if birthday > dt.date.today():
        raise ValueError("Data nașterii nu poate fi în viitor.")
    if plays_professional not in ("Da", "Nu"):
        raise ValueError("Alege dacă joci la un club profesionist.")
    if position not in ("Portar", "Fundaș", "Mijlocaș", "Atacant"):
        raise ValueError("Alege poziția ta în teren.")
    users = load_users()
    if normalized_username in users:
        raise ValueError("Există deja un cont cu acest nume de utilizator.")
    if any(str(record.get("email", "")).strip().casefold() == normalized_email
           for record in users.values()):
        raise ValueError("Există deja un cont cu această adresă de e-mail.")
    salt, digest = password_hash(password)
    users[normalized_username] = {"nume": name.strip(), "email": normalized_email,
        "data_nasterii": birthday.strftime("%d.%m.%Y"),
        "joaca_fotbal": plays_professional, "pozitie": position, "sare": salt, "hash": digest,
        "iteratii": PASSWORD_ITERATIONS, "dispozitive": [], "selectii_ligi": {},
        "creat": dt.date.today().strftime("%d.%m.%Y")}
    save_users(users)
    return normalized_username


def get_user_leagues(username):
    if SUPABASE_ENABLED:
        entries = []
        for row in all_db_league_rows():
            owner = row.get("owner_username", "")
            data = row.get("data") or {}
            role = "owner" if owner.casefold() == username.casefold() else None
            if role is None:
                member = next((m for m in data.get("membri", [])
                               if str(m.get("username", "")).casefold() == username.casefold()
                               and m.get("activ", True)), None)
                if member:
                    role = member.get("rol", "vizitator")
            if role:
                entries.append({"path": db_league_path(owner, row["id"]), "role": role,
                                "owner": owner, "updated_at": row.get("updated_at", "")})
        return sorted(entries, key=lambda entry: entry.get("updated_at", ""), reverse=True)
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    entries = []
    own_dir = BASE_DIR / username
    own_dir.mkdir(parents=True, exist_ok=True)
    for path in own_dir.glob("*.json"):
        entries.append({"path": path, "role": "owner", "owner": username})
    for folder in BASE_DIR.iterdir():
        if not folder.is_dir() or folder.name.startswith("_") or folder.name.casefold() == username.casefold():
            continue
        for path in folder.glob("*.json"):
            try:
                data = load_league(path)
            except ValueError:
                continue
            access = next((m for m in data.get("membri", [])
                           if str(m.get("username", "")).casefold() == username.casefold()), None)
            if access and access.get("activ", True):
                entries.append({"path": path, "role": access.get("rol", "vizitator"), "owner": folder.name})
    return sorted(entries, key=lambda entry: entry["path"].stat().st_mtime, reverse=True)


def league_key(entry):
    return f"{entry['owner']}/{entry['path'].name}"


def find_invitation(token):
    if not token:
        return None
    if SUPABASE_ENABLED:
        for row in all_db_league_rows():
            path, owner = db_league_path(row["owner_username"], row["id"]), row["owner_username"]
            data = normalizeaza_date(row.get("data") or {})
            for invite in data.get("invitatii", []):
                if invite.get("activ", True) and hmac.compare_digest(
                        str(invite.get("token", "")), str(token)):
                    role = "vizitator" if invite.get("tip", "spectator") == "spectator" else invite.get("rol", "vizitator")
                    return {"path": path, "owner": owner, "role": role,
                            "invitation": invite, "data": data, "access_method": "legacy"}
        return None
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    for folder in BASE_DIR.iterdir():
        if not folder.is_dir() or folder.name.startswith("_"):
            continue
        for path in folder.glob("*.json"):
            try:
                data = load_league(path)
            except ValueError:
                continue
            for invite in data.get("invitatii", []):
                if (invite.get("activ", True)
                        and hmac.compare_digest(str(invite.get("token", "")), str(token))):
                    role = "vizitator" if invite.get("tip", "spectator") == "spectator" else invite.get("rol", "vizitator")
                    return {"path": path, "owner": folder.name, "role": role,
                            "invitation": invite, "data": data, "access_method": "legacy"}
    return None


def normalize_access_code(code):
    return "".join(char for char in str(code or "").upper() if char.isalnum())


def new_access_code():
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    raw = "".join(secrets.choice(alphabet) for _ in range(12))
    return "-".join(raw[index:index + 4] for index in range(0, 12, 4))


def new_league_access_codes():
    return {"spectator": new_access_code(), "editor": new_access_code()}


def find_access_code(code):
    normalized = normalize_access_code(code)
    if len(normalized) != 12:
        return None
    if SUPABASE_ENABLED:
        for row in all_db_league_rows():
            path, owner = db_league_path(row["owner_username"], row["id"]), row["owner_username"]
            data = normalizeaza_date(row.get("data") or {})
            codes = data.get("coduri_invitat", {})
            if not isinstance(codes, dict):
                continue
            for code_type, role in (("spectator", "vizitator"), ("editor", "editor")):
                existing = normalize_access_code(codes.get(code_type, ""))
                if existing and hmac.compare_digest(existing, normalized):
                    return {"path": path, "owner": owner, "role": role,
                            "code_type": code_type, "code": codes[code_type], "data": data,
                            "access_method": "cod"}
        return None
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    for folder in BASE_DIR.iterdir():
        if not folder.is_dir() or folder.name.startswith("_"):
            continue
        for path in folder.glob("*.json"):
            try:
                data = load_league(path)
            except ValueError:
                continue
            codes = data.get("coduri_invitat", {})
            if not isinstance(codes, dict):
                continue
            for code_type, role in (("spectator", "vizitator"), ("editor", "editor")):
                existing = normalize_access_code(codes.get(code_type, ""))
                if existing and hmac.compare_digest(existing, normalized):
                    return {"path": path, "owner": folder.name, "role": role,
                            "code_type": code_type, "code": codes[code_type], "data": data,
                            "access_method": "cod"}
    return None


def save_guest_selection(path, invitation, team, player):
    fresh = load_league(path)
    active = next((item for item in fresh.get("invitatii", [])
                   if item.get("id") == invitation.get("id")
                   and hmac.compare_digest(str(item.get("token", "")), str(invitation.get("token", "")))
                   and item.get("activ", True)), None)
    if not active:
        raise ValueError("Invitația a fost revocată.")
    if team not in fresh.get("echipe", {}) or player not in fresh["echipe"][team].get("jucatori", {}):
        raise ValueError("Alege un jucător care există în lot.")
    fresh.setdefault("selectii_membri", {})[invitation["id"]] = {
        "nume": invitation.get("nume", "Invitat"), "tip": invitation.get("tip", "spectator"),
        "echipa": team, "jucator": player, "actualizat": dt.datetime.now().timestamp()}
    _store_league(path, fresh)


def join_league_with_code(entry, username, access_code, member_choice=None):
    fresh = load_league(entry["path"])
    codes = fresh.get("coduri_invitat", {})
    if not isinstance(codes, dict):
        codes = {}
    code_type = entry["code_type"]
    active_code = normalize_access_code(codes.get(code_type, ""))
    if not active_code or not hmac.compare_digest(active_code, normalize_access_code(access_code)):
        raise ValueError("Codul a fost schimbat. Cere proprietarului codul nou.")
    role = "editor" if code_type == "editor" else "vizitator"
    choice = member_choice if code_type == "spectator" else None
    member_type = "jucator" if choice and choice.get("kind") == "jucator" else "spectator"
    users_to_save = None
    if entry["owner"].casefold() != username.casefold():
        fresh.setdefault("membri", [])
        membership = next((item for item in fresh["membri"]
                           if str(item.get("username", "")).casefold() == username.casefold()), None)
        values = {"username": username, "rol": role, "tip": member_type, "activ": True,
                  "creat": dt.datetime.now().strftime("%d.%m.%Y %H:%M"), "sursa": "cod"}
        if membership is None:
            fresh["membri"].append(values)
        else:
            membership.update(values)
        if choice and choice.get("kind") == "jucator":
            team, player = choice.get("team"), choice.get("player")
            if team not in fresh.get("echipe", {}) or player not in fresh["echipe"][team].get("jucatori", {}):
                raise ValueError("Jucătorul ales nu mai există în lot. Alege din nou.")
            selection = {"echipa": team, "jucator": player, "tip": "jucator",
                         "actualizat": dt.datetime.now().timestamp()}
            fresh.setdefault("selectii_membri", {})[username] = selection
            users = load_users()
            if username in users:
                users[username].setdefault("selectii_ligi", {})[league_key(entry)] = {
                    **selection, "pozitie": users[username].get("pozitie", "")}
                users_to_save = users
        _store_league(entry["path"], fresh)
        # Save the league membership/selection first. If account-profile
        # synchronization fails, the player can still enter and the choice
        # remains available from the league data.
        if users_to_save is not None:
            try:
                save_users(users_to_save)
                st.session_state.pop("player_profile_sync_error", None)
            except Exception as exc:
                st.session_state["player_profile_sync_error"] = str(exc)
    return role if entry["owner"].casefold() != username.casefold() else "owner"


def spectator_entry_gate(entry):
    code = entry["code"]
    key = league_key(entry)
    choice = st.session_state.get("spectator_profile", {})
    if choice.get("league") == key and choice.get("code") == code and choice.get("kind") in ("jucator", "spectator"):
        return choice
    if choice.get("league") != key or choice.get("code") != code:
        choice = {}
        st.session_state.pop("spectator_profile", None)
        st.session_state.pop("spectator_choice_stage", None)
        st.session_state.pop("spectator_team_choice", None)
        st.session_state.pop("spectator_player_choice", None)

    st.title("Înainte să intri în ligă")
    st.caption(f"Ai acces de spectator la „{entry['data'].get('nume_liga', 'Liga')}”. Alege cum vrei să apari.")
    if st.session_state.get("spectator_choice_stage") == "player":
        teams = list(entry["data"].get("echipe", {}))
        if not teams:
            st.info("Liga nu are încă echipe. Poți intra doar ca spectator.")
            if st.button("Intră ca spectator", type="primary"):
                choice = {"league": key, "code": code, "kind": "spectator"}
                st.session_state["spectator_profile"] = choice
                st.rerun()
        else:
            team = st.selectbox("Echipa ta", teams, key="spectator_team_choice")
            players = list(entry["data"]["echipe"][team].get("jucatori", {}))
            player = st.selectbox("Alege-ți jucătorul", players, key="spectator_player_choice") if players else None
            if not players:
                st.caption("Echipa aleasă nu are încă jucători în lot.")
            choose = st.button("Continuă ca jucător", type="primary", disabled=not bool(players))
            if choose and player:
                st.session_state["spectator_profile"] = {
                    "league": key, "code": code, "kind": "jucator", "team": team, "player": player}
                st.session_state.pop("spectator_choice_stage", None)
                st.rerun()
        if st.button("Înapoi", key="spectator_choice_back"):
            st.session_state.pop("spectator_choice_stage", None)
            st.rerun()
        return None

    player_col, spectator_col = st.columns(2, gap="large")
    with player_col:
        with st.container(border=True):
            st.markdown("### ⚽ Sunt jucător în ligă")
            st.caption("Îți alegi numele din lot, iar statisticile lui apar în profilul tău.")
            if st.button("Alege-mi jucătorul", type="primary", key="choose_guest_player"):
                st.session_state["spectator_choice_stage"] = "player"
                st.rerun()
    with spectator_col:
        with st.container(border=True):
            st.markdown("### 👁 Sunt doar spectator")
            st.caption("Vezi liga fără asociere cu un jucător.")
            if st.button("Intră ca spectator", key="choose_guest_spectator"):
                st.session_state["spectator_profile"] = {"league": key, "code": code, "kind": "spectator"}
                st.rerun()
    return None


def create_user_league(username, name, source_entry=None, league_type="Ligă"):
    if SUPABASE_ENABLED:
        path = db_league_path(username, uuid.uuid4())
        copied_teams = {}
        if source_entry:
            source_data = load_league(source_entry["path"])
            copied_teams = {
                team: {"jucatori": {player: dict(STATS_JUCATOR) for player in info.get("jucatori", {})},
                       **STATS_ECHIPA}
                for team, info in source_data.get("echipe", {}).items()
            }
        created_data = {"nume_liga": name.strip() or "Liga mea", "echipe": copied_teams,
                        "istoric_meciuri": [], "program": [], "transferuri": [], "cupe": [], "membri": [],
                        "coduri_invitat": new_league_access_codes()}
        if league_type in ("Ligă + cupă", "Cupă"):
            cup = make_cup(list(copied_teams), f"Cupa {created_data['nume_liga']}") if len(copied_teams) >= 2 else {
                "id": uuid.uuid4().hex[:8], "nume": f"Cupa {created_data['nume_liga']}", "runde": [],
                "status": "în desfășurare", "castigatoare": None}
            created_data["cupe"].append(cup)
        save_league(path, created_data)
        return path
    user_folder = BASE_DIR / username
    user_folder.mkdir(parents=True, exist_ok=True)
    path = user_folder / f"{safe_slug(name)}.json"
    suffix = 2
    while path.exists():
        path = user_folder / f"{safe_slug(name)}-{suffix}.json"
        suffix += 1
    copied_teams = {}
    if source_entry:
        source_data = load_league(source_entry["path"])
        copied_teams = {
            team: {"jucatori": {player: dict(STATS_JUCATOR) for player in info.get("jucatori", {})},
                   **STATS_ECHIPA}
            for team, info in source_data.get("echipe", {}).items()
        }
    created_data = {"nume_liga": name.strip() or "Liga mea", "echipe": copied_teams,
                    "istoric_meciuri": [], "program": [], "transferuri": [], "cupe": [], "membri": [],
                    "coduri_invitat": new_league_access_codes()}
    if league_type in ("Ligă + cupă", "Cupă"):
        cup = make_cup(list(copied_teams), f"Cupa {created_data['nume_liga']}") if len(copied_teams) >= 2 else {
            "id": uuid.uuid4().hex[:8], "nume": f"Cupa {created_data['nume_liga']}", "runde": [],
            "status": "în desfășurare", "castigatoare": None}
        created_data["cupe"].append(cup)
    save_league(path, created_data)
    return path


def load_league(path):
    if is_db_league_path(path):
        try:
            result = (supabase_client().table("app_leagues").select("data")
                      .eq("id", db_league_id(path)).limit(1).execute().data or [])
            if not result:
                raise ValueError("Liga nu mai există în baza de date.")
            return normalizeaza_date(result[0].get("data") or {})
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError(f"Nu pot citi liga din Supabase: {exc}") from exc
    try:
        with path.open("r", encoding="utf-8") as handle:
            return normalizeaza_date(json.load(handle))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Nu pot citi fișierul ligii: {exc}") from exc


def _store_league(path, data):
    if is_db_league_path(path):
        payload = normalizeaza_date(data)
        supabase_client().table("app_leagues").upsert({
            "id": db_league_id(path), "owner_username": path.parent.name,
            "nume": payload.get("nume_liga", "Liga mea"), "data": payload,
            "updated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        }, on_conflict="id").execute()
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("w", encoding="utf-8") as handle:
        json.dump(normalizeaza_date(data), handle, ensure_ascii=False, indent=2)
    if path.exists():
        shutil.copy2(path, path.with_suffix(path.suffix + ".bak"))
    os.replace(temp, path)


def save_league(path, data):
    role = st.session_state.get("active_league_role")
    if role == "vizitator":
        st.error("Ai acces doar pentru vizualizare în această ligă.")
        st.stop()
    exists = path.exists()
    if is_db_league_path(path):
        exists = bool(supabase_client().table("app_leagues").select("id")
                      .eq("id", db_league_id(path)).limit(1).execute().data)
    if role == "editor" and exists:
        current = load_league(path)
        access = st.session_state.get("active_guest_access")
        if access and Path(access.get("path", "")) == path:
            current_codes = current.get("coduri_invitat", {})
            if not isinstance(current_codes, dict):
                current_codes = {}
            current_code = normalize_access_code(
                current_codes.get("editor", ""))
            if not current_code or not hmac.compare_digest(
                    current_code, normalize_access_code(access.get("code", ""))):
                st.error("Codul de editor a fost schimbat sau revocat.")
                st.stop()
        guest = st.session_state.get("active_guest_invite")
        if guest and Path(guest.get("path", "")) == path:
            active_invite = next((invite for invite in current.get("invitatii", [])
                if hmac.compare_digest(str(invite.get("token", "")), str(guest.get("token", "")))
                and invite.get("activ", True)), None)
            if not active_invite or active_invite.get("tip") == "spectator" or active_invite.get("rol") != "editor":
                st.error("Invitația nu mai permite modificarea ligii.")
                st.stop()
        # Editors can change league content but cannot grant themselves or others access.
        data["membri"] = current.get("membri", [])
        for key in ("invitatii", "selectii_membri", "coduri_invitat", "partajare", "partajare_adresa", "partajare_setari"):
            if key in current:
                data[key] = current[key]
    _store_league(path, data)


def build_match(home, away, events, round_no=None, walkover=None, reason=""):
    if walkover:
        goals_home, goals_away = (3, 0) if walkover == home else (0, 3)
        events = []
    else:
        goals_home = goals_away = 0
        for event in events:
            if event["tip"] in TIPURI_GOL:
                if event["echipa"] == home:
                    goals_home += 1
                else:
                    goals_away += 1
            elif event["tip"] == "Autogol":
                if event["echipa"] == home:
                    goals_away += 1
                else:
                    goals_home += 1
    stats = {}
    for event in events:
        team_stats = stats.setdefault(event["echipa"], {})
        player_stats = team_stats.setdefault(event["jucator"], dict(STATS_JUCATOR))
        if event["tip"] in TIPURI_GOL:
            player_stats["goluri"] += 1
            if event.get("asist"):
                team_stats.setdefault(event["asist"], dict(STATS_JUCATOR))["asisturi"] += 1
        elif event["tip"] == "Cartonaș Galben":
            player_stats["cartonase_galbene"] += 1
        elif event["tip"] == "Cartonaș Roșu":
            player_stats["cartonase_rosii"] += 1
    match = {"id": uuid.uuid4().hex[:8], "etapa": round_no,
             "modificat": int(dt.datetime.now().timestamp() * 1000),
             "e1": home, "e2": away, "goluri_e1": goals_home, "goluri_e2": goals_away,
             "mod_e1": stats.get(home, {}), "mod_e2": stats.get(away, {}),
             "evenimente": sorted(events, key=lambda e: e["minut"])}
    if walkover:
        match.update(masa_verde=walkover, motiv_mv=reason)
    return match


def render_match_event_entry(data, home, away, draft_id, initial_events=None):
    """Interactive event entry with a live score preview."""
    state_key = f"match_draft_{draft_id}"
    events = st.session_state.setdefault(state_key, copy.deepcopy(initial_events or []))
    next_key = f"{state_key}_next"
    entry_id = st.session_state.get(next_key, 0)
    st.markdown("#### Evenimentele meciului")
    st.caption("Adaugă fiecare gol sau cartonaș separat. Scorul se actualizează automat.")
    left, right = st.columns([1, 1])
    with left:
        minute = st.number_input("Minut", min_value=1, max_value=150, value=1,
                                 step=1, key=f"{state_key}_minute_{entry_id}")
        event_team = st.selectbox("Echipa", [home, away], key=f"{state_key}_team_{entry_id}")
        event_type = st.selectbox("Eveniment", TIPURI_EVENIMENT, key=f"{state_key}_type_{entry_id}")
    roster = list(data.get("echipe", {}).get(event_team, {}).get("jucatori", {}))
    team_token = hashlib.sha1(event_team.encode()).hexdigest()[:6]
    player_options = [*roster, "Alt jucător…"]
    player_choice = st.selectbox("Jucător", player_options, key=f"{state_key}_player_{team_token}_{entry_id}")
    player_name = (st.text_input("Numele jucătorului", key=f"{state_key}_player_manual_{team_token}_{entry_id}")
                   if player_choice == "Alt jucător…" else player_choice)
    assist = None
    if event_type in TIPURI_GOL:
        assist_options = ["Fără assist", *roster, "Alt jucător…"]
        assist_choice = st.selectbox("Assist (opțional)", assist_options,
                                     key=f"{state_key}_assist_{team_token}_{entry_id}")
        if assist_choice == "Alt jucător…":
            assist = st.text_input("Numele celui care a dat assist", key=f"{state_key}_assist_manual_{team_token}_{entry_id}").strip() or None
        elif assist_choice != "Fără assist":
            assist = assist_choice
    if st.button("＋ Adaugă eveniment", type="primary", key=f"{state_key}_add_{entry_id}"):
        player_name = player_name.strip()
        if not player_name:
            st.error("Alege sau scrie numele jucătorului.")
        elif assist and assist.casefold() == player_name.casefold():
            st.error("Marcatorul nu poate să-și dea assist lui însuși.")
        else:
            events.append({"echipa": event_team, "minut": int(minute), "tip": event_type,
                           "jucator": player_name, "asist": assist})
            st.session_state[next_key] = st.session_state.get(next_key, 0) + 1
            st.rerun()
    preview = build_match(home, away, events)
    st.markdown(f"### {home}  **{preview['goluri_e1']} – {preview['goluri_e2']}**  {away}")
    if events:
        st.markdown("**Evenimente adăugate**")
        for index, event in enumerate(list(events)):
            detail = f"{event['minut']}′ · {event['echipa']} · {event['tip']} · {event['jucator']}"
            if event.get("asist"):
                detail += f" (assist: {event['asist']})"
            c1, c2 = st.columns([8, 1])
            c1.write(detail)
            if c2.button("Șterge", key=f"{state_key}_delete_{index}"):
                events.pop(index)
                st.rerun()
    else:
        st.caption("Nu ai adăugat încă evenimente. Poți salva scorul 0–0.")
    return events


def round_title(match_count):
    return {1: "Finala", 2: "Semifinale", 4: "Sferturi", 8: "Optimi",
            16: "Șaisprezecimi"}.get(match_count, f"Runda cu {match_count} meciuri")


def make_cup(teams, name):
    shuffled = list(teams)
    import random
    random.shuffle(shuffled)
    bracket_size = 1
    while bracket_size < len(shuffled):
        bracket_size *= 2
    byes = bracket_size - len(shuffled)
    rounds, matches_count = [], bracket_size // 2
    while matches_count:
        rounds.append({"nume": round_title(matches_count), "meciuri": [
            {"id": uuid.uuid4().hex[:8], "e1": None, "e2": None,
             "meci": None, "castigator": None, "penalti": False}
            for _ in range(matches_count)]})
        matches_count //= 2
    cursor = 0
    for index, slot in enumerate(rounds[0]["meciuri"]):
        if index < byes:
            slot["e1"] = shuffled[cursor]
            cursor += 1
        else:
            slot["e1"], slot["e2"] = shuffled[cursor:cursor + 2]
            cursor += 2
    cup = {"id": uuid.uuid4().hex[:8], "nume": name, "echipe": list(teams),
           "creata": dt.date.today().strftime("%d.%m.%Y"), "runde": rounds,
           "status": "în desfășurare", "castigatoare": None}
    propagate_cup_byes(cup)
    return cup


def advance_cup_winner(cup, round_index, match_index):
    slot = cup["runde"][round_index]["meciuri"][match_index]
    if round_index + 1 == len(cup["runde"]):
        cup["castigatoare"] = slot["castigator"]
        cup["status"] = "terminată"
    else:
        next_slot = cup["runde"][round_index + 1]["meciuri"][match_index // 2]
        next_slot["e1" if match_index % 2 == 0 else "e2"] = slot["castigator"]


def participanti_supercupa(data, cup):
    cup_winner = cup.get("castigatoare")
    if not cup_winner:
        return None, None, "Cupa selectată nu are încă o câștigătoare."
    table = ranking(data)
    teams = [row["Echipă"] for row in table]
    if len(teams) < 2:
        return None, None, "Ai nevoie de cel puțin două echipe în clasament."
    champion = teams[0]
    return (cup_winner, champion, "campioana ligii") if cup_winner != champion else (
        cup_winner, teams[1], "locul 2 din ligă (dubla ligă + cupă)")


def make_supercup(name, team_a, team_b, source_cup_id=None):
    return {"id": uuid.uuid4().hex[:8], "nume": name, "super": True,
            "sursa_cupa": source_cup_id, "echipe": [team_a, team_b],
            "creata": dt.date.today().strftime("%d.%m.%Y"),
            "runde": [{"nume": "Finala", "meciuri": [{"id": uuid.uuid4().hex[:8],
                "e1": team_a, "e2": team_b, "meci": None,
                "castigator": None, "penalti": False}]}],
            "status": "în desfășurare", "castigatoare": None}


def definitii_premii(data):
    league_name = data.get("nume_liga") or "Liga"
    awards = [{"cheie": "campioana", "titlu": "🏆 Campioana ligii", "tip": "echipa",
               "trofeu": f"Campioană — {league_name}"}]
    for cup in data.get("cupe", []):
        awards.append({"cheie": f"cupa:{cup.get('id')}",
            "titlu": f"🏅 Câștigătoarea Supercupei — {cup.get('nume', 'Cupa')}" if cup.get("super")
                     else f"🏆 Câștigătoarea — {cup.get('nume', 'Cupa')}",
            "tip": "echipa", "trofeu": (f"Trofeul Supercupei — {cup.get('nume', 'Supercupa')}"
                if cup.get("super") else f"Câștigătoare {cup.get('nume', 'Cupa')}")})
    awards.append({"cheie": "gheata_liga", "titlu": "👟 Gheata de Aur — Ligă", "tip": "jucator", "trofeu": "Gheata de Aur — Ligă"})
    if any(not cup.get("super") for cup in data.get("cupe", [])):
        awards.append({"cheie": "gheata_cupa", "titlu": "👟 Gheata de Aur — Cupă", "tip": "jucator", "trofeu": "Gheata de Aur — Cupă"})
    awards.extend([
        {"cheie": "balon", "titlu": "🌟 Balonul de Aur", "tip": "jucator", "trofeu": "Balonul de Aur"},
        {"cheie": "yashin", "titlu": "🧤 Trofeul Yashin · portar", "tip": "jucator", "trofeu": "Trofeul Yashin", "poz": "port"},
        {"cheie": "kopa", "titlu": "⭐ Trofeul Kopa · tânăr", "tip": "jucator", "trofeu": "Trofeul Kopa"},
        {"cheie": "fundas", "titlu": "🛡 Cel mai bun fundaș", "tip": "jucator", "trofeu": "Cel mai bun fundaș", "poz": "fund"},
        {"cheie": "mijlocas", "titlu": "🧠 Cel mai bun mijlocaș", "tip": "jucator", "trofeu": "Cel mai bun mijlocaș", "poz": "mijloc"},
        {"cheie": "atacant", "titlu": "⚽ Cel mai bun atacant", "tip": "jucator", "trofeu": "Cel mai bun atacant", "poz": "atac"},
    ])
    return awards


def trofee_echipa(data, team):
    chosen = data.get("premii_alese", {})
    return [award["trofeu"] for award in definitii_premii(data)
            if award["tip"] == "echipa" and (chosen.get(award["cheie"]) or {}).get("echipa") == team]


def trofee_jucator(data, team, player):
    chosen = data.get("premii_alese", {})
    return [award["trofeu"] for award in definitii_premii(data)
            if award["tip"] == "jucator" and
            (chosen.get(award["cheie"]) or {}).get("echipa") == team and
            (chosen.get(award["cheie"]) or {}).get("jucator") == player]


def propagate_cup_byes(cup):
    if not cup.get("runde"):
        return
    for index, slot in enumerate(cup["runde"][0]["meciuri"]):
        if slot.get("meci") is None and bool(slot.get("e1")) != bool(slot.get("e2")):
            slot["castigator"] = slot.get("e1") or slot.get("e2")
            advance_cup_winner(cup, 0, index)


def clear_cup_result(cup, round_index, match_index):
    removed = []
    while True:
        slot = cup["runde"][round_index]["meciuri"][match_index]
        if slot.get("meci"):
            removed.append(slot["meci"])
        slot["meci"], slot["castigator"], slot["penalti"] = None, None, False
        if round_index + 1 >= len(cup["runde"]):
            break
        next_slot = cup["runde"][round_index + 1]["meciuri"][match_index // 2]
        next_slot["e1" if match_index % 2 == 0 else "e2"] = None
        if next_slot.get("meci") is None:
            break
        round_index, match_index = round_index + 1, match_index // 2
    cup["castigatoare"] = None
    cup["status"] = "în desfășurare"
    return removed


def apply_player_stats(data, team_name, player_stats, sign=1):
    """Apply player stats while keeping a transferred player's history with them."""
    for player, values in player_stats.items():
        team, name = team_name, player
        visited = {team}
        while True:
            transfer = next((t for t in reversed(data.get("transferuri", []))
                             if t.get("de_la") == team and t.get("jucator", "").casefold() == name.casefold()), None)
            if not transfer or transfer.get("la") in visited:
                break
            team, name = transfer["la"], transfer.get("nume_nou", player)
            visited.add(team)
        if team not in data["echipe"]:
            continue
        target = data["echipe"][team]["jucatori"].setdefault(name, dict(STATS_JUCATOR))
        for key in STATS_JUCATOR:
            target[key] = max(0, target.get(key, 0) + sign * values.get(key, 0))


def transfer_player(data, player, source, destination, new_name=None):
    if source == destination:
        raise ValueError("Alege două echipe diferite.")
    source_roster = data["echipe"][source]["jucatori"]
    destination_roster = data["echipe"][destination]["jucatori"]
    if player not in source_roster:
        raise ValueError("Jucătorul nu mai este în lotul sursă.")
    final_name = (new_name or player).strip()
    if not final_name:
        final_name = player
    if final_name in destination_roster:
        raise ValueError(f"{destination} are deja un jucător numit «{final_name}».")
    destination_roster[final_name] = source_roster.pop(player)
    data["transferuri"].append({"jucator": player, "nume_nou": final_name,
        "de_la": source, "la": destination, "data": dt.date.today().strftime("%d.%m.%Y")})
    for chosen in data.get("premii_alese", {}).values():
        if chosen.get("echipa") == source and chosen.get("jucator") == player:
            chosen["echipa"], chosen["jucator"] = destination, final_name
    return final_name


def rename_team(data, old_name, new_name):
    new_name = new_name.strip()
    if not new_name or new_name == old_name:
        raise ValueError("Introdu un nume nou pentru echipă.")
    if new_name in data["echipe"]:
        raise ValueError("Există deja o echipă cu acest nume.")
    data["echipe"][new_name] = data["echipe"].pop(old_name)
    for match in data["istoric_meciuri"]:
        if match.get("e1") == old_name: match["e1"] = new_name
        if match.get("e2") == old_name: match["e2"] = new_name
        if match.get("masa_verde") == old_name: match["masa_verde"] = new_name
        for event in match.get("evenimente", []):
            if event.get("echipa") == old_name: event["echipa"] = new_name
    for fixture in data["program"]:
        if fixture.get("e1") == old_name: fixture["e1"] = new_name
        if fixture.get("e2") == old_name: fixture["e2"] = new_name
    for transfer in data.get("transferuri", []):
        if transfer.get("de_la") == old_name: transfer["de_la"] = new_name
        if transfer.get("la") == old_name: transfer["la"] = new_name
    for chosen in data.get("premii_alese", {}).values():
        if chosen.get("echipa") == old_name:
            chosen["echipa"] = new_name
    for cup in data.get("cupe", []):
        if cup.get("castigatoare") == old_name: cup["castigatoare"] = new_name
        cup["echipe"] = [new_name if team == old_name else team for team in cup.get("echipe", [])]
        for round_data in cup.get("runde", []):
            for slot in round_data.get("meciuri", []):
                if slot.get("e1") == old_name: slot["e1"] = new_name
                if slot.get("e2") == old_name: slot["e2"] = new_name
                if slot.get("castigator") == old_name: slot["castigator"] = new_name
                match = slot.get("meci")
                if match:
                    if match.get("e1") == old_name: match["e1"] = new_name
                    if match.get("e2") == old_name: match["e2"] = new_name
                    if match.get("masa_verde") == old_name: match["masa_verde"] = new_name
                    for event in match.get("evenimente", []):
                        if event.get("echipa") == old_name: event["echipa"] = new_name


def apply_match(data, match):
    for team_name in (match["e1"], match["e2"]):
        data["echipe"].setdefault(team_name, {"jucatori": {}, **STATS_ECHIPA})
    for name, gf, ga in ((match["e1"], match["goluri_e1"], match["goluri_e2"]),
                         (match["e2"], match["goluri_e2"], match["goluri_e1"])):
        team = data["echipe"][name]
        team["meciuri_jucate"] += 1
        team["goluri_marcate"] += gf
        team["goluri_primite"] += ga
        team["puncte"] += 3 if gf > ga else (1 if gf == ga else 0)
    data["istoric_meciuri"].append(match)
    apply_player_stats(data, match["e1"], match.get("mod_e1", {}))
    apply_player_stats(data, match["e2"], match.get("mod_e2", {}))


def rebuild_stats(data):
    for team in data["echipe"].values():
        team.update(STATS_ECHIPA)
        for stats in team["jucatori"].values():
            stats.update(STATS_JUCATOR)
    for match in data["istoric_meciuri"]:
        for name, gf, ga, key in ((match["e1"], match["goluri_e1"], match["goluri_e2"], "mod_e1"),
                                  (match["e2"], match["goluri_e2"], match["goluri_e1"], "mod_e2")):
            team = data["echipe"].setdefault(name, {"jucatori": {}, **STATS_ECHIPA})
            team["meciuri_jucate"] += 1
            team["goluri_marcate"] += gf
            team["goluri_primite"] += ga
            team["puncte"] += 3 if gf > ga else (1 if gf == ga else 0)
            apply_player_stats(data, name, match.get(key, {}))
    for cup in data.get("cupe", []):
        for round_data in cup.get("runde", []):
            for slot in round_data.get("meciuri", []):
                match = slot.get("meci")
                if match:
                    apply_player_stats(data, match["e1"], match.get("mod_e1", {}))
                    apply_player_stats(data, match["e2"], match.get("mod_e2", {}))


def generate_rounds(teams, home_away=False):
    rotating = list(teams)
    if len(rotating) < 2:
        return []
    if len(rotating) % 2:
        rotating.append(None)
    rounds = []
    for round_index in range(len(rotating) - 1):
        fixtures = []
        for i in range(len(rotating) // 2):
            one, two = rotating[i], rotating[-1 - i]
            if one is not None and two is not None:
                if (round_index + i) % 2:
                    one, two = two, one
                fixtures.append({"id": uuid.uuid4().hex[:8], "etapa": round_index + 1,
                                 "e1": one, "e2": two, "data": "", "meci_id": None})
        rounds.append(fixtures)
        rotating = [rotating[0], rotating[-1], *rotating[1:-1]]
    if home_away:
        for round_index, fixtures in enumerate(copy.deepcopy(rounds), start=len(rounds) + 1):
            rounds.append([{**f, "id": uuid.uuid4().hex[:8], "etapa": round_index,
                            "e1": f["e2"], "e2": f["e1"]} for f in fixtures])
    return [fixture for round_fixtures in rounds for fixture in round_fixtures]


def ranking(data):
    rows = []
    for name, team in data["echipe"].items():
        rows.append({"Echipă": name, "MJ": team["meciuri_jucate"], "V": 0, "E": 0, "Î": 0,
                     "GM": team["goluri_marcate"], "GP": team["goluri_primite"],
                     "DG": team["goluri_marcate"] - team["goluri_primite"], "Pct": team["puncte"],
                     "Formă": []})
    mapped = {row["Echipă"]: row for row in rows}
    for match in data["istoric_meciuri"]:
        if match["e1"] not in mapped or match["e2"] not in mapped:
            continue
        a, b = mapped[match["e1"]], mapped[match["e2"]]
        if match["goluri_e1"] > match["goluri_e2"]:
            a["V"] += 1; b["Î"] += 1
            a["Formă"].append("V"); b["Formă"].append("Î")
        elif match["goluri_e1"] < match["goluri_e2"]:
            b["V"] += 1; a["Î"] += 1
            b["Formă"].append("V"); a["Formă"].append("Î")
        else:
            a["E"] += 1; b["E"] += 1
            a["Formă"].append("E"); b["Formă"].append("E")
    for row in rows:
        row["Formă"] = " · ".join(row["Formă"][-5:]) or "–"
    return sorted(rows, key=lambda x: (-x["Pct"], -x["DG"], -x["GM"], x["Echipă"]))


def player_leaderboard(data, stat_key, label):
    players = [(player, team_name, stats.get(stat_key, 0))
               for team_name, team in data["echipe"].items()
               for player, stats in team.get("jucatori", {}).items()
               if stats.get(stat_key, 0) > 0]
    players.sort(key=lambda item: (-item[2], item[0].casefold(), item[1].casefold()))
    return [{"Loc": {1: "🥇", 2: "🥈", 3: "🥉"}.get(index, str(index)),
             "Jucător": player, "Echipă": team, label: value}
            for index, (player, team, value) in enumerate(players, 1)]


def _stage_sort_key(item):
    original_index, record = item
    stage = record.get("etapa")
    try:
        stage_number = int(stage)
    except (TypeError, ValueError):
        return (1, original_index, original_index)
    if stage_number <= 0:
        return (1, original_index, original_index)
    return (0, stage_number, original_index)


def ordered_by_stage(records):
    """Sort numbered rounds first; keep original order for records without a round."""
    return [record for _, record in sorted(enumerate(records), key=_stage_sort_key)]


def render_cards(rows):
    """Render compact, themed rows matching the original app's Treeview tables."""
    rows = list(rows)
    if not rows:
        st.caption("Nu există date de afișat încă.")
        return
    columns = list(dict.fromkeys(key for row in rows for key in row))
    head = "".join(f"<th>{html.escape(str(column))}</th>" for column in columns)
    body_rows = []
    for row in rows:
        cells = "".join(
            f"<td>{html.escape(str(row.get(column) if row.get(column) not in (None, '') else '–'))}</td>"
            for column in columns)
        body_rows.append(f"<tr>{cells}</tr>")
    markup = ("<div class='league-table-wrap'><table class='league-table'>"
              f"<thead><tr>{head}</tr></thead><tbody>{''.join(body_rows)}</tbody>"
              "</table></div>")
    st.markdown(markup, unsafe_allow_html=True)


def render_view_only(data, username, profile, entry, guest_invite=None, guest_profile=None):
    st.info("Acces de vizualizare · nu poți modifica această ligă.")
    if username:
        selection_key = league_key(entry)
        saved_selection = (profile.get("selectii_ligi", {}).get(selection_key) or
                           data.get("selectii_membri", {}).get(username, {}))
        if saved_selection.get("tip") == "jucator" or saved_selection.get("jucator"):
            st.success(f"Ai intrat ca jucător: {saved_selection.get('jucator')} · {saved_selection.get('echipa')}.")
            if st.session_state.get("player_profile_sync_error"):
                st.warning("Alegerea a fost salvată în ligă, dar nu s-a putut sincroniza cu profilul contului. Statisticile din ligă rămân disponibile.")
            player_stats = (data.get("echipe", {}).get(saved_selection.get("echipa"), {})
                            .get("jucatori", {}).get(saved_selection.get("jucator"), {}))
            if player_stats:
                stat_cols = st.columns(4)
                for col, label, key in zip(stat_cols, ("Goluri", "Assisturi", "Galbene", "Roșii"),
                        ("goluri", "asisturi", "cartonase_galbene", "cartonase_rosii")):
                    col.metric(label, player_stats.get(key, 0))
    can_choose_player = username or (guest_profile and guest_profile.get("kind") == "jucator") or (
        guest_invite and guest_invite.get("access_method") == "legacy"
        and guest_invite["invitation"].get("tip") == "jucator")
    tabs = st.tabs(["Clasament", "Loturi", "Meciuri", "Program", "Cupe", "Premii"] +
                   (["Alegerea mea"] if can_choose_player else []))
    t1, t2, t3, t4, t5 = tabs[:5]
    with t1:
        st.subheader(data.get("nume_liga", "Liga"))
        render_cards(ranking(data))
    with t2:
        for team, info in data["echipe"].items():
            with st.expander(f"{team} · {len(info.get('jucatori', {}))} jucători"):
                render_cards([{"Jucător": p, "Poziție": s.get("pozitie") or "–",
                               "Trofee": " · ".join(trofee_jucator(data, team, p)) or "–",
                               **{k: v for k, v in s.items() if k != "pozitie"}}
                              for p, s in info.get("jucatori", {}).items()])
    with t3:
        render_cards([{"Etapa": m.get("etapa") or "–", "Gazdă": m.get("e1"),
            "Scor": f"{m.get('goluri_e1', 0)} – {m.get('goluri_e2', 0)}", "Oaspeți": m.get("e2")}
            for m in ordered_by_stage(data.get("istoric_meciuri", []))])
    with t4:
        render_cards([{"Etapa": f.get("etapa"), "Gazdă": f.get("e1"), "Oaspeți": f.get("e2"),
            "Data": f.get("data", ""), "Status": "Jucat" if f.get("meci_id") else "Programat"}
            for f in data.get("program", [])])
    with t5:
        for cup in data.get("cupe", []):
            st.markdown(f"### {'🏅 ' if cup.get('super') else ''}{cup.get('nume', 'Cupa')} · {cup.get('status', '')}")
            for round_data in cup.get("runde", []):
                st.markdown(f"**{round_data.get('nume', 'Runda')}**")
                for slot in round_data.get("meciuri", []):
                    match = slot.get("meci")
                    if match:
                        st.write(f"{match['e1']} {match['goluri_e1']} – {match['goluri_e2']} {match['e2']} · câștigă {slot.get('castigator')}")
                    else:
                        st.write(f"{slot.get('e1') or '—'} vs {slot.get('e2') or 'așteaptă'}")
    with tabs[5]:
        awards = []
        selected_awards = data.get("premii_alese", {})
        for award in definitii_premii(data):
            selected = selected_awards.get(award["cheie"], {})
            if award["tip"] == "echipa":
                winner_text = selected.get("echipa", "")
            else:
                winner_text = (f"{selected.get('jucator')} · {selected.get('echipa')}"
                               if selected.get("jucator") else "")
            awards.append({"Premiu": award["titlu"], "Câștigător": winner_text or "Neacordat"})
        render_cards(awards)
    if can_choose_player:
        with tabs[6]:
            teams = list(data.get("echipe", {}))
            if username:
                st.write(f"{profile.get('nume', username)} · @{username} · {profile.get('pozitie', 'Poziție nespecificată')}")
                selection_key = league_key(entry)
                prior = (profile.get("selectii_ligi", {}).get(selection_key) or
                         data.get("selectii_membri", {}).get(username, {}))
            elif guest_profile:
                st.write(f"Profilul meu · **{guest_profile.get('player')}** · {guest_profile.get('team')}")
                prior = data.get("selectii_membri", {}).get(guest_profile.get("profile_id"), {})
            else:
                invitation = guest_invite["invitation"]
                st.write(f"Invitație pentru **{invitation.get('nume', 'Jucător invitat')}** · jucător în ligă")
                selection_key = invitation.get("id")
                prior = data.get("selectii_membri", {}).get(selection_key, {})
            if guest_profile:
                stats = data.get("echipe", {}).get(prior.get("echipa"), {}).get("jucatori", {}).get(prior.get("jucator"), {})
                if stats:
                    stat_cols = st.columns(4)
                    for col, title, field in zip(stat_cols, ("Goluri", "Assisturi", "Galbene", "Roșii"),
                        ("goluri", "asisturi", "cartonase_galbene", "cartonase_rosii")):
                        col.metric(title, stats.get(field, 0))
            elif teams:
                with st.form("viewer_profile_link"):
                    team = st.selectbox("Echipa", teams,
                        index=teams.index(prior["echipa"]) if prior.get("echipa") in teams else 0)
                    players = list(data["echipe"][team].get("jucatori", {}))
                    player = st.selectbox("Jucător din lot", players,
                        index=players.index(prior["jucator"]) if prior.get("jucator") in players else 0) if players else None
                    if not players:
                        st.caption("Echipa nu are jucători în lot încă.")
                    save_link = st.form_submit_button("Salvează asocierea", disabled=not bool(players))
                if save_link and player:
                    if username:
                        users = load_users()
                        users[username].setdefault("selectii_ligi", {})[selection_key] = {
                            "echipa": team, "jucator": player, "pozitie": profile.get("pozitie", ""),
                            "actualizat": dt.datetime.now().timestamp()}
                        save_users(users)
                        st.success("Asocierea a fost salvată în profilul tău.")
                    else:
                        try:
                            save_guest_selection(entry["path"], guest_invite["invitation"], team, player)
                            st.success("Asocierea jucătorului invitat a fost salvată.")
                        except ValueError as exc:
                            st.error(str(exc))
                    st.rerun()
                if prior:
                    stats = data.get("echipe", {}).get(prior.get("echipa"), {}).get("jucatori", {}).get(prior.get("jucator"), {})
                    if stats:
                        st.metric("Goluri în această ligă", stats.get("goluri", 0))


def render_guest_player_choice(data, path, invitation):
    st.subheader("Alegerea mea în această ligă")
    st.caption(f"Invitat ca jucător: {invitation.get('nume', 'Invitat')}")
    teams = list(data.get("echipe", {}))
    if not teams:
        st.info("Liga nu are încă echipe.")
        return
    previous = data.get("selectii_membri", {}).get(invitation.get("id"), {})
    with st.form("guest_player_choice"):
        team = st.selectbox("Echipa", teams,
            index=teams.index(previous["echipa"]) if previous.get("echipa") in teams else 0)
        players = list(data["echipe"][team].get("jucatori", {}))
        player = st.selectbox("Jucător", players,
            index=players.index(previous["jucator"]) if previous.get("jucator") in players else 0) if players else None
        if not players:
            st.caption("Echipa aleasă nu are jucători în lot.")
        submit = st.form_submit_button("Salvează alegerea", type="primary", disabled=not bool(players))
    if submit and player:
        try:
            save_guest_selection(path, invitation, team, player)
            st.success("Alegerea ta a fost salvată.")
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))
    if previous:
        stats = data.get("echipe", {}).get(previous.get("echipa"), {}).get("jucatori", {}).get(previous.get("jucator"), {})
        if stats:
            st.metric("Goluri în această ligă", stats.get("goluri", 0))


def auth_view(cookie_manager):
    st.markdown("## Intră în cont sau creează un profil")
    st.caption("Te poți conecta cu numele de utilizator sau adresa de e-mail asociată contului.")
    if not SUPABASE_ENABLED:
        st.warning("Baza de date online nu este conectată. Conturile create aici se pot pierde când aplicația repornește. Verifică Secrets în setările Streamlit Cloud.")
    pending = st.session_state.get("pending_remember_login")
    if pending:
        st.info("Se salvează conectarea pe acest dispozitiv. Te vei conecta imediat ce browserul confirmă salvarea.")
        if st.button("Reîncearcă salvarea conectării", type="primary"):
            remember_account(cookie_manager, pending["username"])
        return
    login_tab, signup_tab = st.tabs(["Autentificare", "Cont nou"])
    with login_tab:
        with st.form("login_account"):
            username = st.text_input("Nume de utilizator sau e-mail")
            password = st.text_input("Parolă", type="password")
            remember = st.checkbox("Rămâi conectat pe acest dispozitiv (30 de zile)", value=True)
            login = st.form_submit_button("Intră în cont", type="primary")
        if login:
            attempts = st.session_state.setdefault("login_attempts", [])
            now = dt.datetime.now().timestamp()
            attempts[:] = [item for item in attempts if now - item < 60]
            if len(attempts) >= 5:
                st.error("Prea multe încercări. Așteaptă un minut și încearcă din nou.")
            else:
                identifier = username.strip().casefold()
                try:
                    users = load_users()
                    if "@" in identifier:
                        key = next((user_key for user_key, user_record in users.items()
                                    if str(user_record.get("email", "")).strip().casefold() == identifier), "")
                    else:
                        key = identifier
                    record = users.get(key)
                except Exception as exc:
                    st.error("Nu pot accesa baza de date a conturilor. Verifică setările Supabase din Streamlit Cloud și încearcă din nou.")
                    st.caption(f"Detaliu: {exc}")
                    record = None
                    attempts.append(now)
                    st.stop()
                if record and verify_password(record, password):
                    st.session_state.pop("login_attempts", None)
                    if remember:
                        remember_account(cookie_manager, key)
                        st.success("Conectarea se salvează pe acest dispozitiv…")
                        return
                    else:
                        revoke_remembered_account(cookie_manager)
                        st.session_state["user_key"] = key
                    st.session_state.pop("entered_league", None)
                    st.session_state.pop("active_league_picker", None)
                    st.rerun()
                attempts.append(now)
                st.error("E-mailul/numele de utilizator sau parola nu corespund. Dacă acest cont a fost creat înainte să adaugi e-mailul, conectează-te cu numele de utilizator.")
    with signup_tab:
        with st.form("signup_account"):
            username = st.text_input("Nume de utilizator", key="new_username")
            email = st.text_input("Adresă de e-mail", key="new_email")
            name = st.text_input("Nume și prenume")
            birthday = st.date_input("Data nașterii", value=dt.date(2000, 1, 1), max_value=dt.date.today())
            plays = st.selectbox("Joci la un club profesionist?", ["Da", "Nu"])
            position = st.selectbox("Poziția ta", ["Portar", "Fundaș", "Mijlocaș", "Atacant"])
            password = st.text_input("Parolă (minimum 6 caractere)", type="password", key="new_password")
            confirm = st.text_input("Confirmă parola", type="password")
            remember_new = st.checkbox("Rămâi conectat pe acest dispozitiv (30 de zile)", value=True,
                                       key="remember_new_account")
            signup = st.form_submit_button("Creează cont", type="primary")
        if signup:
            if password != confirm:
                st.error("Parolele nu coincid.")
            else:
                try:
                    account_key = create_account(
                        username, email, password, name, birthday, plays, position)
                    if remember_new:
                        remember_account(cookie_manager, account_key)
                        st.success("Contul a fost creat. Se salvează conectarea pe acest dispozitiv…")
                        return
                    st.session_state["user_key"] = account_key
                    st.session_state.pop("entered_league", None)
                    st.session_state.pop("active_league_picker", None)
                    st.success("Contul a fost creat.")
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))
                except Exception as exc:
                    st.error("Contul nu a putut fi salvat în baza de date. Verifică setările Supabase din Streamlit Cloud.")
                    st.caption(f"Detaliu: {exc}")


def main():
    st.set_page_config(page_title="Liga de fotbal", page_icon="⚽", layout="wide")
    cookie_manager = stx.CookieManager(key="persistent_cookie_manager")
    # Tema este fixată pe întunecat pentru a evita diferențele de contrast
    # dintre componentele Streamlit și stilurile personalizate.
    st.session_state["dark_mode"] = True
    if not st.session_state.get("user_key"):
        if not finish_pending_remember_login(cookie_manager):
            restore_remembered_account(cookie_manager)
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@500;600;700;800&display=swap');
    :root { color-scheme:light; --bg:#f5f7f3; --paper:#fff; --panel:#fff; --panel2:#edf3ed; --line:#e2e9e1;
            --text:#202a22; --muted:#718074; --green:#276747; --green-dark:#1e5238;
            --pale:#e9f2eb; --gold:#b17b2d; --sidebar:#eef2ec; --hover:#e1eae1;
            --selected:#dfece1; --input:#fcfdfb; --input-line:#dbe4da; --focus:#e5f0e7;
            --disabled:#e4e9e4; --disabled-text:#68736b; --header:rgba(245,247,243,.9);
            --shadow:0 8px 28px rgba(33,55,38,.055); }
    html, body, [class*="css"] { font-family:'DM Sans',sans-serif; }
    [data-testid="stAppViewContainer"] { background:var(--bg); color:var(--text); }
    [data-testid="stHeader"] { background:var(--header); }
    [data-testid="stMainBlockContainer"] { max-width:1440px; padding-top:2rem; padding-bottom:4rem; }
    [data-testid="stSidebar"] { background:var(--sidebar); border-right:1px solid var(--line); }
    [data-testid="stSidebar"] * { color:var(--text); }
    [data-testid="stSidebar"] [data-testid="stRadio"] label { padding:9px 11px; border-radius:10px; transition:.15s ease; }
    [data-testid="stSidebar"] [data-testid="stRadio"] label:hover { background:var(--hover); }
    [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) { background:var(--selected); color:var(--green-dark); font-weight:700; }
    h1,h2,h3 { font-family:'Manrope',sans-serif !important; letter-spacing:-.035em; color:var(--text); }
    h1 { font-weight:800 !important; }
    h2,h3 { font-weight:750 !important; }
    p, [data-testid="stCaptionContainer"] { color:var(--muted); }
    [data-testid="stMetric"] { background:var(--paper); border:1px solid var(--line);
        padding:17px 19px; border-radius:15px; box-shadow:var(--shadow); }
    .league-table-wrap { width:100%; overflow-x:auto; border:1px solid var(--line);
        border-radius:10px; background:var(--paper); box-shadow:var(--shadow); margin:.35rem 0 1rem; }
    table.league-table { width:100%; border-collapse:collapse; color:var(--text); font-size:.92rem; }
    .league-table th { background:var(--panel2); color:var(--muted); font-size:.76rem;
        font-weight:750; letter-spacing:.035em; text-align:left; white-space:nowrap;
        padding:10px 14px; border-bottom:1px solid var(--line); }
    .league-table td { padding:9px 14px; border-bottom:1px solid var(--line);
        white-space:nowrap; }
    .league-table tbody tr:nth-child(even) { background:var(--panel2); }
    .league-table tbody tr:last-child td { border-bottom:0; }
    .league-table tbody tr:hover { background:var(--pale); }
    [data-testid="stMetricLabel"] { color:var(--muted); font-size:.82rem; }
    [data-testid="stMetricValue"] { color:var(--green-dark); font-family:'Manrope',sans-serif; font-weight:800; }
    [data-baseweb="tab-list"] { gap:5px; border-bottom:1px solid var(--line);
        flex-wrap:wrap !important; overflow:visible !important; white-space:normal !important; }
    [data-baseweb="tab"] { background:transparent; border-radius:9px 9px 0 0;
        padding:9px 13px; color:var(--muted); font-weight:600; }
    [data-baseweb="tab"][aria-selected="true"], .stTabs [aria-selected="true"] { color:var(--green) !important; }
    [data-baseweb="tab-highlight"] { background-color:var(--green) !important; height:3px; }
    [data-testid="stForm"], [data-testid="stExpander"] { border:1px solid var(--line); border-radius:14px; background:var(--paper); }
    [data-testid="stVerticalBlockBorderWrapper"] > div { border-color:var(--line) !important; border-radius:16px !important; background:var(--paper); box-shadow:var(--shadow); }
    [data-testid="stTextInput"] input, [data-testid="stNumberInput"] input,
    [data-testid="stDateInput"] input, [data-testid="stSelectbox"] [data-baseweb="select"] > div,
    [data-testid="stMultiSelect"] [data-baseweb="select"] > div { border-color:var(--input-line); border-radius:9px; background:var(--input); color:var(--text); }
    [data-testid="stSelectbox"] [data-baseweb="select"] > div,
    [data-testid="stSelectbox"] [data-baseweb="select"] > div,
    [data-testid="stMultiSelect"] [data-baseweb="select"] > div { background:var(--input) !important; color:var(--text) !important; }
    [data-testid="stTextInput"] input:focus, [data-testid="stNumberInput"] input:focus { border-color:#78a68a; box-shadow:0 0 0 3px var(--focus); }
    [data-baseweb="popover"], [data-baseweb="menu"], [role="listbox"] { background:var(--paper) !important; color:var(--text) !important; }
    [role="option"] { color:var(--text) !important; }
    [role="option"]:hover, [aria-selected="true"][role="option"] { background:var(--panel2) !important; color:var(--text) !important; }
    [data-testid="stWidgetLabel"], [data-testid="stMarkdownContainer"], [data-testid="stMarkdownContainer"] * { color:var(--text); }
    [data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] * { color:var(--muted); }
    a { color:var(--green) !important; }
    [data-testid="stAlert"] { color:var(--text); }
    [data-testid="stRadio"] label, [data-testid="stCheckbox"] label,
    [data-testid="stToggle"] label { color:var(--text) !important; }
    div.stButton > button, div.stFormSubmitButton > button { border-radius:9px;
        border:1px solid #dce5dc; min-height:42px; font-weight:700; transition:.15s ease; }
    div.stButton > button:hover, div.stFormSubmitButton > button:hover { border-color:#8aaf96; color:var(--green-dark); transform:translateY(-1px); }
    div.stButton > button[kind="primary"], div.stFormSubmitButton > button[kind="primary"] {
        background:var(--green); border-color:var(--green); color:#fff; box-shadow:0 4px 12px #27674722; }
    div.stButton > button[kind="primary"]:hover, div.stFormSubmitButton > button[kind="primary"]:hover { background:var(--green-dark); color:#fff; }
    button[data-testid="stBaseButton-primary"], button[data-testid="stBaseButton-primaryFormSubmit"] {
        background:var(--green) !important; border-color:var(--green) !important; color:#fff !important;
        opacity:1 !important; box-shadow:0 4px 12px #27674722 !important; }
    button[data-testid="stBaseButton-primary"] *, button[data-testid="stBaseButton-primaryFormSubmit"] * {
        color:#fff !important; opacity:1 !important; font-weight:750 !important; }
    button[data-testid="stBaseButton-primary"]:hover, button[data-testid="stBaseButton-primaryFormSubmit"]:hover {
        background:var(--green-dark) !important; border-color:var(--green-dark) !important; color:#fff !important; }
    button[data-testid="stBaseButton-primary"]:disabled, button[data-testid="stBaseButton-primaryFormSubmit"]:disabled {
        background:var(--disabled) !important; border-color:var(--line) !important; color:var(--disabled-text) !important;
        box-shadow:none !important; opacity:1 !important; cursor:not-allowed !important; }
    button[data-testid="stBaseButton-primary"]:disabled *, button[data-testid="stBaseButton-primaryFormSubmit"]:disabled * {
        color:var(--disabled-text) !important; }
    button[data-testid="stBaseButton-secondary"] { color:var(--text) !important; }
    button[data-testid="stBaseButton-secondary"] * { color:inherit !important; }
    button[data-testid^="stBaseButton-"]:focus-visible { outline:3px solid #83bd94 !important; outline-offset:2px; }
    [data-testid="stAlert"] { border-radius:12px; }
    [data-testid="stFileUploader"] section { border-radius:12px; border-color:var(--input-line); background:var(--input); color:var(--text); }
    .league-kicker { color:var(--green); text-transform:uppercase; letter-spacing:.14em;
        font-size:.74rem; font-weight:800; margin-bottom:.2rem; }
    .league-subtitle { color:var(--muted); margin-top:-.35rem; margin-bottom:1.5rem; font-size:1.03rem; }
    @media(max-width:700px) { [data-testid="stMainBlockContainer"] { padding:1.2rem 1rem 3rem; }
        [data-testid="stMetric"] { padding:13px; } h1 { font-size:1.8rem !important; } }
    </style>
    """, unsafe_allow_html=True)
    dark_mode = bool(st.session_state.get("dark_mode", False))
    if dark_mode:
        st.markdown("""
        <style>
        :root { color-scheme:dark; --bg:#111815 !important; --paper:#1b2520 !important;
          --panel:#1b2520 !important; --panel2:#24322a !important; --line:#34443a !important;
          --text:#e8f0e9 !important; --muted:#a5b4a8 !important; --green:#56b878 !important;
          --green-dark:#328c54 !important; --pale:#203a2a !important; --gold:#e5b86b !important;
          --sidebar:#17211b !important; --hover:#24322a !important; --selected:#203a2a !important;
          --input:#131c17 !important; --input-line:#46574b !important; --focus:#203a2a !important;
          --disabled:#303b34 !important; --disabled-text:#b7c3ba !important;
          --header:rgba(17,24,21,.94) !important;
          --shadow:0 10px 30px rgba(0,0,0,.2) !important; }
        [data-testid="stAppViewContainer"] { background:#111815 !important; color:#e8f0e9 !important; }
        [data-testid="stHeader"] { background:var(--header) !important; }
        [data-testid="stSidebar"] { background:#17211b !important; border-color:#34443a !important; }
        [data-testid="stSidebar"] *, h1,h2,h3,[data-testid="stMarkdownContainer"],
        [data-testid="stMarkdownContainer"] *,[data-testid="stWidgetLabel"] { color:#e8f0e9; }
        p,[data-testid="stCaptionContainer"],[data-testid="stCaptionContainer"] * { color:#a5b4a8 !important; }
        [data-testid="stMetric"],[data-testid="stForm"],[data-testid="stExpander"],
        [data-testid="stVerticalBlockBorderWrapper"] > div { background:#1b2520 !important;
          border-color:#34443a !important; color:#e8f0e9 !important; }
        [data-testid="stMetricValue"] { color:#82d39c !important; }
        a { color:#82d39c !important; }
        [data-testid="stTextInput"] input,[data-testid="stNumberInput"] input,[data-testid="stDateInput"] input,
        [data-testid="stTextArea"] textarea,[data-testid="stSelectbox"] [data-baseweb="select"] > div,
        [data-testid="stMultiSelect"] [data-baseweb="select"] > div {
          background:#131c17 !important; color:#e8f0e9 !important; border-color:#46574b !important; }
        [data-testid="stTextInputRootElement"] { background:#131c17 !important; border-color:#46574b !important; }
        [data-testid="stTextInput"] input::placeholder,[data-testid="stTextArea"] textarea::placeholder { color:#8c9c90 !important; }
        button[aria-label="Show password"] { background:#24322a !important; color:#e8f0e9 !important; border-color:#46574b !important; }
        button[aria-label="Show password"] * { color:#e8f0e9 !important; }
        [data-baseweb="tab"] { color:#a5b4a8 !important; }
        [data-baseweb="tab"][aria-selected="true"] { color:#82d39c !important; }
        [data-testid="stFileUploader"] section { background:#17211b !important; border-color:#46574b !important; }
        [data-baseweb="popover"],[data-baseweb="menu"],[role="listbox"] { background:#1b2520 !important; color:#e8f0e9 !important; }
        [role="option"] { color:#e8f0e9 !important; }
        [role="option"]:hover,[aria-selected="true"][role="option"] { background:#24322a !important; color:#fff !important; }
        [data-testid="stAlert"] { background:#1b2520 !important; }
        button[data-testid="stBaseButton-secondary"] { background:#202d25 !important; color:#e8f0e9 !important; border-color:#405246 !important; }
        button[data-testid="stBaseButton-secondary"] * { color:#e8f0e9 !important; }
        button[data-testid="stBaseButton-primary"],button[data-testid="stBaseButton-primaryFormSubmit"] {
          background:#2f9b5b !important; border-color:#2f9b5b !important; color:#fff !important; }
        button[data-testid="stBaseButton-primary"] *,button[data-testid="stBaseButton-primaryFormSubmit"] * { color:#fff !important; }
        button[data-testid="stBaseButton-primary"]:disabled,button[data-testid="stBaseButton-primaryFormSubmit"]:disabled {
          background:#303b34 !important; border-color:#3d4941 !important; color:#9eaaa1 !important; }
        button[data-testid="stBaseButton-primary"]:disabled *,button[data-testid="stBaseButton-primaryFormSubmit"]:disabled * { color:#9eaaa1 !important; }
        </style>
        """, unsafe_allow_html=True)
    st.title("⚽ Managerul ligii de fotbal")
    st.markdown('<div class="league-subtitle">Clasamente, meciuri și cupe într-un singur loc</div>', unsafe_allow_html=True)
    access_code = str(st.query_params.get("cod", "")).strip()
    invite_token = str(st.query_params.get("invitat", "")).strip()
    guest_entry = find_access_code(access_code) if access_code else None
    if not access_code and invite_token:
        guest_entry = find_invitation(invite_token)
    if access_code and not guest_entry:
        st.error("Codul de acces nu este valid sau a fost schimbat.")
        if st.button("Înapoi la pagina principală"):
            st.query_params.clear()
            st.session_state.pop("active_guest_invite", None)
            st.session_state.pop("active_guest_access", None)
            st.rerun()
        return
    if invite_token and not guest_entry:
        st.error("Această invitație nu mai este valabilă sau a fost revocată.")
        if st.button("Înapoi la pagina principală"):
            st.query_params.clear()
            st.session_state.pop("active_guest_invite", None)
            st.session_state.pop("active_guest_access", None)
            st.rerun()
        return
    is_code_access = bool(guest_entry and guest_entry.get("access_method") == "cod")
    is_legacy_guest = bool(guest_entry and guest_entry.get("access_method") == "legacy")
    is_guest = is_legacy_guest
    username = st.session_state.get("user_key")
    users = load_users()
    if is_code_access and (not username or username not in users):
        auth_view(cookie_manager)
        return
    if not is_guest and not is_code_access and (not username or username not in users):
        st.session_state.pop("user_key", None)
        st.session_state.pop("active_guest_invite", None)
        st.session_state.pop("active_guest_access", None)
        auth_view(cookie_manager)
        return
    guest_profile = None
    if is_code_access:
        profile = users[username]
        profile.setdefault("selectii_ligi", {})
        if guest_entry.get("code_type") == "spectator" and guest_entry["owner"].casefold() != username.casefold():
            guest_profile = spectator_entry_gate(guest_entry)
            if guest_profile is None:
                return
        try:
            access_role = join_league_with_code(guest_entry, username, access_code, guest_profile)
        except ValueError as exc:
            st.error(str(exc))
            if st.button("Înapoi la ligile mele"):
                st.query_params.clear()
                st.session_state.pop("spectator_profile", None)
                st.session_state.pop("spectator_choice_stage", None)
                st.rerun()
            return
        except Exception as exc:
            st.error("Nu am putut salva intrarea ca jucător. Verifică dacă aplicația Streamlit Cloud este actualizată și încearcă din nou.")
            st.caption(f"Detaliu: {exc}")
            if st.button("Reîncearcă intrarea"):
                st.rerun()
            return
        if access_role != "owner":
            st.session_state["entered_league"] = league_key(guest_entry)
        else:
            st.session_state["entered_league"] = league_key(guest_entry)
        st.query_params.clear()
        st.session_state.pop("spectator_profile", None)
        st.session_state.pop("spectator_choice_stage", None)
        st.session_state.pop("spectator_team_choice", None)
        st.session_state.pop("spectator_player_choice", None)
        st.rerun()
        return
    if is_guest:
        invite = guest_entry["invitation"]
        profile = {"nume": invite.get("nume", "Invitat"), "pozitie": "", "selectii_ligi": {}}
        st.session_state.pop("active_guest_access", None)
        st.session_state["active_guest_invite"] = {
            "path": str(guest_entry["path"]), "token": invite_token, "id": invite.get("id")}
        paths = [guest_entry]
    else:
        st.session_state.pop("active_guest_invite", None)
        st.session_state.pop("active_guest_access", None)
        profile = users[username]
        profile.setdefault("selectii_ligi", {})
        paths = get_user_leagues(username)
    st.session_state.setdefault("login_attempts", [])
    st.session_state["active_league_role"] = "owner"
    with st.sidebar:
        if is_guest:
            st.markdown(f"### 🎟️ {profile['nume']}")
            st.caption("Cod de ligă · acces temporar" if guest_entry.get("access_method") == "cod"
                       else "Invitație de ligă · acces temporar")
            if st.button("Ieși din invitație", width="stretch"):
                st.query_params.clear()
                st.session_state.pop("active_guest_invite", None)
                st.session_state.pop("active_guest_access", None)
                st.session_state.pop("spectator_profile", None)
                st.session_state.pop("spectator_choice_stage", None)
                st.session_state.pop("spectator_team_choice", None)
                st.session_state.pop("spectator_player_choice", None)
                st.rerun()
        else:
            st.markdown(f"### 👤 {profile.get('nume') or username}")
            st.caption(f"@{username}")
            if st.button("Deconectare", width="stretch"):
                revoke_remembered_account(cookie_manager)
                st.session_state.pop("user_key", None)
                st.session_state.pop("active_league_role", None)
                st.session_state.pop("entered_league", None)
                st.session_state.pop("active_league_picker", None)
                st.rerun()
        st.divider()
    by_label = {f"{load_league(item['path']).get('nume_liga', item['path'].stem)} · "
                f"{item['owner']} · {'proprie' if item['role'] == 'owner' else item['role']}": item
                for item in paths}
    by_key = {league_key(item): item for item in paths}
    entered_key = league_key(guest_entry) if is_guest else st.session_state.get("entered_league")
    if entered_key not in by_key:
        st.session_state.pop("entered_league", None)
        entered_key = None
    if entered_key is None:
        st.markdown("## Bine ai venit în Managerul Ligii de Fotbal")
        st.caption("Creează o ligă nouă sau intră într-o ligă pe care o administrezi ori care ți-a fost partajată.")
        create_col, enter_col = st.columns(2, gap="large")
        with create_col:
            with st.container(border=True):
                st.markdown("### ➕ Creează o ligă")
                with st.form("launcher_create_league"):
                    new_name = st.text_input("Numele ligii", "Liga mea")
                    source_entry = st.selectbox("Pornește de la", [None, *paths],
                        format_func=lambda item: "Ligă goală" if item is None else
                            f"{load_league(item['path']).get('nume_liga', item['path'].stem)} · @{item['owner']}")
                    league_type = st.selectbox("Tipul competiției", ["Ligă", "Ligă + cupă", "Cupă"])
                    create = st.form_submit_button("Creează liga", type="primary", width="stretch")
                if create:
                    created_path = create_user_league(username, new_name, source_entry, league_type)
                    created_entry = {"path": created_path, "role": "owner", "owner": username}
                    st.session_state["entered_league"] = league_key(created_entry)
                    st.session_state["active_league_role"] = "owner"
                    st.session_state.pop("active_league_picker", None)
                    st.rerun()
        with enter_col:
            with st.container(border=True):
                st.markdown("### 📂 Intră într-o ligă")
                if paths:
                    selected_launcher = st.selectbox("Alege liga", list(by_label), key="launcher_league")
                    selected_launcher_entry = by_label[selected_launcher]
                    st.caption(f"Proprietar: @{selected_launcher_entry['owner']} · Acces: "
                               f"{'propriu' if selected_launcher_entry['role'] == 'owner' else selected_launcher_entry['role']}")
                    if st.button("Intră în ligă", type="primary", width="stretch"):
                        st.session_state["entered_league"] = league_key(selected_launcher_entry)
                        st.session_state.pop("active_league_picker", None)
                        st.rerun()
                else:
                    st.info("Nu ai încă ligi. Creează una sau importă un fișier JSON.")
                first_import = st.file_uploader("Importă o ligă existentă", type=["json"], key="launcher_import")
                if first_import and st.button("Importă liga", key="launcher_import_button"):
                    try:
                        imported = normalizeaza_date(json.loads(first_import.getvalue().decode("utf-8")))
                        if SUPABASE_ENABLED:
                            existing_names = {load_league(item["path"]).get("nume_liga", "").casefold()
                                              for item in get_user_leagues(username) if item["role"] == "owner"}
                            target = db_league_path(username, uuid.uuid4())
                            already_exists = imported.get("nume_liga", "").casefold() in existing_names
                        else:
                            user_folder = BASE_DIR / username
                            user_folder.mkdir(parents=True, exist_ok=True)
                            target = user_folder / f"{safe_slug(imported['nume_liga'])}.json"
                            already_exists = target.exists()
                        if already_exists:
                            st.error("Există deja o ligă cu acest nume în cont.")
                        else:
                            save_league(target, imported)
                            st.session_state["entered_league"] = f"{username}/{target.name}"
                            st.session_state.pop("active_league_picker", None)
                            st.rerun()
                    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
                        st.error(f"Fișierul nu este un JSON de ligă valid: {exc}")
                st.divider()
                st.markdown("#### Intră cu un cod de ligă")
                with st.form("launcher_access_code"):
                    access_code = st.text_input("Cod spectator sau editor")
                    enter_with_code = st.form_submit_button("Continuă cu codul", type="primary", width="stretch")
                if enter_with_code:
                    normalized_code = normalize_access_code(access_code)
                    if len(normalized_code) != 12:
                        st.error("Codul trebuie să aibă 12 caractere.")
                    else:
                        st.query_params["cod"] = normalized_code
                        st.rerun()
        return
    if is_guest:
        chosen_key = entered_key
    else:
        with st.sidebar:
            if st.button("↩ Schimbă liga", width="stretch"):
                st.session_state.pop("entered_league", None)
                st.session_state.pop("active_league_picker", None)
                st.rerun()
            st.divider()
            st.markdown("**Liga activă**")
        labels_by_key = {league_key(item): label for label, item in by_label.items()}
        chosen_key = st.sidebar.selectbox("Alege altă ligă", list(by_key),
            index=list(by_key).index(entered_key), format_func=lambda key: labels_by_key[key], key="active_league_picker")
        if chosen_key != entered_key:
            st.session_state["entered_league"] = chosen_key
            st.rerun()
    selected_entry = by_key[chosen_key]
    path = selected_entry["path"]
    role = selected_entry["role"]
    owner = selected_entry["owner"]
    st.session_state["active_league_role"] = role
    data = load_league(path)
    if role == "vizitator":
        st.title(data.get("nume_liga", "Liga"))
        st.caption(f"Partajată de @{owner}")
        render_view_only(data, username, profile, selected_entry,
                         guest_entry if guest_entry and guest_entry.get("access_method") == "legacy" else None,
                         guest_profile)
        return
    pages = ["Clasament", "Statistici", "Echipe și jucători", "Meciuri și program", "Cupa",
            "Supercupa", "Premii sezon", "Transferuri", "Membri", "Import / export"]
    if not is_guest:
        pages.insert(-1, "Profil")
    elif guest_entry.get("access_method") == "legacy" and guest_entry["invitation"].get("tip") == "jucator":
        pages.insert(-1, "Alegerea mea")
    if st.session_state.get("main_navigation") not in pages:
        st.session_state["main_navigation"] = pages[0]
    page = st.sidebar.radio(
        "Navigare",
        pages,
        format_func=lambda item: {
            "Clasament": "🏆  Clasament",
            "Echipe și jucători": "🛡  Echipe și jucători",
            "Meciuri și program": "⚽  Meciuri și program",
            "Cupa": "🥇  Cupa",
            "Supercupa": "🏅  Supercupa",
            "Statistici": "📊  Statistici",
            "Premii sezon": "🏅  Premii sezon",
            "Transferuri": "🔁  Transferuri",
            "Membri": "👥  Membri",
            "Profil": "👤  Profil",
            "Alegerea mea": "🪪  Alegerea mea",
            "Import / export": "⚙  Import / export",
        }[item],
        key="main_navigation",
    )

    if page == "Alegerea mea" and is_guest:
        render_guest_player_choice(data, path, guest_entry["invitation"])

    if page == "Clasament":
        st.subheader(data["nume_liga"])
        c1, c2, c3 = st.columns(3)
        c1.metric("Echipe", len(data["echipe"]))
        c2.metric("Meciuri", len(data["istoric_meciuri"]))
        c3.metric("Jucători", sum(len(t["jucatori"]) for t in data["echipe"].values()))
        if data["echipe"]:
            render_cards(ranking(data))
            st.caption("Forma ultimelor cinci meciuri: V = victorie · E = egal · Î = înfrângere")
        else:
            st.info("Adaugă echipe pentru a vedea clasamentul.")
        with st.expander("Setări ligă"):
            rename = st.text_input("Denumire", value=data["nume_liga"], key="rename")
            if st.button("Salvează denumirea") and rename.strip():
                data["nume_liga"] = rename.strip(); save_league(path, data); st.rerun()

    if page == "Echipe și jucători":
        st.subheader("Echipe și loturi")
        with st.form("echipa_noua"):
            team_name = st.text_input("Adaugă echipă")
            add_team = st.form_submit_button("Adaugă")
        if add_team:
            if not team_name.strip(): st.error("Introdu numele echipei.")
            elif team_name.strip() in data["echipe"]: st.error("Echipa există deja.")
            else:
                data["echipe"][team_name.strip()] = {"jucatori": {}, **STATS_ECHIPA}
                save_league(path, data); st.rerun()
        for name, team in data["echipe"].items():
            trophies = trofee_echipa(data, name)
            with st.expander(f"{name} · {len(team['jucatori'])} jucători" +
                             (f" · 🏆 {len(trophies)} trofee" if trophies else "")):
                st.write(f"{team['meciuri_jucate']} meciuri · {team['puncte']} puncte · "
                         f"goluri {team['goluri_marcate']}–{team['goluri_primite']}")
                with st.form(f"jucator_{name}"):
                    player_name = st.text_input("Jucător nou", key=f"pn_{name}")
                    player_position = st.selectbox("Poziție", ["Nespecificată", "Portar", "Fundaș", "Mijlocaș", "Atacant"], key=f"pp_{name}")
                    add_player = st.form_submit_button("Adaugă în lot")
                if add_player:
                    if player_name.strip() in team["jucatori"]:
                        st.error("Jucătorul există deja în lot.")
                    elif player_name.strip():
                        team["jucatori"][player_name.strip()] = {**STATS_JUCATOR,
                            "pozitie": "" if player_position == "Nespecificată" else player_position}
                        save_league(path, data); st.rerun()
                if team["jucatori"]:
                    render_cards([{"Jucător": p, "Poziție": s.get("pozitie") or "–",
                                   **{k: v for k, v in s.items() if k != "pozitie"}}
                                  for p, s in team["jucatori"].items()])
                    with st.form(f"player_position_form_{safe_slug(name)}"):
                        position_player = st.selectbox("Actualizează poziția", list(team["jucatori"]),
                            key=f"position_player_{safe_slug(name)}")
                        player_positions = ["Nespecificată", "Portar", "Fundaș", "Mijlocaș", "Atacant"]
                        previous_position = team["jucatori"][position_player].get("pozitie", "")
                        position_index = player_positions.index(previous_position) if previous_position in player_positions else 0
                        chosen_position = st.selectbox("Poziție nouă", player_positions, index=position_index,
                            key=f"chosen_position_{safe_slug(name)}")
                        save_position = st.form_submit_button("Salvează poziția")
                    if save_position:
                        team["jucatori"][position_player]["pozitie"] = "" if chosen_position == "Nespecificată" else chosen_position
                        save_league(path, data); st.success("Poziția a fost actualizată."); st.rerun()
                    for player_name, stats in team["jucatori"].items():
                        player_trophies = trofee_jucator(data, name, player_name)
                        if player_trophies:
                            st.caption(f"🏅 {player_name}: " + " · ".join(player_trophies))
                    with st.form(f"sterge_jucator_{name}"):
                        delete_player = st.selectbox("Șterge jucător", list(team["jucatori"]), key=f"dp_{name}")
                        delete_player_btn = st.form_submit_button("Șterge din lot")
                    if delete_player_btn:
                        del team["jucatori"][delete_player]; save_league(path, data); st.rerun()
                with st.form(f"rename_team_{name}"):
                    renamed = st.text_input("Redenumește echipa", value=name, key=f"rename_value_{name}")
                    rename_button = st.form_submit_button("Salvează numele")
                if rename_button:
                    try:
                        rename_team(data, name, renamed)
                        save_league(path, data); st.success("Echipa a fost redenumită."); st.rerun()
                    except ValueError as exc:
                        st.error(str(exc))

    if page == "Meciuri și program":
        st.subheader("Înregistrează un meci")
        teams = list(data["echipe"])
        if len(teams) < 2:
            st.info("Adaugă cel puțin două echipe.")
        else:
            match_ids = {m.get("id") for m in data["istoric_meciuri"]}
            playable = [f for f in ordered_by_stage(data["program"])
                        if not f.get("meci_id") or f.get("meci_id") not in match_ids]
            scheduled = st.selectbox("Meci programat (opțional)", [None, *playable],
                format_func=lambda f: "Alege manual" if f is None else
                    f"Etapa {f.get('etapa') or '–'} · {f.get('e1')} – {f.get('e2')}" + (f" · {f.get('data')}" if f.get("data") else ""),
                key="scheduled_fixture")
            fixture_identity = scheduled.get("id") if scheduled else "manual"
            draft_id = hashlib.sha1(str(f"{selected_entry.get('id')}:{fixture_identity}").encode()).hexdigest()[:12]
            home_default = teams.index(scheduled["e1"]) if scheduled and scheduled.get("e1") in teams else 0
            away_default = teams.index(scheduled["e2"]) if scheduled and scheduled.get("e2") in teams else min(1, len(teams)-1)
            left, right = st.columns(2)
            home = left.selectbox("Gazdă", teams, index=home_default, key=f"match_home_{draft_id}")
            away = right.selectbox("Oaspeți", teams, index=away_default, key=f"match_away_{draft_id}")
            round_no = st.number_input("Etapa (lasă 0 dacă nu se aplică)", min_value=0,
                value=int(scheduled.get("etapa") or 0) if scheduled else 0, step=1,
                key=f"match_round_{draft_id}")
            entry_mode = st.radio("Cum se încheie meciul?", ["Introduc evenimentele", "Victorie la masa verde (3–0)"],
                                  horizontal=True, key=f"match_mode_{draft_id}")
            walkover = entry_mode.startswith("Victorie")
            winner = reason = None
            if walkover:
                winner = st.selectbox("Câștigătoare", [home, away], key=f"match_winner_{draft_id}")
                reason = st.text_input("Motivul (opțional)", key=f"match_reason_{draft_id}")
                st.info(f"Rezultatul va fi {winner} 3–0.")
                events = []
            elif home != away:
                events = render_match_event_entry(data, home, away, draft_id)
            else:
                events = []
                st.warning("Alege două echipe diferite pentru a introduce evenimentele.")
            save_match = st.button("Salvează meciul", type="primary", key=f"save_match_{draft_id}")
            if save_match:
                if home == away:
                    st.error("Gazda și oaspeții trebuie să fie echipe diferite.")
                else:
                    match = build_match(home, away, events, int(round_no) or None,
                                        winner if walkover else None, reason or "")
                    apply_match(data, match)
                    if scheduled:
                        scheduled["e1"], scheduled["e2"] = home, away
                        scheduled["etapa"], scheduled["meci_id"] = match.get("etapa"), match["id"]
                    st.session_state.pop(f"match_draft_{draft_id}", None)
                    save_league(path, data); st.success("Meci salvat."); st.rerun()
        if data["istoric_meciuri"]:
            st.subheader("Rezultate")
            render_cards([{"Etapa": m.get("etapa") or "–", "Gazdă": m["e1"],
                           "Scor": f"{m['goluri_e1']} – {m['goluri_e2']}", "Oaspeți": m["e2"],
                           "Masa verde": "Da" if m.get("masa_verde") else ""}
                          for m in ordered_by_stage(data["istoric_meciuri"])])
            with st.expander("Editează un rezultat"):
                match_to_edit = st.selectbox("Meci de editat", data["istoric_meciuri"],
                    format_func=lambda m: f"{m.get('etapa') or '–'} · {m['e1']} {m['goluri_e1']}–{m['goluri_e2']} {m['e2']}",
                    key="match_to_edit")
                teams_for_edit = list(data["echipe"])
                original_events = match_to_edit.get("evenimente", [])
                with st.form("edit_match_form"):
                    ec1, ec2 = st.columns(2)
                    edited_home = ec1.selectbox("Gazdă", teams_for_edit,
                        index=teams_for_edit.index(match_to_edit["e1"]) if match_to_edit["e1"] in teams_for_edit else 0)
                    edited_away = ec2.selectbox("Oaspeți", teams_for_edit,
                        index=teams_for_edit.index(match_to_edit["e2"]) if match_to_edit["e2"] in teams_for_edit else min(1, len(teams_for_edit)-1))
                    edited_round = st.number_input("Etapa", min_value=0,
                        value=int(match_to_edit.get("etapa") or 0), step=1)
                    save_edit = st.form_submit_button("Salvează modificările")
                edited_events = render_match_event_entry(data, edited_home, edited_away,
                    f"edit_{match_to_edit['id']}", initial_events=original_events)
                if save_edit:
                    if edited_home == edited_away:
                        st.error("Alege două echipe diferite.")
                    else:
                        new_events, invalid = [], False
                        for row in edited_events:
                            player_name = str(row.get("jucator", "")).strip()
                            if not player_name:
                                continue
                            if row.get("echipa") not in (edited_home, edited_away):
                                st.error("Evenimentul trebuie să aparțină uneia dintre echipe."); invalid = True; break
                            assist_name = row.get("asist") or None
                            if assist_name == player_name:
                                st.error("Marcatorul nu poate să-și dea assist lui însuși."); invalid = True; break
                            new_events.append({"echipa": row["echipa"],
                                "minut": int(row.get("minut", 1)),
                                "tip": row.get("tip", TIPURI_EVENIMENT[0]),
                                "jucator": player_name, "asist": assist_name})
                        if not invalid:
                            old_index = data["istoric_meciuri"].index(match_to_edit)
                            old_id = match_to_edit["id"]
                            data["istoric_meciuri"].pop(old_index)
                            rebuild_stats(data)
                            corrected = build_match(edited_home, edited_away, new_events,
                                int(edited_round) or None, walkover=match_to_edit.get("masa_verde"),
                                reason=match_to_edit.get("motiv_mv", ""))
                            corrected["id"] = old_id
                            apply_match(data, corrected)
                            data["istoric_meciuri"].insert(old_index, data["istoric_meciuri"].pop())
                            for fixture in data["program"]:
                                if fixture.get("meci_id") == old_id:
                                    fixture["e1"], fixture["e2"] = corrected["e1"], corrected["e2"]
                                    fixture["etapa"] = corrected.get("etapa")
                            save_league(path, data); st.success("Rezultatul a fost corectat."); st.rerun()
            with st.expander("Anulează un rezultat"):
                selected = st.selectbox("Meci", data["istoric_meciuri"],
                    format_func=lambda m: f"{m.get('etapa') or '–'} · {m['e1']} {m['goluri_e1']}–{m['goluri_e2']} {m['e2']}")
                if st.button("Anulează meciul selectat", type="secondary"):
                    data["istoric_meciuri"].remove(selected)
                    for fixture in data["program"]:
                        if fixture.get("meci_id") == selected.get("id"):
                            fixture["meci_id"] = None
                    rebuild_stats(data)
                    save_league(path, data); st.rerun()

    if page == "Meciuri și program":
        st.subheader("Program")
        if len(data["echipe"]) < 2:
            st.info("Adaugă cel puțin două echipe pentru a genera programul.")
        else:
            with st.form("gen_program"):
                twice = st.checkbox("Tur și retur")
                make_schedule = st.form_submit_button("Generează programul")
            if make_schedule:
                data["program"] = generate_rounds(list(data["echipe"]), twice)
                save_league(path, data); st.rerun()
            with st.expander("Adaugă manual un meci în program"):
                with st.form("fixture_manual"):
                    fc1, fc2, fc3, fc4 = st.columns([1, 2, 2, 2])
                    stage = fc1.number_input("Etapa", min_value=1, step=1, key="manual_stage")
                    fixture_home = fc2.selectbox("Gazdă", list(data["echipe"]), key="manual_home")
                    fixture_away = fc3.selectbox("Oaspeți", list(data["echipe"]), index=1, key="manual_away")
                    fixture_date = fc4.text_input("Data", placeholder="ZZ.LL.AAAA")
                    add_fixture = st.form_submit_button("Adaugă în program")
                if add_fixture:
                    if fixture_home == fixture_away:
                        st.error("Alege două echipe diferite.")
                    else:
                        data["program"].append({"id": uuid.uuid4().hex[:8], "etapa": int(stage),
                            "e1": fixture_home, "e2": fixture_away, "data": fixture_date.strip(), "meci_id": None})
                        save_league(path, data); st.success("Meciul a fost adăugat în program."); st.rerun()
        if data["program"]:
            render_cards([{"Etapa": f.get("etapa"), "Gazdă": f.get("e1"),
                           "Oaspeți": f.get("e2"), "Data": f.get("data", ""),
                           "Status": "Jucat" if f.get("meci_id") else "Programat"}
                          for f in ordered_by_stage(data["program"])])
            if st.button("Șterge programul"):
                data["program"] = []; save_league(path, data); st.rerun()

    if page == "Cupa":
        st.subheader("Cupa")
        st.caption("Alege o cupă, urmărește meciurile pe runde și înregistrează rezultatul unui singur meci odată.")
        teams = list(data["echipe"])
        cups = [c for c in data.get("cupe", []) if not c.get("super")]
        with st.expander("➕ Creează o cupă nouă", expanded=not cups):
            if len(teams) < 2:
                st.info("Ai nevoie de cel puțin două echipe în ligă.")
            else:
                with st.form("creare_cupa"):
                    cup_name = st.text_input("Numele cupei", f"Cupa {data['nume_liga']}")
                    participants = st.multiselect("Echipe participante", teams, default=teams)
                    st.caption("Tragerea la sorți se face automat. Dacă numărul echipelor nu se potrivește tabloului, unele primesc tur liber.")
                    create_cup = st.form_submit_button("Creează cupa", type="primary")
                if create_cup:
                    if len(participants) < 2:
                        st.error("Alege cel puțin două echipe.")
                    elif any(str(c.get("nume") or "").strip().casefold() ==
                             (cup_name.strip() or "Cupa").casefold() for c in cups):
                        st.error("Există deja o cupă cu acest nume. Alege-o din lista cupelor, nu o crea din nou.")
                    else:
                        new_cup = make_cup(participants, cup_name.strip() or "Cupa")
                        data.setdefault("cupe", []).append(new_cup)
                        st.session_state["cup_select_after_create"] = new_cup["id"]
                        save_league(path, data); st.rerun()

        cups = [c for c in data.get("cupe", []) if not c.get("super")]
        if not cups:
            st.info("Creează o cupă ca să vezi tabloul și să introduci rezultatele.")
        else:
            cups_by_id = {item["id"]: item for item in cups}
            cup_ids = list(cups_by_id)
            cup_numbers = {cup_id: index + 1 for index, cup_id in enumerate(cup_ids)}
            cup_picker_key = "active_regular_cup_" + hashlib.sha1(
                "|".join(cup_ids).encode("utf-8")).hexdigest()[:10]
            select_after_create = st.session_state.pop("cup_select_after_create", None)
            if select_after_create in cups_by_id:
                st.session_state[cup_picker_key] = select_after_create
            selected_cup_id = st.selectbox("Alege cupa de administrat", cup_ids,
                format_func=lambda cup_id: f"Cupa {cup_numbers[cup_id]} · {cups_by_id[cup_id]['nume']} · {cups_by_id[cup_id].get('status', 'în desfășurare')}",
                key=cup_picker_key)
            cup = cups_by_id[selected_cup_id]
            rounds = cup.get("runde", [])
            pending = [(ri, mi, slot) for ri, round_data in enumerate(rounds)
                       for mi, slot in enumerate(round_data.get("meciuri", []))
                       if slot.get("e1") and slot.get("e2") and not slot.get("meci")]
            played_count = sum(1 for round_data in rounds for slot in round_data.get("meciuri", [])
                               if slot.get("meci"))
            total_games = max(1, len(cup.get("echipe", [])) - 1)
            info_cols = st.columns(3)
            info_cols[0].metric("Echipe", len(cup.get("echipe", [])))
            info_cols[1].metric("Meciuri jucate", f"{played_count} / {total_games}")
            info_cols[2].metric("Runde", len(rounds))
            st.progress(min(1.0, played_count / total_games), text="Progresul cupei")
            if cup.get("castigatoare"):
                st.success(f"🏆 {cup['castigatoare']} a câștigat {cup['nume']}!")

            with st.expander("Setări cupă și ștergere"):
                source_supercup_exists = any(
                    item.get("super") and item.get("sursa_cupa") == cup["id"]
                    for item in data.get("cupe", []))
                st.caption("Ștergerea elimină această cupă și statisticile obținute în meciurile ei."
                           + (" Supercupa creată din ea rămâne în istoricul competițiilor." if source_supercup_exists else ""))
                if st.button("Șterge această cupă", type="secondary", key=f"start_delete_cup_{cup['id']}"):
                    st.session_state["cup_delete_pending"] = cup["id"]
                    st.rerun()
                if st.session_state.get("cup_delete_pending") == cup["id"]:
                    st.warning(f"Confirmi ștergerea cupei «{cup['nume']}»? Acțiunea nu poate fi anulată.")
                    confirm_col, cancel_col = st.columns(2)
                    if confirm_col.button("Da, șterge cupa", type="primary", key=f"confirm_delete_cup_{cup['id']}"):
                        for round_data in cup.get("runde", []):
                            for slot in round_data.get("meciuri", []):
                                old_match = slot.get("meci")
                                if old_match:
                                    apply_player_stats(data, old_match["e1"], old_match.get("mod_e1", {}), -1)
                                    apply_player_stats(data, old_match["e2"], old_match.get("mod_e2", {}), -1)
                        data["cupe"] = [item for item in data.get("cupe", []) if item.get("id") != cup["id"]]
                        data.get("premii_alese", {}).pop(f"cupa:{cup['id']}", None)
                        for state_key in list(st.session_state):
                            if state_key.startswith(f"match_draft_cup_{cup['id']}_"):
                                st.session_state.pop(state_key, None)
                        st.session_state.pop("cup_delete_pending", None)
                        save_league(path, data)
                        st.success("Cupa a fost ștearsă.")
                        st.rerun()
                    if cancel_col.button("Păstrează cupa", key=f"cancel_delete_cup_{cup['id']}"):
                        st.session_state.pop("cup_delete_pending", None)
                        st.rerun()

            next_round = pending[0][0] if pending else None
            for ri, round_data in enumerate(rounds):
                round_slots = round_data.get("meciuri", [])
                finished = sum(1 for slot in round_slots if slot.get("castigator"))
                with st.expander(f"{round_data.get('nume', f'Runda {ri + 1}')}  ·  {finished}/{len(round_slots)} decise",
                                 expanded=(ri == next_round)):
                    for mi, slot in enumerate(round_slots):
                        home_cup, away_cup = slot.get("e1"), slot.get("e2")
                        with st.container(border=True):
                            st.caption(f"Meciul {mi + 1}")
                            played = slot.get("meci")
                            if played:
                                penalty_note = " · decis la penaltyuri" if slot.get("penalti") else ""
                                st.markdown(f"**{played['e1']}  {played['goluri_e1']} – {played['goluri_e2']}  {played['e2']}**")
                                st.caption(f"Se califică {slot.get('castigator')}{penalty_note}.")
                                if st.button("Anulează acest rezultat și rundele următoare",
                                    key=f"cup_undo_{cup['id']}_{ri}_{mi}"):
                                    for old_match in clear_cup_result(cup, ri, mi):
                                        apply_player_stats(data, old_match["e1"], old_match.get("mod_e1", {}), -1)
                                        apply_player_stats(data, old_match["e2"], old_match.get("mod_e2", {}), -1)
                                    save_league(path, data); st.rerun()
                            elif slot.get("castigator"):
                                st.markdown(f"**{slot['castigator']}** avansează cu tur liber.")
                            elif home_cup and away_cup:
                                st.markdown(f"**{home_cup} — {away_cup}**")
                                st.caption("Meci de jucat")
                            else:
                                st.markdown(f"**{home_cup or 'Echipa 1'} — {away_cup or 'Echipa 2'}**")
                                st.caption("Echipele se stabilesc după runda anterioară.")

            st.markdown("### Înregistrează un rezultat")
            if pending:
                pending_ids = "_".join(slot.get("id", f"{ri}-{mi}") for ri, mi, slot in pending)
                selected_match = st.selectbox("Alege meciul", pending,
                    format_func=lambda item: f"{rounds[item[0]].get('nume', 'Runda')} · {item[2]['e1']} — {item[2]['e2']}",
                    key=f"cup_pending_{cup['id']}_{pending_ids}")
                ri, mi, slot = selected_match
                home_cup, away_cup = slot["e1"], slot["e2"]
                st.info("Adaugă golurile și celelalte evenimente. Dacă scorul este egal, alegi câștigătoarea la penaltyuri.")
                penalty_winner = st.selectbox("Câștigătoare la egalitate", [home_cup, away_cup],
                    key=f"cpw_{cup['id']}_{ri}_{mi}")
                result_events = render_match_event_entry(data, home_cup, away_cup,
                    f"cup_{cup['id']}_{ri}_{mi}")
                if st.button("Salvează rezultatul și califică echipa", type="primary",
                             key=f"save_cup_match_{cup['id']}_{ri}_{mi}"):
                    cup_match = build_match(home_cup, away_cup, result_events)
                    tied = cup_match["goluri_e1"] == cup_match["goluri_e2"]
                    winner_name = penalty_winner if tied else (
                        home_cup if cup_match["goluri_e1"] > cup_match["goluri_e2"] else away_cup)
                    slot["meci"], slot["castigator"], slot["penalti"] = cup_match, winner_name, tied
                    apply_player_stats(data, home_cup, cup_match.get("mod_e1", {}))
                    apply_player_stats(data, away_cup, cup_match.get("mod_e2", {}))
                    advance_cup_winner(cup, ri, mi)
                    save_league(path, data); st.rerun()
            elif cup.get("castigatoare"):
                st.success("Toate rundele s-au încheiat. Cupa are câștigătoare.")
            else:
                st.info("Nu există încă un meci disponibil. Completează meciurile rundei curente ca să se stabilească următorii adversari.")

    if page == "Supercupa":
        st.subheader("Supercupa")
        st.caption("Finala se joacă între câștigătoarea unei cupe și campioana ligii. Dacă aceeași echipă câștigă ambele trofee, adversara este echipa de pe locul 2.")
        regular_cup_winners = [c for c in data.get("cupe", [])
                               if not c.get("super") and c.get("castigatoare")]
        if len(data.get("echipe", {})) < 2:
            st.info("Adaugă cel puțin două echipe în ligă înainte să creezi Supercupa.")
        elif not regular_cup_winners:
            st.info("Termină o cupă eliminatorie. Câștigătoarea ei va juca Supercupa.")
        else:
            with st.container(border=True):
                st.markdown("#### Creează Supercupa")
                with st.form("create_supercup"):
                    source_cup = st.selectbox("Alege cupa", regular_cup_winners,
                        format_func=lambda c: f"{c.get('nume', 'Cupa')} · câștigătoare: {c['castigatoare']}")
                    preview_a, preview_b, preview_reason = participanti_supercupa(data, source_cup)
                    if preview_a:
                        st.markdown(f"**Finală propusă:** {preview_a} — {preview_b}")
                        st.caption(f"{preview_reason}. Perecherea folosește clasamentul actual al ligii.")
                    confirm_current_ranking = st.checkbox("Confirm că folosesc clasamentul actual")
                    create_supercup = st.form_submit_button("Creează finala Supercupei", type="primary")
                if create_supercup:
                    team_a, team_b, reason = participanti_supercupa(data, source_cup)
                    if not team_a:
                        st.error(reason)
                    elif not confirm_current_ranking:
                        st.warning("Confirmă folosirea clasamentului actual pentru a continua.")
                    else:
                        existing_supercups = [c for c in data.get("cupe", []) if c.get("super")]
                        super_name = "Supercupa" if not existing_supercups else f"Supercupa {len(existing_supercups) + 1}"
                        while any(c.get("nume", "").casefold() == super_name.casefold() for c in data["cupe"]):
                            super_name += " II"
                        data["cupe"].append(make_supercup(super_name, team_a, team_b, source_cup.get("id")))
                        save_league(path, data)
                        st.success(f"{super_name}: {team_a} — {team_b} ({reason}).")
                        st.rerun()

        supercups = [c for c in data.get("cupe", []) if c.get("super")]
        if not supercups:
            st.caption("Supercupele create vor apărea aici.")
        else:
            selected_supercup = st.selectbox("Supercupa activă", supercups,
                format_func=lambda c: f"{c.get('nume', 'Supercupa')} · {c.get('status', 'în desfășurare')}",
                key="active_supercup")
            if selected_supercup.get("castigatoare"):
                st.success(f"🏆 {selected_supercup['castigatoare']} a câștigat {selected_supercup['nume']}!")
            rounds = selected_supercup.get("runde", [])
            if not rounds or not rounds[0].get("meciuri"):
                st.info("Această Supercupă nu are încă o finală configurată.")
            else:
                final_slot = rounds[0]["meciuri"][0]
                home_super, away_super = final_slot.get("e1"), final_slot.get("e2")
                with st.container(border=True):
                    st.markdown(f"#### Finala · {home_super or '—'} — {away_super or '—'}")
                    played_super = final_slot.get("meci")
                    if played_super:
                        penalty_note = " · decisă la penaltyuri" if final_slot.get("penalti") else ""
                        st.write(f"{played_super['goluri_e1']} – {played_super['goluri_e2']} · câștigă **{final_slot.get('castigator')}**{penalty_note}")
                        if st.button("Anulează rezultatul Supercupei", key=f"supercup_undo_{selected_supercup['id']}"):
                            for old_match in clear_cup_result(selected_supercup, 0, 0):
                                apply_player_stats(data, old_match["e1"], old_match.get("mod_e1", {}), -1)
                                apply_player_stats(data, old_match["e2"], old_match.get("mod_e2", {}), -1)
                            save_league(path, data); st.rerun()
                    elif home_super and away_super:
                        penalty_winner = st.selectbox("Câștigătoare la egalitate (penaltyuri)",
                            [home_super, away_super], key=f"supercup_penalty_{selected_supercup['id']}")
                        events = render_match_event_entry(data, home_super, away_super,
                            f"supercup_{selected_supercup['id']}")
                        save_final = st.button("Salvează rezultatul final", type="primary",
                            key=f"save_supercup_{selected_supercup['id']}")
                        if save_final:
                            final_match = build_match(home_super, away_super, events)
                            tied = final_match["goluri_e1"] == final_match["goluri_e2"]
                            winner = penalty_winner if tied else (home_super if final_match["goluri_e1"] > final_match["goluri_e2"] else away_super)
                            final_slot["meci"], final_slot["castigator"], final_slot["penalti"] = final_match, winner, tied
                            advance_cup_winner(selected_supercup, 0, 0)
                            apply_player_stats(data, home_super, final_match.get("mod_e1", {}))
                            apply_player_stats(data, away_super, final_match.get("mod_e2", {}))
                            save_league(path, data); st.rerun()

    if page == "Transferuri":
        st.subheader("Transferuri de jucători")
        team_names = list(data["echipe"])
        if len(team_names) < 2:
            st.info("Adaugă cel puțin două echipe pentru a face transferuri.")
        else:
            with st.form("transfer_jucator"):
                source = st.selectbox("Pleacă de la", team_names)
                available_players = list(data["echipe"][source]["jucatori"])
                if available_players:
                    transferred_player = st.selectbox("Jucător", available_players)
                    destination = st.selectbox("Merge la", [t for t in team_names if t != source])
                    new_player_name = st.text_input("Nume în lotul nou (opțional)")
                    make_transfer = st.form_submit_button("Transferă jucătorul")
                else:
                    transferred_player, destination, new_player_name, make_transfer = None, None, "", False
                    st.caption("Echipa aleasă nu are jucători în lot.")
            if make_transfer and transferred_player:
                try:
                    transfer_player(data, transferred_player, source, destination, new_player_name)
                    rebuild_stats(data)
                    save_league(path, data); st.success("Transferul a fost salvat."); st.rerun()
                except ValueError as exc:
                    st.error(str(exc))
        if data.get("transferuri"):
            st.markdown("#### Istoric transferuri")
            render_cards([{"Data": t.get("data", ""), "Jucător": t.get("nume_nou", t.get("jucator")),
                           "De la": t.get("de_la"), "La": t.get("la")} for t in reversed(data["transferuri"])],
                         )

    if page == "Statistici":
        st.subheader("Statistici jucători")
        st.caption("Alege un top, ca în aplicația principală. Valorile se actualizează după înregistrarea meciurilor.")
        stat_sections = (
            ("⚽ Marcatori", "goluri", "Goluri"),
            ("🎯 Asistenți", "asisturi", "Assisturi"),
            ("🟨 Galbene", "cartonase_galbene", "Galbene"),
            ("🟥 Roșii", "cartonase_rosii", "Roșii"),
        )
        stat_tabs = st.tabs([title for title, _, _ in stat_sections])
        for tab, (title, field, label) in zip(stat_tabs, stat_sections):
            with tab:
                rows = player_leaderboard(data, field, label)
                if rows:
                    render_cards(rows)
                else:
                    st.info("Încă nu există date pentru acest top.")

    if page == "Premii sezon":
        st.subheader("Premii de sezon")
        st.caption("Alegi tu câștigătorii. Clasamentul și statisticile sunt sugestii; premiile nu se acordă automat.")
        pending_fixtures = sum(1 for f in data.get("program", [])
                               if not f.get("meci_id") or f.get("meci_id") not in
                               {m.get("id") for m in data["istoric_meciuri"]})
        pending_cups = sum(1 for c in data.get("cupe", []) if not c.get("castigatoare"))
        if pending_fixtures or pending_cups:
            st.info(f"Sezonul este încă în desfășurare: {pending_fixtures} meciuri de ligă și {pending_cups} cupe fără câștigător. Poți acorda premiile oricând.")
        teams_ranked = ranking(data)
        player_rows = [(team_name, player, stats) for team_name, team in data["echipe"].items()
                       for player, stats in team.get("jucatori", {}).items()]
        player_rows.sort(key=lambda row: (row[1].casefold(), row[0].casefold()))
        award_options = [("", "")] + [(team_name, player) for team_name, player, _ in player_rows]

        def award_label(choice):
            team_name, player = choice
            if not player:
                return "— Neacordat —"
            stats = data["echipe"].get(team_name, {}).get("jucatori", {}).get(player, {})
            position = stats.get("pozitie")
            details = f" · ⚽ {stats.get('goluri', 0)} · 🎯 {stats.get('asisturi', 0)}"
            return f"{player} · {team_name}" + (f" · {position}" if position else "") + details

        suggestions = {"campioana": (teams_ranked[0]["Echipă"] if teams_ranked else "Nicio echipă încă")}
        def event_totals(matches):
            result = {}
            for played_match in matches:
                for event in played_match.get("evenimente", []):
                    player_name = event.get("jucator")
                    if not player_name or event.get("tip") not in TIPURI_GOL:
                        continue
                    key = (event.get("echipa") or "", player_name)
                    totals = result.setdefault(key, {"goluri": 0, "asisturi": 0})
                    totals["goluri"] += 1
                    assist_name = event.get("asist")
                    if assist_name:
                        result.setdefault((key[0], assist_name), {"goluri": 0, "asisturi": 0})["asisturi"] += 1
            return result

        league_events = event_totals(data.get("istoric_meciuri", []))
        cup_matches = [slot["meci"] for cup_data in data.get("cupe", []) if not cup_data.get("super")
                       for round_data in cup_data.get("runde", []) for slot in round_data.get("meciuri", [])
                       if slot.get("meci")]
        cup_events = event_totals(cup_matches)
        combined_events = {}
        for group in (league_events, cup_events,
                      event_totals([slot["meci"] for cup_data in data.get("cupe", []) if cup_data.get("super")
                                    for round_data in cup_data.get("runde", []) for slot in round_data.get("meciuri", [])
                                    if slot.get("meci")])):
            for player_key, numbers in group.items():
                total = combined_events.setdefault(player_key, {"goluri": 0, "asisturi": 0})
                total["goluri"] += numbers["goluri"]
                total["asisturi"] += numbers["asisturi"]

        def leader_text(totals, metric, score=None):
            scores = {key: (score(value) if score else value[metric]) for key, value in totals.items()}
            best = max(scores.values(), default=0)
            if best <= 0:
                return ""
            winners = [f"{player} · {team}" for (team, player), value in scores.items() if value == best]
            return f"{' / '.join(sorted(winners))} ({best})"

        goal_hint = leader_text(league_events, "goluri")
        cup_goal_hint = leader_text(cup_events, "goluri")
        ballon_hint = leader_text(combined_events, "goluri", lambda value: value["goluri"] * 2 + value["asisturi"])
        if goal_hint:
            suggestions["gheata_liga"] = goal_hint + " goluri"
        if cup_goal_hint:
            suggestions["gheata_cupa"] = cup_goal_hint + " goluri"
        if ballon_hint:
            suggestions["balon"] = ballon_hint + " puncte · 2/gol + 1/assist"
        for cup_item in data.get("cupe", []):
            if cup_item.get("castigatoare"):
                suggestions[f"cupa:{cup_item.get('id')}"] = f"{cup_item['castigatoare']} (câștigătoare)"

        for award_index, award in enumerate(definitii_premii(data)):
            current = data.get("premii_alese", {}).get(award["cheie"], {})
            with st.container(border=True):
                st.markdown(f"#### {award['titlu']}")
                suggestion = suggestions.get(award["cheie"])
                if suggestion:
                    st.caption(f"Sugestie din datele actuale: {suggestion}")
                if award["tip"] == "echipa":
                    candidates = ["— Neacordat —", *sorted(data["echipe"], key=str.casefold)]
                    existing = current.get("echipa", "")
                    default_index = candidates.index(existing) if existing in candidates else 0
                    with st.form(f"award_form_{award_index}_{safe_slug(award['cheie'])}"):
                        winner = st.selectbox("Câștigătoare", candidates, index=default_index,
                            key=f"award_team_{award_index}_{safe_slug(award['cheie'])}")
                        save_award = st.form_submit_button("Salvează alegerea", type="primary")
                    chosen_value = {"echipa": "" if winner == "— Neacordat —" else winner, "jucator": ""}
                else:
                    ordered = list(award_options)
                    target_position = award.get("poz")
                    if target_position:
                        ordered = [ordered[0]] + sorted(ordered[1:], key=lambda choice:
                            (0 if target_position in str(data["echipe"].get(choice[0], {}).get("jucatori", {}).get(choice[1], {}).get("pozitie", "")).casefold() else 1,
                             award_label(choice).casefold()))
                    current_choice = (current.get("echipa", ""), current.get("jucator", ""))
                    default_index = ordered.index(current_choice) if current_choice in ordered else 0
                    with st.form(f"award_form_{award_index}_{safe_slug(award['cheie'])}"):
                        winner = st.selectbox("Câștigător", ordered, index=default_index,
                            format_func=award_label, key=f"award_player_{award_index}_{safe_slug(award['cheie'])}",
                            disabled=len(ordered) == 1)
                        save_award = st.form_submit_button("Salvează alegerea", type="primary", disabled=len(ordered) == 1)
                    chosen_value = {"echipa": winner[0], "jucator": winner[1]}
                if save_award:
                    data.setdefault("premii_alese", {})[award["cheie"]] = {
                        **chosen_value, "modificat": int(dt.datetime.now().timestamp() * 1000)}
                    save_league(path, data)
                    st.success("Premiul a fost salvat.")
                    st.rerun()

    if page == "Membri":
        st.subheader("Membri și acces la ligă")
        if role != "owner":
            st.info("Doar proprietarul ligii poate administra accesul membrilor.")
            st.write(f"Proprietar: **@{owner}** · Rolul tău: **{'Editor' if role == 'editor' else 'Vizitator'}**")
        else:
            previous_codes = data.get("coduri_invitat", {})
            previous_codes = copy.deepcopy(previous_codes) if isinstance(previous_codes, dict) else {}
            codes = data["coduri_invitat"] = copy.deepcopy(previous_codes)
            if not codes.get("spectator"):
                codes["spectator"] = new_access_code()
            if not codes.get("editor"):
                codes["editor"] = new_access_code()
            if codes != previous_codes:
                save_league(path, data)
            st.markdown("#### Coduri de acces pentru această ligă")
            st.caption("Codurile sunt aceleași pentru toți invitații. Le poți copia o singură dată și le poți schimba oricând.")
            code_col1, code_col2 = st.columns(2, gap="large")
            for col, code_type, title, description in (
                    (code_col1, "spectator", "👁 Cod spectator", "Invitatul alege dacă este jucător sau doar spectator."),
                    (code_col2, "editor", "✏️ Cod editor", "Invitatul intră direct și poate modifica liga.")):
                with col:
                    with st.container(border=True):
                        st.markdown(f"### {title}")
                        st.code(codes[code_type], language=None)
                        st.caption(description)
                        if st.button("Generează cod nou", key=f"rotate_{code_type}"):
                            data["coduri_invitat"][code_type] = new_access_code()
                            save_league(path, data)
                            st.rerun()
            st.info("Invitații introduc codul pe ecranul de autentificare. Schimbarea unui cod dezactivează imediat codul vechi.")

            st.divider()
            st.markdown("#### Acordă acces unui cont existent")
            data.setdefault("membri", [])
            existing = {m.get("username", "").casefold() for m in data["membri"]}
            candidates = sorted(k for k in load_users() if k != username and k not in existing)
            if candidates:
                with st.form("invite_account"):
                    invite_username = st.selectbox("Cont de invitat", candidates)
                    invite_role = st.selectbox("Drepturi", ["editor", "vizitator"],
                        format_func=lambda r: "Editor · poate modifica liga" if r == "editor" else "Vizitator · doar vizualizare")
                    invite_type = st.selectbox("Tip membru", ["spectator", "jucator"],
                        format_func=lambda kind: "Spectator" if kind == "spectator" else "Jucător")
                    invite = st.form_submit_button("Adaugă membrul")
                if invite:
                    data["membri"].append({"username": invite_username, "rol": invite_role,
                        "tip": invite_type, "activ": True,
                        "creat": dt.datetime.now().strftime("%d.%m.%Y %H:%M")})
                    save_league(path, data); st.success(f"@{invite_username} are acces la ligă."); st.rerun()
            else:
                st.caption("Nu există alte conturi disponibile pentru invitație. Persoana trebuie să-și creeze întâi un cont.")
            if data["membri"]:
                st.markdown("#### Acces acordat")
                for index, member in enumerate(list(data["membri"])):
                    member_name = member.get("username", "?")
                    with st.container(border=True):
                        m1, m2, m3 = st.columns([2, 2, 1])
                        m1.markdown(f"**@{member_name}** · {'Jucător' if member.get('tip') == 'jucator' else 'Spectator'}")
                        new_role = m2.selectbox("Rol", ["editor", "vizitator"],
                            index=0 if member.get("rol") == "editor" else 1,
                            format_func=lambda r: "Editor" if r == "editor" else "Vizitator",
                            key=f"member_role_{index}_{member_name}")
                        if m2.button("Salvează rolul", key=f"save_role_{index}_{member_name}"):
                            next(m for m in data["membri"] if m.get("username") == member_name)["rol"] = new_role
                            save_league(path, data); st.success("Rol actualizat."); st.rerun()
                        if m3.button("Revocă", key=f"revoke_{index}_{member_name}"):
                            data["membri"] = [m for m in data["membri"] if m.get("username") != member_name]
                            save_league(path, data); st.success("Acces revocat."); st.rerun()
                        linked = load_users().get(member_name, {}).get("selectii_ligi", {}).get(league_key(selected_entry))
                        if linked:
                            st.caption(f"Alegerea profilului: {linked.get('echipa')} · {linked.get('jucator')} ({linked.get('pozitie') or 'poziție nespecificată'})")
            else:
                st.info("Nu ai partajat această ligă cu niciun cont încă.")

    if page == "Profil":
        st.subheader("Profil personal")
        birthday_value = dt.date(2000, 1, 1)
        try:
            birthday_value = dt.datetime.strptime(profile.get("data_nasterii", ""), "%d.%m.%Y").date()
        except (ValueError, TypeError):
            pass
        with st.form("profile_details"):
            display_name = st.text_input("Nume și prenume", value=profile.get("nume", username))
            account_email = st.text_input("Adresă de e-mail", value=profile.get("email", ""),
                                          help="După salvare, te vei putea conecta și cu această adresă.")
            birthday = st.date_input("Data nașterii", value=min(birthday_value, dt.date.today()), max_value=dt.date.today())
            professional = st.selectbox("Joci la un club profesionist?", ["Da", "Nu"],
                index=0 if profile.get("joaca_fotbal") == "Da" else 1)
            positions = ["Portar", "Fundaș", "Mijlocaș", "Atacant"]
            position = st.selectbox("Poziția ta", positions,
                index=positions.index(profile["pozitie"]) if profile.get("pozitie") in positions else 0)
            save_profile = st.form_submit_button("Salvează profilul")
        if save_profile:
            users = load_users()
            normalized_email = account_email.strip().casefold()
            email_in_use = any(user_key != username and
                str(user_record.get("email", "")).strip().casefold() == normalized_email
                for user_key, user_record in users.items()) if normalized_email else False
            if normalized_email and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", normalized_email):
                st.error("Introdu o adresă de e-mail validă.")
            elif email_in_use:
                st.error("Adresa aceasta este deja folosită de alt cont.")
            else:
                users[username].update({"nume": display_name.strip() or username,
                    "email": normalized_email,
                    "data_nasterii": birthday.strftime("%d.%m.%Y"),
                    "joaca_fotbal": professional, "pozitie": position})
                save_users(users); st.success("Profilul a fost salvat. Te poți conecta și cu e-mailul."); st.rerun()

        st.markdown("#### Parolă")
        with st.form("change_account_password"):
            old_password = st.text_input("Parola curentă", type="password")
            new_password = st.text_input("Parola nouă", type="password")
            new_password_confirm = st.text_input("Confirmă parola nouă", type="password")
            change_password = st.form_submit_button("Schimbă parola")
        if change_password:
            if not verify_password(profile, old_password):
                st.error("Parola curentă este greșită.")
            elif len(new_password) < 6:
                st.error("Parola nouă trebuie să aibă cel puțin 6 caractere.")
            elif new_password != new_password_confirm:
                st.error("Parolele noi nu coincid.")
            else:
                users = load_users()
                salt, digest = password_hash(new_password)
                users[username].update({"sare": salt, "hash": digest,
                    "iteratii": PASSWORD_ITERATIONS, "dispozitive": []})
                save_users(users); st.success("Parola a fost schimbată."); st.rerun()

        st.markdown("#### Alege-ți echipa și jucătorul")
        if paths:
            personal_league = st.selectbox("Liga", paths,
                format_func=lambda item: f"{load_league(item['path']).get('nume_liga', item['path'].stem)} · @{item['owner']}",
                key="profile_league")
            personal_data = load_league(personal_league["path"])
            personal_teams = list(personal_data["echipe"])
            if personal_teams:
                selected_key = league_key(personal_league)
                prior = profile.setdefault("selectii_ligi", {}).get(selected_key, {})
                with st.form("profile_team_link"):
                    selected_team = st.selectbox("Echipa", personal_teams,
                        index=personal_teams.index(prior["echipa"]) if prior.get("echipa") in personal_teams else 0)
                    player_options = list(personal_data["echipe"][selected_team].get("jucatori", {}))
                    if player_options:
                        selected_player = st.selectbox("Jucător din lot", player_options,
                            index=player_options.index(prior["jucator"]) if prior.get("jucator") in player_options else 0)
                    else:
                        selected_player = None
                        st.caption("Echipa nu are încă jucători în lot.")
                    save_link = st.form_submit_button("Salvează asocierea", disabled=not bool(player_options))
                if save_link and selected_player:
                    users = load_users()
                    users[username].setdefault("selectii_ligi", {})[selected_key] = {
                        "echipa": selected_team, "jucator": selected_player,
                        "pozitie": profile.get("pozitie", ""), "actualizat": dt.datetime.now().timestamp()}
                    save_users(users); st.success("Profilul a fost asociat jucătorului."); st.rerun()
            else:
                st.info("Adaugă echipe în ligă pentru a-ți asocia un jucător.")
        totals = dict(STATS_JUCATOR)
        associations = []
        for league_entry in paths:
            league_data = load_league(league_entry["path"])
            selection = (profile.get("selectii_ligi", {}).get(league_key(league_entry)) or
                         league_data.get("selectii_membri", {}).get(username))
            if not selection:
                continue
            team_name, player_name = selection.get("echipa"), selection.get("jucator")
            stats = league_data.get("echipe", {}).get(team_name, {}).get("jucatori", {}).get(player_name)
            if not stats:
                continue
            for stat in totals:
                totals[stat] += int(stats.get(stat, 0) or 0)
            associations.append((league_data.get("nume_liga", league_entry["path"].stem), team_name,
                                 player_name, stats, trofee_jucator(league_data, team_name, player_name)))
        st.markdown("#### Statisticile mele")
        mcols = st.columns(4)
        for col, title, field in zip(mcols, ("Goluri", "Assisturi", "Galbene", "Roșii"),
                                     ("goluri", "asisturi", "cartonase_galbene", "cartonase_rosii")):
            col.metric(title, totals[field])
        if associations:
            render_cards([{"Ligă": league, "Echipă": team, "Jucător": player,
                "Goluri": stats.get("goluri", 0), "Assisturi": stats.get("asisturi", 0),
                "Galbene": stats.get("cartonase_galbene", 0), "Roșii": stats.get("cartonase_rosii", 0),
                "Trofee": " · ".join(trophies) if trophies else "–"}
                for league, team, player, stats, trophies in associations])
        else:
            st.caption("Asociază un jucător cu profilul tău pentru a vedea statisticile personale.")

    if page == "Import / export":
        st.subheader("Import / export JSON")
        upload = st.file_uploader("Importă un fișier JSON de ligă", type=["json"], key="import_json")
        if upload and st.button("Importă peste liga activă"):
            try:
                imported = normalizeaza_date(json.loads(upload.getvalue().decode("utf-8")))
                save_league(path, imported); st.success("Liga a fost importată."); st.rerun()
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
                st.error(f"Fișierul nu este un JSON de ligă valid: {exc}")
        st.download_button("Descarcă liga activă", json.dumps(data, ensure_ascii=False, indent=2),
                           file_name=f"{safe_slug(data['nume_liga'])}.json", mime="application/json")
        st.caption("Datele sunt stocate în Supabase." if SUPABASE_ENABLED else
                   f"Mod local · date ligi: `{BASE_DIR}` · conturi: `{USERS_FILE}`. Pentru Streamlit Cloud configurează SUPABASE_URL și SUPABASE_SERVICE_ROLE_KEY.")


if __name__ == "__main__":
    main()

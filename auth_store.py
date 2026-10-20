import re
from datetime import datetime, timezone

from werkzeug.security import check_password_hash, generate_password_hash

from db import IntegrityError

USERNAME_RE = re.compile(r"^[a-zA-Z0-9_.]{3,30}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

def normalize_phone(raw):
    digits = re.sub(r"\D", "", str(raw or ""))
    if digits.startswith("00966"):
        digits = digits[5:]
    elif digits.startswith("966"):
        digits = digits[3:]
    if len(digits) == 9 and digits.startswith("5"):
        digits = "0" + digits
    if len(digits) == 10 and digits.startswith("05"):
        return digits
    return ""

def login_kind(raw):
    text = str(raw or "").strip()
    if not text:
        return "", ""
    if "@" in text:
        return "email", text.lower()
    phone = normalize_phone(text)
    if phone:
        return "phone", phone
    return "username", text.lower()

def valid_username(raw):
    name = str(raw or "").strip()
    if USERNAME_RE.fullmatch(name) is None:
        return ""
    if "@" in name or normalize_phone(name):
        return ""
    return name

def valid_password(raw):
    text = str(raw or "")
    if len(text) < 8 or len(text) > 128:
        return False
    return True

def clean_display(raw):
    name = " ".join(str(raw or "").split())
    if len(name) < 2 or len(name) > 40:
        return ""
    if "<" in name or ">" in name:
        return ""
    return name

def find_user(conn, kind, value):
    if kind == "email":
        return conn.execute("SELECT * FROM users WHERE email = %s", (value,)).fetchone()
    if kind == "phone":
        return conn.execute("SELECT * FROM users WHERE phone = %s", (value,)).fetchone()
    return conn.execute("SELECT * FROM users WHERE LOWER(username) = LOWER(%s)", (value,)).fetchone()

def register_user(conn, username, email, phone, password, display_name):
    user = valid_username(username)
    if not user:
        return None, "اسم المستخدم: 3 إلى 30 حرفًا، لاتيني وأرقام و _ و . فقط."
    if not valid_password(password):
        return None, "كلمة السر 8 أحرف على الأقل."
    label = clean_display(display_name) or user
    mail = str(email or "").strip().lower()
    if mail and EMAIL_RE.fullmatch(mail) is None:
        return None, "صيغة البريد غير صحيحة."
    mobile = normalize_phone(phone) if str(phone or "").strip() else ""
    if str(phone or "").strip() and not mobile:
        return None, "رقم الجوال بصيغة 05xxxxxxxx."
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        res = conn.execute(
            "INSERT INTO users (username, email, phone, password_hash, display_name, created_at) VALUES (%s, %s, %s, %s, %s, %s)",
            (user, mail or None, mobile or None, generate_password_hash(password), label, now),
        )
        return res.lastrowid, None
    except IntegrityError:
        row = conn.execute(
            "SELECT username, email, phone FROM users WHERE LOWER(username) = LOWER(%s) OR email <=> %s OR phone <=> %s",
            (user, mail or None, mobile or None),
        ).fetchone()
        if row is None:
            return None, "تعذر إنشاء الحساب."
        if row["username"].lower() == user.lower():
            return None, "اسم المستخدم محجوز."
        if mail and row["email"] and row["email"].lower() == mail:
            return None, "البريد مستخدم."
        if mobile and row["phone"] == mobile:
            return None, "رقم الجوال مستخدم."
        return None, "تعذر إنشاء الحساب."

def verify_login(conn, login_id, password):
    kind, value = login_kind(login_id)
    if not kind:
        return None, "general"
    row = find_user(conn, kind, value)
    if row is None or not check_password_hash(row["password_hash"], password):
        return None, "general"
    return row, None

def _demo():
    assert valid_username("ab") == ""
    assert valid_username("leader1") == "leader1"
    assert normalize_phone("966512345678") == "0512345678"
    assert login_kind("a@b.co")[0] == "email"
    assert login_kind("0512345678")[0] == "phone"
    assert valid_password("short") is False
    assert valid_password("secret12") is True
    print("auth ok")

if __name__ == "__main__":
    _demo()

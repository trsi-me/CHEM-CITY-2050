import logging
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from functools import wraps
from urllib.parse import quote

from flask import Flask, abort, flash, g, redirect, render_template, request, session, url_for
from werkzeug.exceptions import HTTPException

import auth_store
import game
from db import IntegrityError, init_db, open_mysql

BASE = os.path.dirname(os.path.abspath(__file__))
LOGIN_MAX_FAILS = 8

def load_env():
    path = os.path.join(BASE, ".env")
    if not os.path.isfile(path):
        key = secrets.token_hex(32)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("# تطبيق فلاسك: مفتاح الجلسة ومنفذ التشغيل على جهاز العرض\n")
            handle.write("FLASK_SECRET_KEY=" + key + "\n")
            handle.write("PORT=5000\n")
            handle.write("FLASK_DEBUG=0\n")
            handle.write("SESSION_SECURE=0\n\n")
            handle.write("# قاعدة البيانات: اتصال MySQL\n")
            handle.write("DB_HOST=127.0.0.1\n")
            handle.write("DB_PORT=3306\n")
            handle.write("DB_NAME=chem_city\n")
            handle.write("DB_USER=\n")
            handle.write("DB_PASSWORD=\n")
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            raw = line.strip()
            if not raw or raw.startswith("#") or "=" not in raw:
                continue
            key, value = raw.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())

load_env()
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
init_db()

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "").strip() or secrets.token_hex(32)
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("SESSION_SECURE", "0") == "1"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=14)
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024
app.config["TEMPLATES_AUTO_RELOAD"] = True

def csrf_token():
    token = session.get("csrf")
    if not token:
        token = secrets.token_hex(24)
        session["csrf"] = token
    return token

def csrf_ok():
    sent = request.form.get("csrf", "")
    saved = session.get("csrf", "")
    if not sent or not saved:
        return False
    return secrets.compare_digest(sent, saved)

def valid_sid(value):
    return len(value) == 32 and all(ch in "0123456789abcdef" for ch in value)

def get_db():
    if "db" not in g:
        g.db = open_mysql()
    return g.db

def current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    return get_db().execute("SELECT id, username, display_name, created_at FROM users WHERE id = %s", (uid,)).fetchone()

def login_user(user_id, remember):
    session.clear()
    session["user_id"] = user_id
    session["csrf"] = secrets.token_hex(24)
    session.permanent = bool(remember)

def login_blocked():
    return int(session.get("login_fails", 0)) >= LOGIN_MAX_FAILS

def bump_login_fail():
    session["login_fails"] = int(session.get("login_fails", 0)) + 1

def clear_login_fail():
    session.pop("login_fails", None)

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if current_user() is None:
            return redirect(url_for("login") + "?next=" + quote(request.path, safe=""))
        return view(*args, **kwargs)
    return wrapped

def owns_row(row):
    user = current_user()
    if user is None or row is None:
        return False
    return row["user_id"] == user["id"]

def load_decisions(sid):
    rows = get_db().execute("SELECT * FROM decisions WHERE session_id = %s ORDER BY stage", (sid,)).fetchall()
    items = []
    for row in rows:
        item = dict(row)
        item["stage_name"] = game.STAGES[game.ORDER[item["stage"] - 1]]["name"]
        items.append(item)
    return items

def steps_for(current):
    rows = []
    for index, stage_id in enumerate(game.ORDER, start=1):
        state = "todo"
        if index < current:
            state = "done"
        elif index == current:
            state = "now"
        rows.append({"name": game.STAGES[stage_id]["name"], "state": state})
    return rows

def meter_origin(city, decisions):
    score = game.sustainability(city["water"], city["air"], city["energy"])
    last = decisions[-1] if decisions else None
    if last:
        return {
            "score": score,
            "score_from": game.sustainability(last["water_before"], last["air_before"], last["energy_before"]),
            "water_from": last["water_before"],
            "air_from": last["air_before"],
            "energy_from": last["energy_before"],
            "budget_from": last["budget_before"],
            "last": last,
        }
    return {
        "score": score,
        "score_from": score,
        "water_from": city["water"],
        "air_from": city["air"],
        "energy_from": city["energy"],
        "budget_from": city["budget"],
        "last": None,
    }

@app.template_filter("ksa")
def ksa_filter(value):
    return game.format_ksa(value)

def user_stats(user_id):
    db = get_db()
    rows = db.execute(
        "SELECT water, air, energy, budget, start_budget, status FROM sessions WHERE user_id = %s",
        (user_id,),
    ).fetchall()
    total = len(rows)
    playing = 0
    done_n = 0
    spent = 0
    scores = []
    waters = []
    airs = []
    energies = []
    saved = 0
    partial = 0
    collapse = 0
    for row in rows:
        spent += int(row["start_budget"]) - int(row["budget"])
        if row["status"] == "play":
            playing += 1
            continue
        done_n += 1
        waters.append(int(row["water"]))
        airs.append(int(row["air"]))
        energies.append(int(row["energy"]))
        score = game.sustainability(row["water"], row["air"], row["energy"])
        scores.append(score)
        key = game.verdict({"water": row["water"], "air": row["air"], "energy": row["energy"]})[0]
        if key == "saved":
            saved += 1
        elif key == "partial":
            partial += 1
        else:
            collapse += 1
    quiz = db.execute(
        "SELECT COALESCE(SUM(d.quiz_ok), 0) AS hits, COUNT(d.id) AS total FROM decisions d INNER JOIN sessions s ON s.id = d.session_id WHERE s.user_id = %s",
        (user_id,),
    ).fetchone()
    def avg(values):
        if not values:
            return 0
        return int(round(sum(values) / len(values)))
    return {
        "total": total,
        "playing": playing,
        "done": done_n,
        "spent": spent,
        "avg_score": avg(scores),
        "best_score": max(scores) if scores else 0,
        "avg_water": avg(waters),
        "avg_air": avg(airs),
        "avg_energy": avg(energies),
        "saved": saved,
        "partial": partial,
        "collapse": collapse,
        "quiz_hits": int(quiz["hits"]),
        "quiz_total": int(quiz["total"]),
    }

@app.context_processor
def inject_nav():
    return {"nav_user": current_user(), "csrf": csrf_token(), "page": request.endpoint}

@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()

@app.after_request
def harden(resp):
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "same-origin"
    resp.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; base-uri 'self'; form-action 'self'"
    resp.headers["Server"] = "web"
    resp.headers.pop("X-Powered-By", None)
    if not request.path.startswith("/static/"):
        resp.headers["Cache-Control"] = "no-store"
    return resp

@app.get("/")
def home():
    city = game.new_state()
    score = game.sustainability(city["water"], city["air"], city["energy"])
    user = current_user()
    leader_default = user["display_name"] if user else ""
    return render_template("index.html", error=None, city=city, score=score, leader_default=leader_default)

@app.get("/register", endpoint="register")
def register_form():
    if current_user():
        return redirect(url_for("home"))
    return render_template("register.html", error=None)

@app.post("/register")
def register_post():
    if current_user():
        return redirect(url_for("home"))
    if not csrf_ok():
        return render_template("register.html", error="أعيدي إرسال النموذج."), 400
    password = request.form.get("password", "")
    password2 = request.form.get("password2", "")
    if password != password2:
        return render_template("register.html", error="كلمتا السر غير متطابقتين."), 400
    uid, err = auth_store.register_user(
        get_db(),
        request.form.get("username", ""),
        request.form.get("email", ""),
        request.form.get("phone", ""),
        password,
        request.form.get("display_name", ""),
    )
    if err:
        return render_template("register.html", error=err), 400
    get_db().commit()
    login_user(uid, False)
    return redirect(url_for("home"))

@app.get("/login", endpoint="login")
def login_form():
    if current_user():
        return redirect(url_for("home"))
    return render_template("login.html", error=None)

@app.post("/login")
def login_post():
    if current_user():
        return redirect(url_for("home"))
    if not csrf_ok():
        return render_template("login.html", error="أعيدي إرسال النموذج."), 400
    if login_blocked():
        return render_template("login.html", error="محاولات كثيرة. انتظري قليلًا ثم أعيدي المحاولة."), 429
    row, _kind = auth_store.verify_login(get_db(), request.form.get("login_id", ""), request.form.get("password", ""))
    if row is None:
        bump_login_fail()
        return render_template("login.html", error="بيانات الدخول غير صحيحة."), 401
    clear_login_fail()
    login_user(row["id"], request.form.get("remember") == "1")
    dest = request.args.get("next", "")
    if dest.startswith("/") and not dest.startswith("//"):
        return redirect(dest)
    return redirect(url_for("home"))

@app.post("/logout")
def logout():
    if csrf_ok():
        session.clear()
    return redirect(url_for("home"))

@app.get("/missions")
@login_required
def missions():
    user = current_user()
    rows = get_db().execute(
        "SELECT id, leader, created_at, stage, status, water, air, energy FROM sessions WHERE user_id = %s ORDER BY created_at DESC LIMIT 30",
        (user["id"],),
    ).fetchall()
    runs = []
    for row in rows:
        item = dict(row)
        item["score"] = game.sustainability(row["water"], row["air"], row["energy"])
        runs.append(item)
    return render_template("missions.html", runs=runs)

@app.get("/account", endpoint="account")
@login_required
def account():
    user = get_db().execute("SELECT id, username, display_name, created_at FROM users WHERE id = %s", (current_user()["id"],)).fetchone()
    return render_template("account.html", user=user, stats=user_stats(user["id"]))

@app.post("/start")
@login_required
def start():
    city = game.new_state()
    score = game.sustainability(city["water"], city["air"], city["energy"])
    user = current_user()
    try:
        if not csrf_ok():
            return render_template("index.html", error="أعيدي إرسال النموذج.", city=city, score=score, leader_default=user["display_name"]), 400
        leader = game.clean_leader(request.form.get("leader", "")) or user["display_name"]
        sid = uuid.uuid4().hex
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        get_db().execute(
            "INSERT INTO sessions (id, leader, created_at, water, air, energy, budget, start_water, start_air, start_energy, start_budget, stage, status, user_id) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 1, 'play', %s)",
            (sid, leader, now, city["water"], city["air"], city["energy"], city["budget"], city["water"], city["air"], city["energy"], city["budget"], user["id"]),
        )
        get_db().commit()
        return redirect(url_for("play", sid=sid))
    except HTTPException:
        raise
    except Exception:
        app.logger.exception("start")
        abort(500)

@app.get("/play/<sid>")
@login_required
def play(sid):
    if not valid_sid(sid):
        abort(404)
    try:
        row = get_db().execute("SELECT * FROM sessions WHERE id = %s", (sid,)).fetchone()
        if row is None or not owns_row(row):
            abort(404)
        if row["status"] != "play":
            return redirect(url_for("report", sid=sid))
        city = dict(row)
        decisions = load_decisions(sid)
        origin = meter_origin(city, decisions)
        stage = game.public_stage(game.ORDER[city["stage"] - 1], city["budget"])
        return render_template(
            "play.html",
            city=city,
            stage=stage,
            steps=steps_for(city["stage"]),
            pulse=game.pulse(city),
            **origin,
        )
    except HTTPException:
        raise
    except Exception:
        app.logger.exception("play")
        abort(500)

@app.post("/play/<sid>")
@login_required
def decide(sid):
    if not valid_sid(sid):
        abort(404)
    if not csrf_ok():
        flash("أعيدي إرسال النموذج.")
        return redirect(url_for("play", sid=sid))
    db = get_db()
    try:
        row = db.execute("SELECT * FROM sessions WHERE id = %s", (sid,)).fetchone()
        if row is None or not owns_row(row):
            abort(404)
        if row["status"] != "play" or row["stage"] > 3:
            return redirect(url_for("report", sid=sid))
        stage_id = game.ORDER[row["stage"] - 1]
        if request.form.get("stage", "") != stage_id:
            flash("انتهت هذه المرحلة. تابعي من اللوحة.")
            return redirect(url_for("play", sid=sid))
        state = {"water": row["water"], "air": row["air"], "energy": row["energy"], "budget": row["budget"]}
        nxt, decision, err = game.apply(state, stage_id, request.form.get("choice", ""), request.form.get("quiz", ""))
        if err == "budget":
            flash("هذا الحل يكلف أكثر من رصيد المدينة.")
            return redirect(url_for("play", sid=sid))
        if err:
            flash("اختاري إجابة وحلًا من هذه المرحلة.")
            return redirect(url_for("play", sid=sid))
        new_stage = row["stage"] + 1
        status = "done" if new_stage > 3 else "play"
        db.execute(
            "INSERT INTO decisions (session_id, stage, choice_id, choice_title, cost, quiz_ok, concept, quiz_concept, equation, explanation, quiz_note, water_before, air_before, energy_before, budget_before, water_after, air_after, energy_after, budget_after) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (
                sid, row["stage"], decision["choice_id"], decision["choice_title"], decision["cost"], decision["quiz_ok"],
                decision["concept"], decision["quiz_concept"], decision["equation"], decision["explanation"], decision["quiz_note"],
                state["water"], state["air"], state["energy"], state["budget"],
                nxt["water"], nxt["air"], nxt["energy"], nxt["budget"],
            ),
        )
        db.execute(
            "UPDATE sessions SET water = %s, air = %s, energy = %s, budget = %s, stage = %s, status = %s WHERE id = %s",
            (nxt["water"], nxt["air"], nxt["energy"], nxt["budget"], new_stage, status, sid),
        )
        db.commit()
    except HTTPException:
        raise
    except IntegrityError:
        db.rollback()
        flash("هذا القرار سُجّل من قبل.")
        return redirect(url_for("play", sid=sid))
    except Exception:
        db.rollback()
        app.logger.exception("decide")
        abort(500)
    if status == "done":
        return redirect(url_for("report", sid=sid))
    return redirect(url_for("play", sid=sid) + "#sim")

@app.get("/report/<sid>")
@login_required
def report(sid):
    if not valid_sid(sid):
        abort(404)
    try:
        row = get_db().execute("SELECT * FROM sessions WHERE id = %s", (sid,)).fetchone()
        if row is None or not owns_row(row):
            abort(404)
        if row["status"] != "done":
            return redirect(url_for("play", sid=sid))
        city = dict(row)
        decisions = load_decisions(sid)
        key, title, text, score = game.verdict(city)
        got, missed = game.concepts_of(decisions)
        hits = sum(1 for item in decisions if item["quiz_ok"])
        return render_template(
            "report.html",
            city=city,
            decisions=decisions,
            steps=steps_for(city["stage"]),
            verdict_key=key,
            verdict_title=title,
            verdict_text=text,
            score=score,
            before_score=game.sustainability(city["start_water"], city["start_air"], city["start_energy"]),
            got=got,
            missed=missed,
            hits=hits,
            used=city["start_budget"] - city["budget"],
            tips=game.recommendations(city),
            pulse=game.pulse(city),
        )
    except HTTPException:
        raise
    except Exception:
        app.logger.exception("report")
        abort(500)

@app.errorhandler(404)
def missing(_err):
    return render_template("error.html", title="الصفحة غير موجودة", text="ارجعي إلى مدخل المدينة."), 404

@app.errorhandler(500)
def failed(_err):
    return render_template("error.html", title="تعذر إكمال العملية", text="حدث خلل. أعيدي فتح الصفحة."), 500

if __name__ == "__main__":
    raw_port = os.environ.get("PORT", "5000").strip() or "5000"
    port = int(raw_port)
    app.run(host="0.0.0.0", port=port, debug=os.environ.get("FLASK_DEBUG", "0") == "1")

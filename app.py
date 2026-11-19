from functools import wraps

import mysql.connector
from flask import (Flask, flash, g, jsonify, redirect, render_template,
                    request, session, url_for)
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from werkzeug.security import check_password_hash, generate_password_hash

from config import DB_CONFIG, GOOGLE_CLIENT_ID, SECRET_KEY

app = Flask(__name__)
app.secret_key = SECRET_KEY


# ---------- DB helpers ----------

def get_db():
    if "db" not in g:
        g.db = mysql.connector.connect(**DB_CONFIG)
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def query(sql, params=None, fetch=True, commit=False):
    db = get_db()
    cur = db.cursor(dictionary=True)
    cur.execute(sql, params or ())
    result = cur.fetchall() if fetch else None
    if commit:
        db.commit()
    last_id = cur.lastrowid
    cur.close()
    return result, last_id


# ---------- Auth ----------

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "member_id" not in session:
            flash("Please log in first.", "error")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        full_name = request.form["full_name"].strip()
        email = request.form["email"].strip().lower()
        neighborhood = request.form["neighborhood"].strip()
        city = request.form["city"].strip()
        password = request.form["password"]

        if not all([full_name, email, neighborhood, city, password]):
            flash("All fields are required.", "error")
            return render_template("register.html")

        existing, _ = query("SELECT MemberID FROM Members WHERE Email = %s", (email,))
        if existing:
            flash("An account with that email already exists.", "error")
            return render_template("register.html")

        password_hash = generate_password_hash(password)
        _, member_id = query(
            """INSERT INTO Members (FullName, Neighborhood, City, TrustScore,
               JoinedDate, Email, PasswordHash)
               VALUES (%s, %s, %s, 5.00, CURDATE(), %s, %s)""",
            (full_name, neighborhood, city, email, password_hash),
            fetch=False, commit=True,
        )
        session["member_id"] = member_id
        session["full_name"] = full_name
        flash(f"Welcome to SwapShelf, {full_name}!", "success")
        return redirect(url_for("dashboard"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        rows, _ = query("SELECT * FROM Members WHERE Email = %s", (email,))
        member = rows[0] if rows else None

        if member and member["PasswordHash"] and check_password_hash(member["PasswordHash"], password):
            session["member_id"] = member["MemberID"]
            session["full_name"] = member["FullName"]
            return redirect(url_for("dashboard"))

        flash("Incorrect email or password.", "error")

    return render_template("login.html", google_client_id=GOOGLE_CLIENT_ID)


@app.route("/auth/google", methods=["POST"])
def auth_google():
    token = request.get_json(silent=True, force=True).get("credential", "")
    try:
        info = google_id_token.verify_oauth2_token(
            token, google_requests.Request(), GOOGLE_CLIENT_ID
        )
    except (ValueError, AttributeError):
        return jsonify({"error": "Could not verify that Google account."}), 400

    email = info["email"].lower()
    name = info.get("name", email.split("@")[0])

    rows, _ = query("SELECT * FROM Members WHERE Email = %s", (email,))
    if rows:
        member = rows[0]
        session["member_id"] = member["MemberID"]
        session["full_name"] = member["FullName"]
        return jsonify({"redirect": url_for("dashboard")})

    # First time we've seen this Google account: finish the profile first.
    session["pending_google"] = {"email": email, "name": name}
    return jsonify({"redirect": url_for("complete_google_signup")})


@app.route("/complete-signup", methods=["GET", "POST"])
def complete_google_signup():
    pending = session.get("pending_google")
    if not pending:
        return redirect(url_for("login"))

    if request.method == "POST":
        _, member_id = query(
            """INSERT INTO Members (FullName, Neighborhood, City, TrustScore,
               JoinedDate, Email, PasswordHash)
               VALUES (%s, %s, %s, 5.00, CURDATE(), %s, NULL)""",
            (pending["name"], request.form["neighborhood"].strip(),
             request.form["city"].strip(), pending["email"]),
            fetch=False, commit=True,
        )
        session.pop("pending_google", None)
        session["member_id"] = member_id
        session["full_name"] = pending["name"]
        flash(f"Welcome to SwapShelf, {pending['name']}!", "success")
        return redirect(url_for("dashboard"))

    return render_template("complete_signup.html", pending=pending)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------- Core pages ----------

@app.route("/")
def index():
    return redirect(url_for("dashboard") if "member_id" in session else url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    category = request.args.get("category", "")
    sql = """SELECT i.ItemID, i.Title, i.Category, i.ItemCondition, i.Notes,
                     m.FullName AS OwnerName, m.Neighborhood
              FROM Items i JOIN Members m ON i.OwnerID = m.MemberID
              WHERE i.Status = 'Available' AND i.OwnerID != %s"""
    params = [session["member_id"]]
    if category:
        sql += " AND i.Category = %s"
        params.append(category)
    sql += " ORDER BY i.ItemID DESC"
    items, _ = query(sql, params)

    categories, _ = query("SELECT DISTINCT Category FROM Items ORDER BY Category")
    my_items, _ = query(
        "SELECT ItemID, Title FROM Items WHERE OwnerID = %s AND Status = 'Available'",
        (session["member_id"],),
    )
    return render_template("dashboard.html", items=items, categories=categories, my_items=my_items)


@app.route("/items/add", methods=["GET", "POST"])
@login_required
def add_item():
    if request.method == "POST":
        query(
            """INSERT INTO Items (OwnerID, Title, Category, ItemCondition, Status, Notes)
               VALUES (%s, %s, %s, %s, 'Available', %s)""",
            (session["member_id"], request.form["title"].strip(),
             request.form["category"].strip(), request.form["condition"],
             request.form.get("notes", "").strip()),
            fetch=False, commit=True,
        )
        flash("Item added to your shelf.", "success")
        return redirect(url_for("my_items"))
    return render_template("add_item.html")


@app.route("/items/mine")
@login_required
def my_items():
    items, _ = query(
        "SELECT * FROM Items WHERE OwnerID = %s ORDER BY ItemID DESC",
        (session["member_id"],),
    )
    return render_template("my_items.html", items=items)


@app.route("/swap/request/<int:item_id>", methods=["POST"])
@login_required
def request_swap(item_id):
    offered_item_id = request.form.get("offered_item_id")
    if not offered_item_id:
        flash("Pick one of your own items to offer.", "error")
        return redirect(url_for("dashboard"))

    query(
        """INSERT INTO SwapRequests (RequesterID, OfferedItemID, RequestedItemID, RequestStatus, CreatedAt)
           VALUES (%s, %s, %s, 'Pending', NOW())""",
        (session["member_id"], offered_item_id, item_id),
        fetch=False, commit=True,
    )
    flash("Swap request sent.", "success")
    return redirect(url_for("dashboard"))


@app.route("/requests")
@login_required
def requests_view():
    mid = session["member_id"]
    incoming, _ = query(
        """SELECT sr.RequestID, sr.RequestStatus, sr.CreatedAt,
                  req_m.FullName AS RequesterName,
                  off_i.Title AS OfferedTitle, want_i.Title AS RequestedTitle
           FROM SwapRequests sr
           JOIN Items want_i ON sr.RequestedItemID = want_i.ItemID
           JOIN Items off_i ON sr.OfferedItemID = off_i.ItemID
           JOIN Members req_m ON sr.RequesterID = req_m.MemberID
           WHERE want_i.OwnerID = %s
           ORDER BY sr.CreatedAt DESC""",
        (mid,),
    )
    outgoing, _ = query(
        """SELECT sr.RequestID, sr.RequestStatus, sr.CreatedAt,
                  owner_m.FullName AS OwnerName,
                  off_i.Title AS OfferedTitle, want_i.Title AS RequestedTitle
           FROM SwapRequests sr
           JOIN Items want_i ON sr.RequestedItemID = want_i.ItemID
           JOIN Items off_i ON sr.OfferedItemID = off_i.ItemID
           JOIN Members owner_m ON want_i.OwnerID = owner_m.MemberID
           WHERE sr.RequesterID = %s
           ORDER BY sr.CreatedAt DESC""",
        (mid,),
    )
    return render_template("requests.html", incoming=incoming, outgoing=outgoing)


@app.route("/requests/<int:request_id>/<action>", methods=["POST"])
@login_required
def respond_request(request_id, action):
    if action not in ("accept", "reject"):
        flash("Unknown action.", "error")
        return redirect(url_for("requests_view"))

    rows, _ = query("SELECT * FROM SwapRequests WHERE RequestID = %s", (request_id,))
    if not rows:
        flash("Request not found.", "error")
        return redirect(url_for("requests_view"))
    req = rows[0]

    # Only the owner of the requested item may respond.
    owner_rows, _ = query("SELECT OwnerID FROM Items WHERE ItemID = %s", (req["RequestedItemID"],))
    if not owner_rows or owner_rows[0]["OwnerID"] != session["member_id"]:
        flash("You can't respond to that request.", "error")
        return redirect(url_for("requests_view"))

    new_status = "Accepted" if action == "accept" else "Rejected"
    query("UPDATE SwapRequests SET RequestStatus = %s WHERE RequestID = %s",
          (new_status, request_id), fetch=False, commit=True)

    if action == "accept":
        query("UPDATE Items SET Status = 'Swapped' WHERE ItemID IN (%s, %s)",
              (req["OfferedItemID"], req["RequestedItemID"]), fetch=False, commit=True)
        flash("Swap accepted! Both items are now marked Swapped.", "success")
    else:
        flash("Request rejected.", "success")

    return redirect(url_for("requests_view"))


if __name__ == "__main__":
    app.run(debug=True, port=5001)
# SwapShelf — setup on your Mac

Flask backend + MySQL (your existing `swapshelf_db`) + server-rendered
frontend (Jinja templates, no JS framework needed).

## 1. Open the project in VS Code

```bash
cd ~/Downloads/swapshelf_web   # wherever you unzip it
code .
```

(If `code` isn't a recognized command: in VS Code press **Cmd+Shift+P** →
type "Shell Command: Install 'code' command in PATH" → Enter.)

## 2. Create a virtual environment

In VS Code's integrated terminal (**Ctrl+`**):

```bash
python3 -m venv venv
source venv/bin/activate
pip3 install -r requirements.txt
```

VS Code will likely pop up "Select a Python Interpreter" — pick the one
at `./venv/bin/python`. (Or: **Cmd+Shift+P** → "Python: Select Interpreter".)

## 3. Update your database schema

You added columns for login in `schema_update.sql`. Run it once:

```bash
mysql -u root -p swapshelf_db < schema_update.sql
```

Your original 6 members are untouched but have no password — just
register fresh test accounts from the site itself (step 5).

## 4. Set your MySQL credentials

The app reads these from environment variables (see `config.py`).
In the same terminal:

```bash
export DB_USER="root"
export DB_PASSWORD="your_mysql_password"
export SECRET_KEY="anything-random-for-now"
```

Tip: to avoid retyping these every session, add them to `venv/bin/activate`
(paste the three `export` lines at the bottom of that file) so they load
automatically on `source venv/bin/activate`.

## 5. Run it

```bash
python3 app.py
```

Open **http://127.0.0.1:5000** → Register a new account → log in → browse,
add items, propose swaps, accept/reject requests.

## Project layout

```
swapshelf_web/
  app.py              Flask routes (auth, dashboard, items, swaps)
  config.py           DB connection + secret key (reads env vars)
  schema_update.sql   Adds Email/PasswordHash to Members
  requirements.txt
  templates/          Jinja HTML pages
  static/style.css
```

## Where to go next

- Passwords are hashed with Werkzeug (`generate_password_hash`) — never
  stored in plain text.
- There's no "edit item" or "delete item" route yet — easy to add next
  to `add_item` in `app.py` if you need it for the fest demo.
- `TrustScore` is set to a flat 5.00 on registration; wiring it up to
  react to completed swaps is a good next feature.

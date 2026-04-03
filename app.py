import base64
import importlib
import io
import os
from datetime import datetime
from urllib.parse import quote_plus

from flask import Flask, flash, redirect, render_template, request, url_for
from flask_login import (
    LoginManager,
    UserMixin,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash


app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-change-me")


def build_database_uri() -> str:
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        if database_url.startswith("mysql://"):
            return database_url.replace("mysql://", "mysql+pymysql://", 1)
        if database_url.startswith("mysql2://"):
            return database_url.replace("mysql2://", "mysql+pymysql://", 1)
        return database_url

    mysql_host = os.getenv("MYSQLHOST")
    mysql_port = os.getenv("MYSQLPORT", "3306")
    mysql_user = os.getenv("MYSQLUSER")
    mysql_password = os.getenv("MYSQLPASSWORD")
    mysql_database = os.getenv("MYSQLDATABASE")

    if all([mysql_host, mysql_user, mysql_password, mysql_database]):
        return (
            f"mysql+pymysql://{quote_plus(mysql_user)}:{quote_plus(mysql_password)}"
            f"@{mysql_host}:{mysql_port}/{mysql_database}"
        )

    railway_env = any(
        os.getenv(name)
        for name in (
            "RAILWAY_ENVIRONMENT",
            "RAILWAY_PROJECT_ID",
            "RAILWAY_SERVICE_ID",
            "RAILWAY_PUBLIC_DOMAIN",
            "RAILWAY_DEPLOYMENT_ID",
            "PORT",
        )
    )
    if railway_env:
        raise RuntimeError(
            "No Railway MySQL connection settings found. Set DATABASE_URL or MYSQLHOST/MYSQLPORT/MYSQLUSER/MYSQLPASSWORD/MYSQLDATABASE."
        )

    return "mysql+pymysql://root:@127.0.0.1:3306/ledger"


app.config["SQLALCHEMY_DATABASE_URI"] = build_database_uri()
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message_category = "warning"


@app.context_processor
def inject_asset_version():
    def asset_version(filename: str) -> str:
        path = os.path.join(app.static_folder, filename)
        try:
            return str(int(os.path.getmtime(path)))
        except OSError:
            return "1"

    return {"asset_version": asset_version}


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    transactions = db.relationship(
        "Transaction",
        backref="user",
        lazy=True,
        cascade="all, delete-orphan",
    )

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(20), nullable=False)  # income, expense, transfer
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(80), nullable=True)
    description = db.Column(db.String(255), nullable=True)
    transaction_date = db.Column(db.DateTime, nullable=False)
    from_account = db.Column(db.String(80), nullable=True)
    to_account = db.Column(db.String(80), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)


@login_manager.user_loader
def load_user(user_id: str):
    return db.session.get(User, int(user_id))


def parse_date(value: str):
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except (TypeError, ValueError):
        return None


def normalize_transaction_form(form):
    tx_type = form.get("type", "").strip().lower()
    amount_raw = form.get("amount", "").strip()
    category = form.get("category", "").strip() or None
    description = form.get("description", "").strip() or None
    date_raw = form.get("transaction_date", "").strip()
    from_account = form.get("from_account", "").strip() or None
    to_account = form.get("to_account", "").strip() or None

    if tx_type not in {"income", "expense", "transfer"}:
        return None, "Transaction type must be income, expense, or transfer."

    try:
        amount = float(amount_raw)
        if amount <= 0:
            raise ValueError
    except ValueError:
        return None, "Amount must be a positive number."

    tx_date = parse_date(date_raw)
    if tx_date is None:
        return None, "Date must be valid and formatted as YYYY-MM-DD."

    if tx_type == "transfer":
        if not from_account or not to_account:
            return None, "Transfers require both from and to account values."
        if from_account == to_account:
            return None, "Transfer accounts must be different."

    normalized = {
        "type": tx_type,
        "amount": amount,
        "category": category,
        "description": description,
        "transaction_date": tx_date,
        "from_account": from_account,
        "to_account": to_account,
    }
    return normalized, None


def compute_summary(transactions):
    income = sum(t.amount for t in transactions if t.type == "income")
    expense = sum(t.amount for t in transactions if t.type == "expense")
    transfers = sum(t.amount for t in transactions if t.type == "transfer")
    balance = income - expense
    return {
        "income": income,
        "expense": expense,
        "transfers": transfers,
        "balance": balance,
    }


def get_plotter():
    try:
        matplotlib = importlib.import_module("matplotlib")
        matplotlib.use("Agg")
        plt = importlib.import_module("matplotlib.pyplot")
        return plt
    except ModuleNotFoundError:
        return None


@app.route("/")
def index():
    if current_user.is_authenticated:
        txs = (
            Transaction.query.filter_by(user_id=current_user.id)
            .order_by(Transaction.transaction_date.desc())
            .all()
        )
        summary = compute_summary(txs)
        recent = txs[:5]
        return render_template("index.html", summary=summary, recent=recent)
    return render_template("index.html", summary=None, recent=[])


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("transactions"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if not username or not email or not password:
            flash("All fields are required.", "danger")
            return render_template("register.html")
        if password != confirm:
            flash("Passwords do not match.", "danger")
            return render_template("register.html")
        if len(password) < 6:
            flash("Password must be at least 6 characters.", "danger")
            return render_template("register.html")

        existing = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing:
            flash("Username or email already exists.", "danger")
            return render_template("register.html")

        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash("Registration successful. Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("transactions"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        remember = request.form.get("remember") == "on"

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user, remember=remember)
            flash("Welcome back!", "success")
            next_page = request.args.get("next")
            return redirect(next_page or url_for("transactions"))

        flash("Invalid email or password.", "danger")

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))


@app.route("/transactions")
@login_required
def transactions():
    txs = (
        Transaction.query.filter_by(user_id=current_user.id)
        .order_by(Transaction.transaction_date.desc(), Transaction.id.desc())
        .all()
    )
    summary = compute_summary(txs)
    return render_template("transactions.html", transactions=txs, summary=summary)


@app.route("/transactions/add", methods=["GET", "POST"])
@login_required
def add_transaction():
    if request.method == "POST":
        data, error = normalize_transaction_form(request.form)
        if error:
            flash(error, "danger")
            return render_template("transaction_form.html", transaction=None)

        tx = Transaction(user_id=current_user.id, **data)
        db.session.add(tx)
        db.session.commit()
        flash("Transaction added successfully.", "success")
        return redirect(url_for("transactions"))

    return render_template("transaction_form.html", transaction=None)


@app.route("/transactions/<int:transaction_id>/edit", methods=["GET", "POST"])
@login_required
def edit_transaction(transaction_id):
    tx = Transaction.query.filter_by(id=transaction_id, user_id=current_user.id).first_or_404()

    if request.method == "POST":
        data, error = normalize_transaction_form(request.form)
        if error:
            flash(error, "danger")
            return render_template("transaction_form.html", transaction=tx)

        tx.type = data["type"]
        tx.amount = data["amount"]
        tx.category = data["category"]
        tx.description = data["description"]
        tx.transaction_date = data["transaction_date"]
        tx.from_account = data["from_account"]
        tx.to_account = data["to_account"]

        db.session.commit()
        flash("Transaction updated.", "success")
        return redirect(url_for("transactions"))

    return render_template("transaction_form.html", transaction=tx)


@app.route("/transactions/<int:transaction_id>/delete", methods=["POST"])
@login_required
def delete_transaction(transaction_id):
    tx = Transaction.query.filter_by(id=transaction_id, user_id=current_user.id).first_or_404()
    db.session.delete(tx)
    db.session.commit()
    flash("Transaction deleted.", "info")
    return redirect(url_for("transactions"))


@app.route("/reports")
@login_required
def reports():
    txs = Transaction.query.filter_by(user_id=current_user.id).all()
    plt = get_plotter()
    matplotlib_available = plt is not None

    summary = compute_summary(txs)
    chart_url = None

    values = [summary["income"], summary["expense"], summary["transfers"]]
    labels = ["Income", "Expense", "Transfer"]
    colors = ["#3C9D5D", "#C94C4C", "#4B7BE5"]

    if matplotlib_available and any(v > 0 for v in values):
        fig, ax = plt.subplots(figsize=(5, 5))
        ax.pie(values, labels=labels, autopct="%1.1f%%", startangle=90, colors=colors)
        ax.axis("equal")
        ax.set_title("Money Flow Breakdown")

        img = io.BytesIO()
        plt.tight_layout()
        fig.savefig(img, format="png")
        plt.close(fig)
        img.seek(0)
        chart_url = base64.b64encode(img.getvalue()).decode("utf-8")

    return render_template(
        "report.html",
        summary=summary,
        chart_url=chart_url,
        matplotlib_available=matplotlib_available,
    )


@app.route("/profile")
@login_required
def profile():
    txs = Transaction.query.filter_by(user_id=current_user.id).all()
    summary = compute_summary(txs)
    tx_count = len(txs)
    recent = (
        Transaction.query.filter_by(user_id=current_user.id)
        .order_by(Transaction.transaction_date.desc(), Transaction.id.desc())
        .limit(5)
        .all()
    )
    return render_template(
        "profile.html",
        summary=summary,
        tx_count=tx_count,
        recent=recent,
    )


with app.app_context():
    db.create_all()


if __name__ == "__main__":
    app.run(debug=True)

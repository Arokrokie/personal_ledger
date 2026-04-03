# Personal Finance Ledger

A Flask web application for tracking personal income, expenses, and transfers. The project uses Flask-Login for authentication, Flask-SQLAlchemy for persistence, MySQL for storage, and matplotlib for reporting.

## What It Does

- Register and log in users with hashed passwords
- Create, edit, and delete transactions
- Track income, expense, and transfer entries
- Show a summary dashboard and recent activity
- Generate a chart-based report page

## Technology

- Flask
- Flask-Login
- Flask-SQLAlchemy
- PyMySQL
- MySQL or Railway-managed MySQL
- matplotlib

## Project Structure

- `app.py` main Flask application, models, and routes
- `templates/` HTML templates
- `static/` CSS and other static assets
- `requirements.txt` Python dependencies
- `.env.example` sample environment variables

## Setup

1. Create and activate a virtual environment.
2. Install dependencies.

```bash
pip install -r requirements.txt
```

3. Create a MySQL database named `ledger`.

If you are using XAMPP, start MySQL and run:

```sql
CREATE DATABASE IF NOT EXISTS ledger CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

4. Set environment variables.

```powershell
$env:SECRET_KEY="your-secret-key"
$env:DATABASE_URL="mysql+pymysql://username:password@localhost:3306/ledger"
```

If you are using Railway-managed MySQL, set `DATABASE_URL` or the Railway-provided `MYSQLHOST`, `MYSQLPORT`, `MYSQLUSER`, `MYSQLPASSWORD`, and `MYSQLDATABASE` variables.

5. Run the app.

```bash
python app.py
```

6. Open the app in your browser.

```text
http://127.0.0.1:5000
```

## Notes

- Database tables are created automatically on startup.
- The project is configured for MySQL only.
- Update the secret key before deploying to production.
- Matplotlib chart rendering currently requires Python 3.13 or below.

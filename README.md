# Personal Finance Ledger (Flask)

A complete Flask web app with authentication, full transaction CRUD, MySQL database integration, and matplotlib reporting.

## Features

- User registration and login with hashed passwords
- Add, edit, and delete income, expense, and transfer transactions
- SQLAlchemy models and MySQL database integration
- Financial summary dashboard and report page
- Pie chart visualization using matplotlib
- Responsive Bootstrap interface

## Setup

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Set environment variables for Railway MySQL or a local MySQL instance (PowerShell example):

```powershell
$env:SECRET_KEY="your-secret-key"
$env:DATABASE_URL="mysql+pymysql://username:password@host:3306/ledger"
```

If you are using Railway-managed MySQL, Railway usually provides `MYSQLHOST`, `MYSQLPORT`, `MYSQLUSER`, `MYSQLPASSWORD`, and `MYSQLDATABASE` automatically. The app will use those values if `DATABASE_URL` is not set.

4. Run the app:

```bash
python app.py
```

5. Open your browser at:

```text
http://127.0.0.1:5000
```

## Notes

- Database tables are auto-created when the app starts.
- Replace the default secret key before production deployment.
- Railway MySQL support uses the `mysql+pymysql://` SQLAlchemy driver.
- Matplotlib chart rendering currently requires Python 3.13 or below.

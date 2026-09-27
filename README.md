# SAM Personal Platform

A Flask starter for a personal website combining blog, business/services, portfolio, opportunities, user accounts, and an activity audit log.

## Features
- Responsive navigation and product/service slider
- User registration/login/logout
- Activity logging for authentication and page visits
- Admin dashboard with recent activity
- SQLite by default; `DATABASE_URL` can later be changed to MySQL/PostgreSQL
- Simple, modular Flask structure

## Run
1. Create and activate a virtual environment.
2. Install dependencies: `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and set a strong `SECRET_KEY`.
4. Run: `python run.py`
5. Open http://127.0.0.1:5000

The activity tracker is designed for legitimate first-party analytics/auditing. It records account actions and page visits, not passwords or sensitive form contents.

## Stage 1: production-ready configuration

Copy `.env.example` to `.env` for local development and fill in your own values.

Production variables to configure on Render:

- `SECRET_KEY`
- `DATABASE_URL`
- `API_KEY`
- `MPESA_CONSUMER_KEY`
- `MPESA_CONSUMER_SECRET`
- `SESSION_COOKIE_SECURE=1`

The application accepts PostgreSQL URLs and normalizes them for Psycopg 3.
Do not commit `.env` or real API/M-Pesa credentials.


## Stage 5 — M-Pesa

Stage 5 adds Safaricom Daraja M-Pesa Express (STK Push) support. Configure the Daraja sandbox credentials in `.env` before testing. The callback URL must be publicly reachable; for local development, deploy the app to an HTTPS host such as your Render service and set `MPESA_CALLBACK_URL` to the public `/business/payment/callback` route. Do not put real credentials in source control.

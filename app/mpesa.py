import base64
from datetime import datetime
from decimal import Decimal

import requests
from flask import current_app

SANDBOX_BASE = "https://sandbox.safaricom.co.ke"
PRODUCTION_BASE = "https://api.safaricom.co.ke"


def _base_url():
    return (
        PRODUCTION_BASE
        if current_app.config.get("MPESA_ENV", "sandbox") == "production"
        else SANDBOX_BASE
    )


def get_access_token():
    consumer_key = current_app.config.get("MPESA_CONSUMER_KEY", "")
    consumer_secret = current_app.config.get("MPESA_CONSUMER_SECRET", "")

    if not consumer_key or not consumer_secret:
        raise RuntimeError(
            "MPESA_CONSUMER_KEY and MPESA_CONSUMER_SECRET are required."
        )

    response = requests.get(
        f"{_base_url()}/oauth/v1/generate?grant_type=client_credentials",
        auth=(consumer_key, consumer_secret),
        timeout=30,
    )

    response.raise_for_status()

    data = response.json()
    token = data.get("access_token")

    if not token:
        raise RuntimeError("Daraja did not return an access token.")

    return token


def _timestamp():
    return datetime.now().strftime("%Y%m%d%H%M%S")


def stk_password(timestamp):
    shortcode = current_app.config.get("MPESA_SHORTCODE", "")
    passkey = current_app.config.get("MPESA_PASSKEY", "")

    if not shortcode or not passkey:
        raise RuntimeError(
            "MPESA_SHORTCODE and MPESA_PASSKEY are required."
        )

    raw = f"{shortcode}{passkey}{timestamp}".encode()

    return base64.b64encode(raw).decode()


def normalize_phone(phone):
    digits = "".join(ch for ch in str(phone or "") if ch.isdigit())

    if digits.startswith("0") and len(digits) == 10:
        return "254" + digits[1:]

    if digits.startswith("7") and len(digits) == 9:
        return "254" + digits

    if digits.startswith("254") and len(digits) == 12:
        return digits

    raise ValueError(
        "Enter a valid Kenyan M-Pesa number, e.g. 0712345678."
    )


def initiate_stk_push(order_id, amount, phone, callback_url):
    token = get_access_token()
    timestamp = _timestamp()

    shortcode = current_app.config.get("MPESA_SHORTCODE", "")
    normalized_phone = normalize_phone(phone)

    payload = {
        "BusinessShortCode": shortcode,
        "Password": stk_password(timestamp),
        "Timestamp": timestamp,
        "TransactionType": current_app.config.get(
            "MPESA_TRANSACTION_TYPE",
            "CustomerPayBillOnline",
        ),
        "Amount": int(Decimal(str(amount))),
        "PartyA": normalized_phone,
        "PartyB": shortcode,
        "PhoneNumber": normalized_phone,
        "CallBackURL": callback_url,
        "AccountReference": f"ORDER{order_id}",
        "TransactionDesc": f"Payment for order {order_id}",
    }

    response = requests.post(
        f"{_base_url()}/mpesa/stkpush/v1/processrequest",
        json=payload,
        headers={
            "Authorization": f"Bearer {token}",
        },
        timeout=30,
    )

    if not response.ok:
        print("MPESA HTTP STATUS:", response.status_code)
        print("MPESA ERROR RESPONSE:", response.text)

    response.raise_for_status()

    return response.json(), normalized_phone
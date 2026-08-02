"""Vinemap Stripe revenue API — checkout + license issuance."""

import base64
import json
import logging
import os
import smtplib
import time
from email.message import EmailMessage
from typing import Optional

import stripe
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, EmailStr

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("vinemap.api")

LICENSE_PREFIX = "VMP1"

STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "").strip()
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "").strip()
STRIPE_PRICE_ID = os.environ.get("STRIPE_PRICE_ID", "").strip()
LICENSE_PRIVATE_KEY_HEX = os.environ.get("VINEMAP_LICENSE_PRIVATE_KEY", "").strip()
CHECKOUT_SUCCESS_URL = os.environ.get(
    "CHECKOUT_SUCCESS_URL", "https://vinemap.xyz#pricing"
)
CHECKOUT_CANCEL_URL = os.environ.get(
    "CHECKOUT_CANCEL_URL", "https://vinemap.xyz#pricing"
)
LICENSE_DAYS = int(os.environ.get("LICENSE_DAYS", "35"))
ALLOWED_ORIGINS = [
    o.strip()
    for o in os.environ.get("ALLOWED_ORIGINS", "https://vinemap.xyz").split(",")
    if o.strip()
]

if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY

app = FastAPI(title="Vinemap Revenue API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def sign_license_payload(payload: dict, private_key_hex: str) -> str:
    """Build a VMP1 key (same format as engine/vinemap/license.py)."""
    priv = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(private_key_hex))
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    sig = priv.sign(body)
    return f"{LICENSE_PREFIX}.{_b64url_encode(body)}.{_b64url_encode(sig)}"


def issue_pro_license(subject: str, days: int = LICENSE_DAYS) -> str:
    if not LICENSE_PRIVATE_KEY_HEX:
        raise RuntimeError("VINEMAP_LICENSE_PRIVATE_KEY is not configured")
    payload: dict = {"tier": "pro", "sub": subject}
    if days > 0:
        payload["exp"] = int(time.time()) + days * 86400
    return sign_license_payload(payload, LICENSE_PRIVATE_KEY_HEX)


def _send_license_email(to_email: str, license_key: str) -> None:
    host = os.environ.get("SMTP_HOST", "").strip()
    if not host:
        logger.info("SMTP not configured; license for %s: %s", to_email, license_key)
        return

    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ.get("SMTP_USER", "").strip()
    password = os.environ.get("SMTP_PASS", "").strip()
    from_addr = os.environ.get("SMTP_FROM", user or "licenses@vinemap.xyz")

    msg = EmailMessage()
    msg["Subject"] = "Your Vinemap Pro license key"
    msg["From"] = from_addr
    msg["To"] = to_email
    msg.set_content(
        f"Thanks for subscribing to Vinemap Pro.\n\n"
        f"Activate your license:\n\n"
        f"  vinemap license activate {license_key}\n\n"
        f"Keep this key private. Questions: winklogiq@gmail.com\n"
    )

    with smtplib.SMTP(host, port) as smtp:
        smtp.starttls()
        if user and password:
            smtp.login(user, password)
        smtp.send_message(msg)


class CheckoutCreateRequest(BaseModel):
    email: Optional[EmailStr] = None
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None


def _create_checkout_session(
    email: Optional[str] = None,
    success_url: Optional[str] = None,
    cancel_url: Optional[str] = None,
) -> stripe.checkout.Session:
    if not STRIPE_SECRET_KEY or not STRIPE_PRICE_ID:
        raise HTTPException(
            status_code=503,
            detail="Stripe is not configured (STRIPE_SECRET_KEY, STRIPE_PRICE_ID)",
        )

    params: dict = {
        "mode": "subscription",
        "line_items": [{"price": STRIPE_PRICE_ID, "quantity": 1}],
        "subscription_data": {"trial_period_days": 7},
        "success_url": success_url or CHECKOUT_SUCCESS_URL,
        "cancel_url": cancel_url or CHECKOUT_CANCEL_URL,
        "allow_promotion_codes": True,
    }
    if email:
        params["customer_email"] = email

    return stripe.checkout.Session.create(**params)


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "stripe": bool(STRIPE_SECRET_KEY and STRIPE_PRICE_ID),
        "license_signing": bool(LICENSE_PRIVATE_KEY_HEX),
    }


@app.post("/checkout/create")
def checkout_create(body: CheckoutCreateRequest) -> dict:
    session = _create_checkout_session(
        email=body.email,
        success_url=body.success_url,
        cancel_url=body.cancel_url,
    )
    return {"id": session.id, "url": session.url}


@app.get("/checkout")
def checkout_redirect(email: Optional[str] = None) -> RedirectResponse:
    """Browser-friendly entry point for the marketing site (GET → Stripe Checkout)."""
    session = _create_checkout_session(email=email)
    if not session.url:
        raise HTTPException(status_code=502, detail="Stripe did not return a checkout URL")
    return RedirectResponse(url=session.url, status_code=303)


def _customer_email_from_session(session: dict) -> str:
    details = session.get("customer_details") or {}
    email = details.get("email") or session.get("customer_email") or ""
    if not email and session.get("customer"):
        customer = stripe.Customer.retrieve(session["customer"])
        email = customer.get("email") or ""
    return email.strip()


def _handle_checkout_completed(session: dict) -> None:
    email = _customer_email_from_session(session)
    if not email:
        logger.warning("checkout.session.completed without customer email: %s", session.get("id"))
        return

    license_key = issue_pro_license(subject=email)
    _send_license_email(email, license_key)
    logger.info("Issued Pro license for %s (session %s)", email, session.get("id"))


def _handle_invoice_paid(invoice: dict) -> None:
    """Extend license on subscription renewal (skip first invoice if trial)."""
    if invoice.get("billing_reason") == "subscription_create":
        return

    customer_id = invoice.get("customer")
    if not customer_id:
        return

    customer = stripe.Customer.retrieve(customer_id)
    email = (customer.get("email") or "").strip()
    if not email:
        return

    license_key = issue_pro_license(subject=email)
    _send_license_email(email, license_key)
    logger.info("Renewed Pro license for %s (invoice %s)", email, invoice.get("id"))


@app.post("/webhook/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: Optional[str] = Header(None, alias="Stripe-Signature"),
) -> JSONResponse:
    if not STRIPE_WEBHOOK_SECRET:
        raise HTTPException(status_code=503, detail="STRIPE_WEBHOOK_SECRET is not configured")

    payload = await request.body()
    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature or "", STRIPE_WEBHOOK_SECRET
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid payload") from exc
    except stripe.error.SignatureVerificationError as exc:
        raise HTTPException(status_code=400, detail="Invalid signature") from exc

    event_type = event["type"]
    data_object = event["data"]["object"]

    if event_type == "checkout.session.completed":
        _handle_checkout_completed(data_object)
    elif event_type == "invoice.paid":
        _handle_invoice_paid(data_object)

    return JSONResponse({"received": True})

# Vinemap Revenue API

Minimal FastAPI service for Stripe Checkout and Pro license issuance (`VMP1.<payload>.<sig>`).

## Setup

### 1. Stripe

1. Create a [Stripe account](https://dashboard.stripe.com/register).
2. Create a **Product** → **Pro** with a recurring **$10/month** price.
3. Copy the **Price ID** (`price_...`) into `STRIPE_PRICE_ID`.
4. Copy your **Secret key** (`sk_test_...` or `sk_live_...`) into `STRIPE_SECRET_KEY`.
5. Add a webhook endpoint pointing to `https://<your-api>/webhook/stripe` with events:
   - `checkout.session.completed`
   - `invoice.paid` (optional — renews license on billing cycles)
6. Copy the webhook **Signing secret** (`whsec_...`) into `STRIPE_WEBHOOK_SECRET`.

Local webhook forwarding:

```bash
stripe listen --forward-to localhost:8000/webhook/stripe
```

### 2. License signing key

Generate an Ed25519 keypair (keep the private key secret):

```bash
python3 -c "
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
k = Ed25519PrivateKey.generate()
print('private (hex):', k.private_bytes_raw().hex())
print('public  (hex):', k.public_key().public_bytes_raw().hex())
"
```

- Set `VINEMAP_LICENSE_PRIVATE_KEY` to the **private** hex string (server env only).
- Update `LICENSE_PUBLIC_KEY_HEX` in `engine/vinemap/license.py` with the **public** hex before shipping releases.

### 3. Environment

```bash
cp .env.example .env
# edit .env with your keys
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness + config flags |
| POST | `/checkout/create` | JSON `{ "email": "..." }` → Stripe Checkout session URL |
| GET | `/checkout` | Browser redirect to Stripe Checkout (for static site links) |
| POST | `/webhook/stripe` | Stripe webhook (issues license on `checkout.session.completed`) |

Checkout creates a **$10/mo Pro subscription with a 7-day free trial**. On successful checkout, the API signs a `VMP1` license key and emails it (if SMTP is configured) or logs it.

## Website integration

The marketing site reads the checkout URL at **build time**:

```bash
# website/.env.local (or CI env)
NEXT_PUBLIC_STRIPE_CHECKOUT_URL=https://your-api.example.com/checkout
```

Point this at:

- **`GET /checkout`** on this API (recommended), or
- A [Stripe Payment Link](https://dashboard.stripe.com/payment-links) if you prefer dashboard-only setup.

When `NEXT_PUBLIC_STRIPE_CHECKOUT_URL` is unset, the Pro CTA falls back to `mailto:`.

Rebuild the site after setting the variable:

```bash
cd website && npm run build
```

## Deploy

### Vercel (serverless)

1. Set the project root to `api/`.
2. Add env vars from `.env.example`.
3. Use a `vercel.json` with `"builds": [{ "src": "main.py", "use": "@vercel/python" }]` or deploy as a Python serverless function.

### Railway / Render / Fly

1. Connect the repo, set root directory to `api/`.
2. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
3. Add all env vars from `.env.example`.
4. Register the public URL in Stripe webhooks.

## Security notes

- Never commit `.env` or expose `VINEMAP_LICENSE_PRIVATE_KEY`.
- Verify webhook signatures (`STRIPE_WEBHOOK_SECRET`) — enabled by default.
- Use live Stripe keys only in production.

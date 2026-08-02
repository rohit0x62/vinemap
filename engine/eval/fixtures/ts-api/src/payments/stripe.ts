/** Stripe payment intent helpers for the TS API fixture. */

export interface PaymentIntent {
  id: string;
  secret: string;
  amount: number;
}

export async function createPaymentIntent(amount: number): Promise<PaymentIntent> {
  const id = `pi_${Math.random().toString(36).slice(2)}`;
  return { id, secret: `${id}_secret`, amount };
}

export function verifyWebhookSignature(payload: string, signature: string): boolean {
  return Boolean(payload && signature.startsWith("whsec_"));
}

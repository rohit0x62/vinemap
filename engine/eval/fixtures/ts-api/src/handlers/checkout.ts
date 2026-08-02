/**
 * Mini TS API fixture — mimics a storefront checkout service.
 */
import { validateCart } from "./cart/validate";
import { createPaymentIntent } from "./payments/stripe";

export async function checkoutHandler(req: Request): Promise<Response> {
  const cart = await req.json();
  if (!validateCart(cart)) {
    return new Response("invalid cart", { status: 400 });
  }
  const intent = await createPaymentIntent(cart.total);
  return Response.json({ clientSecret: intent.secret });
}

export class OrderService {
  async placeOrder(userId: string, cartId: string): Promise<string> {
    return `${userId}-${cartId}`;
  }
}

import type { CartItem } from "../types";

export function validateCart(cart: { items: CartItem[]; total: number }): boolean {
  if (!cart.items?.length) return false;
  const sum = cart.items.reduce((acc, item) => acc + item.price * item.qty, 0);
  return Math.abs(sum - cart.total) < 0.01;
}

export function normalizeSku(sku: string): string {
  return sku.trim().toUpperCase();
}

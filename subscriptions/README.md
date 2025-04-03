# Stripe Subscription Integration

This app integrates Stripe for handling subscription payments in the ConsulWealth application.

## Setup Instructions

1. First, make sure your environment variables contain the following Stripe API keys:
   ```
   STRIPE_PUBLISHABLE_KEY=pk_live_your_key
   STRIPE_SECRET_KEY=sk_live_your_key
   STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret
   ```

2. Create a Stripe Product and Price in the Stripe Dashboard:
   - Go to https://dashboard.stripe.com/products
   - Click "Add Product"
   - Set the product name to "ConsulWealth Premium"
   - Set the pricing to $14.99 per month (recurring)
   - Save the product

3. Get the Price ID from the newly created product:
   - After saving, you'll be on the product detail page
   - Look for the "API ID" under the Price section (it should start with "price_")
   - Copy this Price ID and set it in your environment:
   ```
   STRIPE_PREMIUM_PRICE_ID=price_live_your_price_id
   ```

## Usage

Once set up, users will be able to:
1. View the subscription page
2. Choose a subscription plan
3. Enter payment details
4. Complete the subscription process

The subscription will be recorded in the database and managed through Stripe.

## Webhook Integration

For production, webhook integration is essential to handle events such as:
- Payment failures
- Subscription renewals
- Subscription cancellations

To set up webhooks:
1. Go to the Stripe Dashboard > Developers > Webhooks
2. Add an endpoint with your production URL: `https://yoursite.com/subscriptions/webhook/`
3. Select events to listen for:
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.payment_succeeded`
   - `invoice.payment_failed`
4. Copy the Webhook Signing Secret and set it as `STRIPE_WEBHOOK_SECRET` in your environment variables 
# Deploying to AWS Amplify

This document outlines the steps needed to deploy the ConsulWealth Django application to AWS Amplify.

## Prerequisites

1. An AWS account
2. AWS CLI configured with appropriate credentials
3. Amplify CLI installed (`npm install -g @aws-amplify/cli`)

## Deployment Steps

### 1. Prepare Your Environment Variables

Create environment variables in the AWS Amplify Console:

- `DJANGO_SECRET_KEY`: A strong, random string for Django
- `DJANGO_DEBUG`: Set to 'False' for production
- `DJANGO_ALLOWED_HOSTS`: Include your amplifyapp.com domain
- `SUPABASE_URL`: Your Supabase project URL
- `SUPABASE_KEY`: Your Supabase API key
- `SUPABASE_SERVICE_KEY`: Your Supabase service role key
- `PLAID_CLIENT_ID`: Your Plaid client ID
- `PLAID_SECRET`: Your Plaid API secret
- `PLAID_ENVIRONMENT`: 'sandbox', 'development', or 'production'
- `STRIPE_PUBLISHABLE_KEY`: Your Stripe publishable key
- `STRIPE_SECRET_KEY`: Your Stripe secret key
- `STRIPE_WEBHOOK_SECRET`: Your Stripe webhook secret
- `STRIPE_PREMIUM_PRICE_ID`: Your Stripe price ID for premium subscriptions

### 2. Set Up Database

For production, set up an AWS RDS instance or another managed database and update the `DATABASES` setting with:

- `DATABASE_URL`: Connection string to your production database

### 3. Initial Deployment

1. Log into AWS Amplify Console: https://console.aws.amazon.com/amplify/
2. Click "New app" > "Host web app"
3. Choose your code repository provider (GitHub, GitLab, etc.)
4. Select your repository and branch
5. Configure build settings:
   - Use the existing `amplify.yml` file in your repo
6. Set environment variables from step 1
7. Click "Save and deploy"

### 4. Important Notes

- Make sure the `wsgi-entrypoint.sh` file has execute permissions (chmod +x wsgi-entrypoint.sh)
- The first deployment might fail due to build cache; if so, clear cache and rebuild
- For custom domains, configure them in the AWS Amplify Console under "Domain management"
- Set up SSL/TLS certificates for your custom domain through the AWS Amplify Console

### 5. Post-Deployment Tasks

1. Run migrations on the production database:
   ```
   aws amplify start-job --app-id YOUR_AMPLIFY_APP_ID --branch-name main --job-type RELEASE --job-reason "Run migrations" --job-id migration-job
   ```

2. Check that static files are being served correctly
3. Monitor the application logs in the AWS Amplify Console

### 6. Troubleshooting

- If static files aren't loading, check your S3 bucket configuration
- If you get 500 errors, check the application logs in the AWS Amplify Console
- For database connectivity issues, verify security group settings on your RDS instance

## Continuous Deployment

AWS Amplify will automatically deploy your application when you push changes to your connected repository branch. 
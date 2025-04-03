# ConsulWealth

ConsulWealth is a comprehensive financial management platform using Django and Supabase.

## Application Structure

- **Backend:** Django application integrated with Supabase
- **Database:** Combination of Supabase and minimal PostgreSQL (for Django-specific models)
- **Authentication:** Supabase Auth with Django shadow user system
- **API:** RESTful API using Django REST framework

## Deployment

This application is configured for deployment with AWS Amplify. For complete deployment instructions, see [DEPLOYMENT.md](DEPLOYMENT.md).

### Quick Start for Deployment

1. Clone the repository
2. Set up your environment variables in the AWS Amplify Console
3. Connect your repository to AWS Amplify
4. Deploy using the existing amplify.yml configuration

## Local Development

1. Clone the repository
2. Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Copy the `.env.example` file to `.env` and fill in your credentials
5. Run migrations:
   ```
   cd clean_backend
   python manage.py migrate
   ```
6. Start the development server:
   ```
   python manage.py runserver
   ```

## Project Structure

The main application is in the `clean_backend` directory, with a Supabase-first architecture that minimizes Django models and maximizes use of Supabase services.

### Key Components:

- **Core:** Django project settings and configuration
- **Supabase Integration:** Adapters and services for Supabase
- **Users:** Authentication and user management
- **Dashboard:** Main application views and templates
- **Subscriptions:** Payment and subscription management

## Documentation

- For detailed backend architecture, see [clean_backend/README.md](clean_backend/README.md)
- For API documentation, refer to the API section in the backend README
- For deployment instructions, see [DEPLOYMENT.md](DEPLOYMENT.md) 
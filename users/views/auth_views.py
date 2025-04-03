from django.contrib.auth import get_user_model, logout
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from ..serializers import UserSerializer
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib import messages
from django.views.decorators.csrf import csrf_protect
from django.contrib.auth.decorators import login_required
from django.core.validators import validate_email, RegexValidator
from django.core.exceptions import ValidationError
from decimal import Decimal
from django.utils import timezone
from ..utils import is_valid_email, validate_password_strength, send_verification_email, notify_admin_account_lockout
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.core.mail import send_mail
from django.conf import settings
import uuid
from ..models import User
import logging
from django.utils.crypto import get_random_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from datetime import timedelta
from ..forms import UserRegisterForm, UserLoginForm
from supabase_integration.adapter import SupabaseAdapter

User = get_user_model()
logger = logging.getLogger(__name__)

@api_view(['POST'])
@permission_classes([AllowAny])
def register_user(request):
    """
    Register a new user
    """
    serializer = UserSerializer(data=request.data)
    if serializer.is_valid():
        # Create user with encrypted password
        user = User.objects.create_user(
            username=serializer.validated_data['username'],
            email=serializer.validated_data['email'],
            password=request.data['password']  # Password will be hashed by create_user
        )
        
        # Update additional fields
        for field in ['phone_number', 'date_of_birth', 'risk_tolerance', 
                     'annual_income', 'investment_experience']:
            if field in serializer.validated_data:
                setattr(user, field, serializer.validated_data[field])
        user.save()
        
        # Return user data without password
        return Response(
            UserSerializer(user).data,
            status=status.HTTP_201_CREATED
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([AllowAny])
def login_user(request):
    """
    Login a user and return token
    """
    from django.contrib.auth import authenticate
    from rest_framework_simplejwt.tokens import RefreshToken
    
    username = request.data.get('username')
    password = request.data.get('password')
    
    if not username or not password:
        return Response(
            {'error': 'Please provide both username and password'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    user = authenticate(username=username, password=password)
    
    if user:
        refresh = RefreshToken.for_user(user)
        return Response({
            'user': UserSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        })
    
    return Response(
        {'error': 'Invalid credentials'},
        status=status.HTTP_401_UNAUTHORIZED
    )

@api_view(['GET', 'PUT'])
def user_profile(request):
    """
    Get or update user profile
    """
    if request.method == 'GET':
        serializer = UserSerializer(request.user)
        return Response(serializer.data)
    
    elif request.method == 'PUT':
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            # Don't save the user yet
            user = form.save(commit=False)
            
            # Get the password from the form
            password = form.cleaned_data.get('password1')
            
            # Create the user in Supabase first
            adapter = SupabaseAdapter()
            
            # Prepare user data for Supabase profile
            user_data = {
                'email': user.email,
                'phone_number': getattr(user, 'phone_number', None),
                'date_of_birth': getattr(user, 'date_of_birth', None),
                'risk_tolerance': getattr(user, 'risk_tolerance', None),
                'investment_experience': getattr(user, 'investment_experience', None),
            }
            
            # Create user in Supabase
            supabase_id = adapter.create_user(user.email, password, user_data)
            
            if supabase_id:
                # Now save the Django user
                user.save()
                
                # No need for SupabaseSync record anymore
                # The sync is handled automatically via user signals
                
                # Log the user in
                login(request, user)
                
                messages.success(request, f'Account created successfully!')
                return redirect('dashboard:dashboard')
            else:
                messages.error(request, 'Error creating account in Supabase')
    else:
        form = UserRegisterForm()
    return render(request, 'users/register.html', {'form': form})

def login_view(request):
    logger.info("Login view accessed")
    
    if request.user.is_authenticated:
        logger.info(f"User {request.user.username} already authenticated, redirecting to dashboard")
        return redirect('dashboard:dashboard')
        
    if request.method == 'POST':
        logger.info("Processing POST request")
        form = UserLoginForm(request.POST)
        if form.is_valid():
            logger.info("Form is valid")
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            logger.info(f"Authentication attempt for user {username}")
            
            if user is not None:
                if user.is_active:
                    login(request, user)
                    logger.info(f"User {username} successfully logged in")
                    messages.success(request, f'Welcome back, {username}!')
                    logger.info("Redirecting to dashboard")
                    return redirect('dashboard:dashboard')
                else:
                    logger.warning(f"User {username} account is not active")
                    messages.error(request, 'Account is not active.')
            else:
                logger.warning(f"Failed login attempt for user {username}")
                messages.error(request, 'Invalid username or password.')
        else:
            logger.warning("Form validation failed")
            logger.warning(f"Form errors: {form.errors}")
    else:
        form = UserLoginForm()
    
    return render(request, 'users/login.html', {'form': form})

@login_required
def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('users:login')

@login_required
def profile_view(request):
    if request.method == 'POST':
        user = request.user
        
        # Validation functions
        def validate_phone(phone):
            phone_regex = RegexValidator(
                regex=r'^\+?1?\d{9,15}$',
                message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
            )
            if phone:
                phone_regex(phone)
            return phone

        def validate_amount(amount, field_name):
            if amount:
                try:
                    amount = Decimal(amount)
                    if amount < 0:
                        raise ValidationError(f"{field_name} cannot be negative")
                    return amount
                except (TypeError, ValueError):
                    raise ValidationError(f"Invalid amount for {field_name}")
            return None

        def validate_age(age):
            if age:
                try:
                    age = int(age)
                    if not (18 <= age <= 100):
                        raise ValidationError("Retirement age must be between 18 and 100")
                    return age
                except ValueError:
                    raise ValidationError("Invalid age value")
            return None

        try:
            # Validate and prepare data
            fields_to_update = {
                'phone_number': validate_phone(request.POST.get('phone_number')),
                'annual_income': validate_amount(request.POST.get('annual_income'), 'Annual income'),
                'net_worth': validate_amount(request.POST.get('net_worth'), 'Net worth'),
                'monthly_savings_goal': validate_amount(request.POST.get('monthly_savings_goal'), 'Monthly savings goal'),
                'retirement_age_goal': validate_age(request.POST.get('retirement_age_goal')),
                'risk_tolerance': request.POST.get('risk_tolerance'),
                'investment_experience': request.POST.get('investment_experience'),
                'investment_timeline': request.POST.get('investment_timeline'),
                'employment_status': request.POST.get('employment_status'),
            }

            # Update valid fields
            for field, value in fields_to_update.items():
                if value not in [None, '']:
                    setattr(user, field, value)
            
            user.save()
            messages.success(request, 'Profile updated successfully!')
            
        except ValidationError as e:
            messages.error(request, f'Validation error: {str(e)}')
        except Exception as e:
            messages.error(request, f'Error updating profile: {str(e)}')
        
        return redirect('profile')
    
    return render(request, 'users/profile.html')

@login_required
def verify_email(request, token):
    try:
        user = User.objects.get(email_verification_token=token)
        
        # Check if token is expired (24 hours)
        if user.email_verification_sent_at < timezone.now() - timezone.timedelta(hours=24):
            messages.error(request, 'Verification link has expired. Please request a new one.')
            return redirect('profile')
        
        user.email_verified = True
        user.save()
        
        messages.success(request, 'Email verified successfully!')
        logger.info(f"Email verified successfully for user: {user.email}")
        
    except User.DoesNotExist:
        messages.error(request, 'Invalid verification link')
        logger.error(f"Invalid verification token: {token}")
    
    return redirect('profile')

@login_required
def resend_verification(request):
    if request.user.is_authenticated and not request.user.email_verified:
        # Generate new verification token
        token = generate_verification_token(request.user)
        
        # Send verification email
        send_verification_email(request.user, token)
        
        messages.success(request, 'Verification email has been resent. Please check your inbox.')
    
    return redirect('users:profile')

def password_reset_request(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        try:
            user = User.objects.get(email=email)
            
            # Generate token
            token = get_random_string(32)
            user.password_reset_token = token
            user.password_reset_token_created = timezone.now()
            user.save()
            
            # Update the reset URL to match our URL pattern
            reset_url = f'http://127.0.0.1:8000/api/users/password_reset_confirm/{urlsafe_base64_encode(force_bytes(user.pk))}/{token}/'
            
            html_message = render_to_string('users/emails/password_reset_email.html', {
                'user': user,
                'reset_url': reset_url,
            })
            
            send_mail(
                'Reset Your ConsulWealth Password',
                strip_tags(html_message),
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                html_message=html_message,
            )
            
            messages.success(request, 'Password reset link has been sent to your email.')
            return redirect('login')
            
        except User.DoesNotExist:
            messages.error(request, 'No account found with that email address.')
    
    return render(request, 'users/password_reset.html')

def password_reset_confirm(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
        valid_link = (
            user.password_reset_token == token and
            user.password_reset_token_created > timezone.now() - timezone.timedelta(hours=1)
        )
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
        valid_link = False
    
    if request.method == 'POST' and valid_link:
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        
        if password1 != password2:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'users/password_reset_confirm.html', {'valid_link': True})
        
        password_errors = validate_password_strength(password1)
        if password_errors:
            for error in password_errors:
                messages.error(request, error)
            return render(request, 'users/password_reset_confirm.html', {'valid_link': True})
        
        user.set_password(password1)
        user.password_reset_token = None
        user.password_reset_token_created = None
        user.save()
        
        messages.success(request, 'Your password has been reset successfully. You can now log in.')
        return redirect('login')
    
    return render(request, 'users/password_reset_confirm.html', {'valid_link': valid_link})

@login_required
def link_account_view(request):
    return render(request, 'users/link_account.html')

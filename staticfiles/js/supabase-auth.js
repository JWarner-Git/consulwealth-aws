/**
 * Supabase Authentication Helper
 * 
 * This script provides client-side support for Supabase authentication,
 * particularly handling token refresh.
 */

// Function to refresh the token when it's about to expire
async function refreshSupabaseToken() {
    try {
        // Get the refresh token from storage (either localStorage or cookie)
        const refreshToken = getRefreshToken();
        
        if (!refreshToken) {
            console.warn('No refresh token available');
            return;
        }
        
        // Call the API endpoint to refresh the token
        const response = await fetch('/auth/token/refresh/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({ refresh_token: refreshToken })
        });
        
        if (!response.ok) {
            throw new Error('Token refresh failed');
        }
        
        const data = await response.json();
        
        // Store the new tokens (in localStorage for this example)
        if (data.access_token) {
            localStorage.setItem('supabase_access_token', data.access_token);
        }
        
        if (data.refresh_token) {
            localStorage.setItem('supabase_refresh_token', data.refresh_token);
        }
        
        console.log('Token refreshed successfully');
        
        // Schedule the next refresh (5 minutes before expiry)
        if (data.expires_in) {
            const refreshIn = (data.expires_in - 300) * 1000; // 5 minutes before expiry
            setTimeout(refreshSupabaseToken, refreshIn);
        }
        
    } catch (error) {
        console.error('Error refreshing token:', error);
        // Redirect to login if refresh fails
        window.location.href = '/auth/login/';
    }
}

// Helper function to get the refresh token from storage
function getRefreshToken() {
    // Try localStorage first
    const token = localStorage.getItem('supabase_refresh_token');
    if (token) {
        return token;
    }
    
    // If not in localStorage, try to get from cookie
    return getCookieValue('supabase_refresh_token');
}

// Helper function to get a cookie value by name
function getCookieValue(name) {
    const cookieString = document.cookie;
    const cookies = cookieString.split(';');
    
    for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        
        // Check if this cookie is the one we're looking for
        if (cookie.startsWith(name + '=')) {
            return cookie.substring(name.length + 1);
        }
    }
    
    return null;
}

// Helper function to get CSRF token from cookies
function getCsrfToken() {
    return getCookieValue('csrftoken');
}

// Function to initialize the auth system when the page loads
function initSupabaseAuth() {
    // Get token from localStorage or cookie
    const token = localStorage.getItem('supabase_access_token') || getCookieValue('supabase_auth_token');
    
    if (token) {
        // Token exists, set up refresh cycle
        // Schedule initial refresh (we'll check validity on the server)
        setTimeout(refreshSupabaseToken, 5 * 60 * 1000); // Check every 5 minutes
    }
}

// Initialize when the page loads
document.addEventListener('DOMContentLoaded', initSupabaseAuth); 
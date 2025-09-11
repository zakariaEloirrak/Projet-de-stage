from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages

class CustomAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # URLs that don't require authentication
        try:
            public_urls = [
                reverse('home'),
                reverse('login'),
                reverse('register'),
            ]
        except:
            # Fallback if reverse fails
            public_urls = [
                '/',
                '/login/',
                '/register/',
            ]
        
        # Admin URLs - allow access for administrators
        admin_prefix = '/admin/'
        
        # Check if user is authenticated
        user_id = request.session.get('user_id')
        
        # Allow access to public URLs
        if request.path in public_urls or request.path == '/':
            return self.get_response(request)
        
        # Handle admin URLs
        if request.path.startswith(admin_prefix):
            if not user_id:
                messages.error(request, 'Vous devez être connecté pour accéder à cette page.')
                return redirect('login')
            
            try:
                from .models import User
                user = User.objects.get(id=user_id, actif=True)
                if user.role != 'ADMIN':
                    messages.error(request, 'Accès non autorisé. Droits administrateur requis.')
                    return redirect('dashboard')
                request.user = user
            except User.DoesNotExist:
                request.session.flush()
                messages.error(request, 'Session expirée. Veuillez vous reconnecter.')
                return redirect('login')
            
            return self.get_response(request)
        
        # Redirect to login if not authenticated for other URLs
        if not user_id:
            messages.error(request, 'Vous devez être connecté pour accéder à cette page.')
            return redirect('login')
        
        # Verify user still exists and is active
        try:
            from .models import User
            user = User.objects.get(id=user_id, actif=True)
            request.user = user  # Add user to request
        except User.DoesNotExist:
            request.session.flush()
            messages.error(request, 'Session expirée. Veuillez vous reconnecter.')
            return redirect('login')

        response = self.get_response(request)
        return response

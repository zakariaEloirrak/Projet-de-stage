from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.hashers import check_password
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from datetime import datetime, timedelta
from .models import User, AuditLog, Commande, CLIENT, POISSON, Facture
from .forms import LoginForm, RegisterForm, UserProfileForm
import json

# Custom login required decorator
def custom_login_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.session.get('user_id'):
            messages.error(request, 'Vous devez être connecté pour accéder à cette page.')
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper

def home_view(request):
    """Home page view - redirects authenticated users to dashboard"""
    user_id = request.session.get('user_id')
    
    if user_id:
        # User is authenticated, redirect to dashboard
        return redirect('dashboard')
    
    # User is not authenticated, show landing page
    context = {
        'total_clients': CLIENT.objects.filter(actif=True).count(),
        'total_produits': POISSON.objects.filter(actif=True).count(),
        'commandes_ce_mois': Commande.objects.filter(
            date_creation__month=timezone.now().month,
            date_creation__year=timezone.now().year
        ).count(),
    }
    
    return render(request, 'home.html', context)

def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            
            try:
                user = User.objects.get(username=username, actif=True)
                if check_password(password, user.password):
                    request.session['user_id'] = user.id
                    request.session['username'] = user.username
                    request.session['role'] = user.role
                    
                    # Log authentication
                    AuditLog.objects.create(
                        utilisateur=user,
                        action='VIEW',
                        model_name='Auth',
                        object_id=user.id,
                        object_repr=f"Login: {user.username}",
                        adresse_ip=get_client_ip(request)
                    )
                    
                    messages.success(request, f'Bienvenue {user.username}!')
                    
                    # Redirect based on role
                    if user.role == 'ADMIN':
                        return redirect('/admin/')
                    else:
                        return redirect('dashboard')
                else:
                    messages.error(request, 'Mot de passe incorrect.')
            except User.DoesNotExist:
                messages.error(request, 'Utilisateur non trouvé ou inactif.')
    else:
        form = LoginForm()
    
    return render(request, 'auth/login.html', {'form': form})


@custom_login_required
def logout_view(request):
    user_id = request.session.get('user_id')
    if user_id:
        try:
            user = User.objects.get(id=user_id)
            # Log logout
            AuditLog.objects.create(
                utilisateur=user,
                action='VIEW',
                model_name='Auth',
                object_id=user.id,
                object_repr=f"Logout: {user.username}",
                adresse_ip=get_client_ip(request)
            )
        except User.DoesNotExist:
            pass
    
    request.session.flush()
    messages.success(request, 'Déconnexion réussie.')
    return redirect('home')

@custom_login_required
def dashboard_view(request):
    user_id = request.session.get('user_id')
    user = User.objects.get(id=user_id)
    
    # Get dashboard statistics
    total_commandes = Commande.objects.count()
    commandes_en_cours = Commande.objects.filter(
        statut__in=['PREPARATION', 'EXPEDIEE']
    ).count()
    factures_impayees = Facture.objects.filter(
        statut__in=['emise', 'envoyee']
    ).count()
    
    # Recent orders
    commandes_recentes = Commande.objects.select_related('client').order_by('-date_creation')[:5]
    
    context = {
        'user': user,
        'total_commandes': total_commandes,
        'commandes_en_cours': commandes_en_cours,
        'factures_impayees': factures_impayees,
        'commandes_recentes': commandes_recentes,
    }
    
    return render(request, 'dashboard/dashboard.html', context)

@custom_login_required
def profile_view(request):
    user_id = request.session.get('user_id')
    user = User.objects.get(id=user_id)
    
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profil mis à jour avec succès.')
            return redirect('profile')
    else:
        form = UserProfileForm(instance=user)
    
    return render(request, 'auth/profile.html', {'form': form, 'user': user})

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
    

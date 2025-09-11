from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Sum, Count, Q, F
from django.utils import timezone
from datetime import datetime, timedelta
from django import forms
import json
import io

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.units import inch

from .models import CLIENT, User, Commande, AuditLog, Facture

# Custom login required decorator
def custom_login_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.session.get('user_id'):
            messages.error(request, 'Vous devez être connecté pour accéder à cette page.')
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper

# Forms
class ClientForm(forms.ModelForm):
    class Meta:
        model = CLIENT
        fields = ['nom_societe', 'email', 'telephone', 'adresse', 'pays', 'role', 
                 'numero_registre_commerce', 'numero_ice']
        widgets = {
            'nom_societe': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'telephone': forms.TextInput(attrs={'class': 'form-control'}),
            'adresse': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'pays': forms.TextInput(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-control'}),
            'numero_registre_commerce': forms.TextInput(attrs={'class': 'form-control'}),
            'numero_ice': forms.TextInput(attrs={'class': 'form-control'}),
        }

class ClientSearchForm(forms.Form):
    search = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Rechercher par nom, email ou code...'
        })
    )
    role = forms.ChoiceField(
        choices=[('', 'Tous')] + CLIENT.ROLE_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    pays = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Filtrer par pays...'
        })
    )

# Views
@custom_login_required
def client_dashboard(request):
    user_id = request.session.get('user_id')
    user = User.objects.get(id=user_id)
    
    # Statistiques générales
    total_clients = CLIENT.objects.filter(actif=True).count()
    clients_actifs = CLIENT.objects.filter(actif=True, role='CLIENT').count()
    fournisseurs_actifs = CLIENT.objects.filter(actif=True, role='FOURNISSEUR').count()
    
    # Nouveaux clients ce mois
    premier_jour_mois = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    nouveaux_clients = CLIENT.objects.filter(
        date_creation__gte=premier_jour_mois,
        actif=True
    ).count()
    
    # Top 5 clients par nombre de commandes
    top_clients = CLIENT.objects.filter(actif=True).annotate(
        nb_commandes=Count('commande')
    ).order_by('-nb_commandes')[:5]
    
    # Répartition par pays
    repartition_pays = CLIENT.objects.filter(actif=True).values('pays').annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    # Clients récents
    clients_recents = CLIENT.objects.filter(actif=True).order_by('-date_creation')[:5]
    
    # Données pour graphique
    chart_data = {}
    for item in repartition_pays:
        chart_data[item['pays'] or 'Non spécifié'] = item['count']
    
    context = {
        'user': user,
        'total_clients': total_clients,
        'clients_actifs': clients_actifs,
        'fournisseurs_actifs': fournisseurs_actifs,
        'nouveaux_clients': nouveaux_clients,
        'top_clients': top_clients,
        'repartition_pays': repartition_pays,
        'clients_recents': clients_recents,
        'chart_data': json.dumps(chart_data),
    }
    
    return render(request, 'clients/dashboard.html', context)

@custom_login_required
def liste_clients(request):
    user_id = request.session.get('user_id')
    user = User.objects.get(id=user_id)
    
    clients = CLIENT.objects.filter(actif=True).order_by('nom_societe')
    
    # Filtres
    search = request.GET.get('search', '')
    if search:
        clients = clients.filter(
            Q(nom_societe__icontains=search) |
            Q(email__icontains=search) |
            Q(code_client__icontains=search) |
            Q(numero_ice__icontains=search)
        )
    
    role_filter = request.GET.get('role', '')
    if role_filter:
        clients = clients.filter(role=role_filter)
    
    pays_filter = request.GET.get('pays', '')
    if pays_filter:
        clients = clients.filter(pays__icontains=pays_filter)
    
    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(clients, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Liste des pays pour le filtre
    pays_list = CLIENT.objects.filter(actif=True).values_list('pays', flat=True).distinct().order_by('pays')
    
    context = {
        'user': user,
        'page_obj': page_obj,
        'pays_list': pays_list,
        'search': search,
        'role_filter': role_filter,
        'pays_filter': pays_filter,
    }
    
    return render(request, 'clients/liste_clients.html', context)

@custom_login_required
def ajouter_client(request):
    user_id = request.session.get('user_id')
    user = User.objects.get(id=user_id)
    
    if request.method == 'POST':
        form = ClientForm(request.POST)
        if form.is_valid():
            client = form.save()
            
            # Log audit
            AuditLog.objects.create(
                utilisateur=user,
                action='CREATE',
                model_name='CLIENT',
                object_id=client.id,
                object_repr=str(client),
                details={
                    'nom_societe': client.nom_societe,
                    'role': client.role,
                    'pays': client.pays
                }
            )
            
            messages.success(request, f'Client {client.nom_societe} ajouté avec succès.')
            return redirect('detail_client', client_id=client.id)
    else:
        form = ClientForm()
    
    return render(request, 'clients/ajouter_client.html', {
        'form': form,
        'user': user
    })

@custom_login_required
def detail_client(request, client_id):
    user_id = request.session.get('user_id')
    user = User.objects.get(id=user_id)
    
    client = get_object_or_404(CLIENT, id=client_id, actif=True)
    
    # Commandes du client
    commandes = Commande.objects.filter(client=client).order_by('-date_creation')[:10]
    
    # Statistiques du client
    total_commandes = Commande.objects.filter(client=client).count()
    commandes_en_cours = Commande.objects.filter(
        client=client,
        statut__in=['PREPARATION', 'EXPEDIEE']
    ).count()
    
    # Factures
    factures = Facture.objects.filter(client=client).order_by('-date_emission')[:5]
    total_factures = Facture.objects.filter(client=client).count()
    factures_impayees = Facture.objects.filter(
        client=client,
        statut__in=['emise', 'envoyee']
    ).count()
    
    # Chiffre d'affaires
    ca_total = Facture.objects.filter(
        client=client,
        statut='payee'
    ).aggregate(total=Sum('montant_ttc'))['total'] or 0
    
    # Évolution des commandes (6 derniers mois)
    chart_data = []
    for i in range(6):
        date_debut = timezone.now().replace(day=1) - timedelta(days=30*i)
        date_fin = (date_debut + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        
        nb_commandes = Commande.objects.filter(
            client=client,
            date_creation__gte=date_debut,
            date_creation__lte=date_fin
        ).count()
        
        chart_data.append({
            'mois': date_debut.strftime('%m/%Y'),
            'commandes': nb_commandes
        })
    
    chart_data.reverse()
    
    context = {
        'user': user,
        'client': client,
        'commandes': commandes,
        'total_commandes': total_commandes,
        'commandes_en_cours': commandes_en_cours,
        'factures': factures,
        'total_factures': total_factures,
        'factures_impayees': factures_impayees,
        'ca_total': ca_total,
        'chart_data': json.dumps(chart_data),
    }
    
    return render(request, 'clients/detail_client.html', context)

@custom_login_required
def modifier_client(request, client_id):
    user_id = request.session.get('user_id')
    user = User.objects.get(id=user_id)
    
    client = get_object_or_404(CLIENT, id=client_id, actif=True)
    
    if request.method == 'POST':
        form = ClientForm(request.POST, instance=client)
        if form.is_valid():
            # Sauvegarder les anciennes valeurs pour l'audit
            anciennes_valeurs = {
                'nom_societe': client.nom_societe,
                'email': client.email,
                'role': client.role
            }
            
            client = form.save()
            
            # Log audit
            AuditLog.objects.create(
                utilisateur=user,
                action='UPDATE',
                model_name='CLIENT',
                object_id=client.id,
                object_repr=str(client),
                details={
                    'anciennes_valeurs': anciennes_valeurs,
                    'nouvelles_valeurs': {
                        'nom_societe': client.nom_societe,
                        'email': client.email,
                        'role': client.role
                    }
                }
            )
            
            messages.success(request, f'Client {client.nom_societe} modifié avec succès.')
            return redirect('detail_client', client_id=client.id)
    else:
        form = ClientForm(instance=client)
    
    context = {
        'form': form,
        'client': client,
        'user': user
    }
    
    return render(request, 'clients/modifier_client.html', context)

@custom_login_required
def desactiver_client(request, client_id):
    user_id = request.session.get('user_id')
    user = User.objects.get(id=user_id)
    
    client = get_object_or_404(CLIENT, id=client_id, actif=True)
    
    if request.method == 'POST':
        client.actif = False
        client.save()
        
        # Log audit
        AuditLog.objects.create(
            utilisateur=user,
            action='UPDATE',
            model_name='CLIENT',
            object_id=client.id,
            object_repr=str(client),
            details={'action': 'désactivation'}
        )
        
        messages.success(request, f'Client {client.nom_societe} désactivé avec succès.')
        return redirect('liste_clients')
    
    return render(request, 'clients/confirmer_desactivation.html', {
        'client': client,
        'user': user
    })

@custom_login_required
def rapport_clients_pdf(request):
    """Génère un rapport PDF des clients"""
    user_id = request.session.get('user_id')
    user = User.objects.get(id=user_id)
    
    # Créer la réponse HTTP pour PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="rapport_clients_{timezone.now().strftime("%Y%m%d_%H%M")}.pdf"'
    
    # Créer le document PDF
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    story = []
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=30,
        alignment=1  # Center
    )
    
    # Titre
    title = Paragraph("RAPPORT CLIENTS", title_style)
    story.append(title)
    story.append(Spacer(1, 12))
    
    # Date et heure
    date_rapport = Paragraph(f"Généré le {timezone.now().strftime('%d/%m/%Y à %H:%M')}", styles['Normal'])
    story.append(date_rapport)
    story.append(Spacer(1, 20))
    
    # Données des clients
    clients = CLIENT.objects.filter(actif=True).order_by('nom_societe')
    
    # Statistiques globales
    stats = {
        'total_clients': clients.count(),
        'clients_acheteurs': clients.filter(role='CLIENT').count(),
        'fournisseurs': clients.filter(role='FOURNISSEUR').count(),
    }
    
    # Tableau des statistiques
    stats_data = [
        ['Statistiques Générales', ''],
        ['Total clients actifs', str(stats['total_clients'])],
        ['Clients acheteurs', str(stats['clients_acheteurs'])],
        ['Fournisseurs', str(stats['fournisseurs'])],
    ]
    
    stats_table = Table(stats_data, colWidths=[3*inch, 2*inch])
    stats_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(stats_table)
    story.append(Spacer(1, 30))
    
    # Titre détail des clients
    detail_title = Paragraph("LISTE DES CLIENTS", styles['Heading2'])
    story.append(detail_title)
    story.append(Spacer(1, 12))
    
    # Tableau des clients
    data = [['Code', 'Société', 'Email', 'Pays', 'Rôle', 'Date Création']]
    
    for client in clients:
        data.append([
            client.code_client or "N/A",
            client.nom_societe,
            client.email,
            client.pays or "N/A",
            client.get_role_display(),
            client.date_creation.strftime('%d/%m/%Y')
        ])
    
    table = Table(data, colWidths=[1*inch, 2*inch, 2*inch, 1*inch, 1*inch, 1*inch])
    table.setStyle(TableStyle([
        # En-tête
        ('BACKGROUND', (0, 0), (-1, 0), colors.navy),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        
        # Corps du tableau
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    
    story.append(table)
    
    # Pied de page
    story.append(Spacer(1, 30))
    footer = Paragraph(f"Rapport généré par {user.username} - FishFlow Manager", styles['Italic'])
    story.append(footer)
    
    # Construire le PDF
    doc.build(story)
    
    # Récupérer le contenu du buffer
    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)
    
    # Log de l'action
    AuditLog.objects.create(
        utilisateur=user,
        action='EXPORT',
        model_name='CLIENT',
        object_id=0,
        object_repr="Rapport clients PDF",
        details={'format': 'PDF', 'clients_count': clients.count()}
    )
    
    return response

@custom_login_required
def api_clients_stats(request):
    """API pour les statistiques clients"""
    try:
        # Répartition par pays
        pays_stats = CLIENT.objects.filter(actif=True).values('pays').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Évolution mensuelle
        evolution = []
        for i in range(6):
            date_debut = timezone.now().replace(day=1) - timedelta(days=30*i)
            date_fin = (date_debut + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            
            nb_clients = CLIENT.objects.filter(
                date_creation__gte=date_debut,
                date_creation__lte=date_fin,
                actif=True
            ).count()
            
            evolution.append({
                'mois': date_debut.strftime('%m/%Y'),
                'clients': nb_clients
            })
        
        evolution.reverse()
        
        return JsonResponse({
            'success': True,
            'pays_stats': list(pays_stats),
            'evolution': evolution
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

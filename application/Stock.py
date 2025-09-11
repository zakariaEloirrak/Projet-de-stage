from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Sum, Count, Q, F
from django.db.models.functions import TruncDate, TruncMonth, TruncWeek
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

from .models import POISSON, MouvementStock, User, Commande, AuditLog

# Custom login required decorator
def custom_login_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.session.get('user_id'):
            messages.error(request, 'Vous devez être connecté pour accéder à cette page.')
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper

# Forms
class MouvementStockForm(forms.ModelForm):
    class Meta:
        model = MouvementStock
        fields = ['poisson', 'type_mouvement', 'quantite', 'commande', 'motif']
        widgets = {
            'poisson': forms.Select(attrs={'class': 'form-control'}),
            'type_mouvement': forms.Select(attrs={'class': 'form-control'}),
            'quantite': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0'
            }),
            'commande': forms.Select(attrs={'class': 'form-control'}),
            'motif': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['poisson'].queryset = POISSON.objects.filter(actif=True)
        self.fields['commande'].queryset = Commande.objects.all()
        self.fields['commande'].required = False

class PoissonForm(forms.ModelForm):
    class Meta:
        model = POISSON
        fields = ['type', 'prix', 'quantite_stock', 'unite_mesure', 'seuil_alerte']
        widgets = {
            'type': forms.TextInput(attrs={'class': 'form-control'}),
            'prix': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0'
            }),
            'quantite_stock': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0'
            }),
            'unite_mesure': forms.TextInput(attrs={'class': 'form-control'}),
            'seuil_alerte': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0'
            })
        }

# Views
@custom_login_required
def stock_dashboard(request):
    user_id = request.session.get('user_id')
    user = User.objects.get(id=user_id)
    
    # Statistiques générales
    total_produits = POISSON.objects.filter(actif=True).count()
    produits_alerte = POISSON.objects.filter(
        quantite_stock__lte=F('seuil_alerte'),
        actif=True
    ).count()
    
    # Valeur totale du stock
    valeur_stock = POISSON.objects.filter(actif=True).aggregate(
        total=Sum(F('quantite_stock') * F('prix'))
    )['total'] or 0
    
    # Mouvements du jour
    aujourd_hui = timezone.now().date()
    mouvements_jour = MouvementStock.objects.filter(
        date_mouvement__date=aujourd_hui
    ).count()
    
    # Mouvements récents
    mouvements_recents = MouvementStock.objects.select_related(
        'poisson', 'utilisateur'
    ).order_by('-date_mouvement')[:10]
    
    # Statistiques par type de mouvement (30 derniers jours)
    date_limite = timezone.now() - timedelta(days=30)
    stats_mouvements = MouvementStock.objects.filter(
        date_mouvement__gte=date_limite
    ).values('type_mouvement').annotate(
        total_quantite=Sum('quantite'),
        nombre_mouvements=Count('id')
    )
    
    # Données pour graphique des 7 derniers jours
    date_debut = timezone.now() - timedelta(days=7)
    mouvements_semaine = MouvementStock.objects.filter(
        date_mouvement__gte=date_debut
    ).extra({'date': 'date(date_mouvement)'}).values(
        'date', 'type_mouvement'
    ).annotate(
        total=Sum('quantite')
    ).order_by('date')
    
    # Préparer données pour Chart.js
    chart_data = {}
    dates_range = [(date_debut + timedelta(days=x)).date() for x in range(8)]
    
    for date_item in dates_range:
        date_str = date_item.strftime('%Y-%m-%d')
        chart_data[date_str] = {'ENTREE': 0, 'SORTIE': 0, 'AJUSTEMENT': 0, 'RETOUR': 0}
    
    for mouvement in mouvements_semaine:
        date_str = mouvement['date'].strftime('%Y-%m-%d')
        if date_str in chart_data:
            chart_data[date_str][mouvement['type_mouvement']] = float(mouvement['total'])
    
    # Top 5 produits les plus mouvementés
    top_produits = MouvementStock.objects.filter(
        date_mouvement__gte=date_limite
    ).values(
        'poisson__type', 'poisson__code_produit'
    ).annotate(
        total_mouvements=Sum('quantite')
    ).order_by('-total_mouvements')[:5]
    
    context = {
        'user': user,
        'total_produits': total_produits,
        'produits_alerte': produits_alerte,
        'valeur_stock': valeur_stock,
        'mouvements_jour': mouvements_jour,
        'mouvements_recents': mouvements_recents,
        'stats_mouvements': stats_mouvements,
        'chart_data': json.dumps(chart_data),
        'top_produits': top_produits,
    }
    
    return render(request, 'stock/dashboard.html', context)

@custom_login_required
def liste_produits(request):
    user_id = request.session.get('user_id')
    user = User.objects.get(id=user_id)
    
    produits = POISSON.objects.filter(actif=True).order_by('type')
    
    # Filtres
    search = request.GET.get('search', '')
    if search:
        produits = produits.filter(
            Q(type__icontains=search) | Q(code_produit__icontains=search)
        )
    
    alerte_only = request.GET.get('alerte', '')
    if alerte_only:
        produits = produits.filter(quantite_stock__lte=F('seuil_alerte'))
    
    stock_faible = request.GET.get('stock_faible', '')
    if stock_faible:
        produits = produits.filter(quantite_stock__lt=10)
    
    context = {
        'user': user,
        'produits': produits,
        'search': search,
        'alerte_only': alerte_only,
        'stock_faible': stock_faible,
    }
    
    return render(request, 'stock/liste_produits.html', context)

@custom_login_required
def ajouter_produit(request):
    user_id = request.session.get('user_id')
    user = User.objects.get(id=user_id)
    
    if request.method == 'POST':
        form = PoissonForm(request.POST)
        if form.is_valid():
            produit = form.save()
            
            # Enregistrer le mouvement initial si quantité > 0
            if produit.quantite_stock > 0:
                MouvementStock.objects.create(
                    poisson=produit,
                    type_mouvement='ENTREE',
                    quantite=produit.quantite_stock,
                    utilisateur=user,
                    motif='Stock initial à la création du produit'
                )
            
            # Log audit
            AuditLog.objects.create(
                utilisateur=user,
                action='CREATE',
                model_name='POISSON',
                object_id=produit.id,
                object_repr=str(produit)
            )
            
            messages.success(request, f'Produit {produit.type} ajouté avec succès.')
            return redirect('liste_produits')
    else:
        form = PoissonForm()
    
    return render(request, 'stock/ajouter_produit.html', {
        'form': form,
        'user': user
    })

@custom_login_required
def mouvement_stock_form(request):
    user_id = request.session.get('user_id')
    user = User.objects.get(id=user_id)
    
    if request.method == 'POST':
        form = MouvementStockForm(request.POST)
        if form.is_valid():
            mouvement = form.save(commit=False)
            mouvement.utilisateur = user
            
            # Mettre à jour le stock
            poisson = mouvement.poisson
            ancienne_quantite = poisson.quantite_stock
            
            if mouvement.type_mouvement == 'ENTREE':
                poisson.quantite_stock += mouvement.quantite
            elif mouvement.type_mouvement == 'SORTIE':
                if poisson.quantite_stock >= mouvement.quantite:
                    poisson.quantite_stock -= mouvement.quantite
                else:
                    messages.error(request, f'Stock insuffisant. Stock actuel: {poisson.quantite_stock} {poisson.unite_mesure}')
                    return render(request, 'stock/mouvement_form.html', {'form': form, 'user': user})
            elif mouvement.type_mouvement == 'AJUSTEMENT':
                poisson.quantite_stock = mouvement.quantite
            elif mouvement.type_mouvement == 'RETOUR':
                poisson.quantite_stock += mouvement.quantite
            
            # Sauvegarder
            poisson.save()
            mouvement.save()
            
            # Log audit
            AuditLog.objects.create(
                utilisateur=user,
                action='CREATE',
                model_name='MouvementStock',
                object_id=mouvement.id,
                object_repr=str(mouvement),
                details={
                    'ancienne_quantite': float(ancienne_quantite),
                    'nouvelle_quantite': float(poisson.quantite_stock),
                    'type_mouvement': mouvement.type_mouvement
                }
            )
            
            messages.success(request, f'Mouvement de stock enregistré. Nouveau stock: {poisson.quantite_stock} {poisson.unite_mesure}')
            return redirect('stock_dashboard')
    else:
        form = MouvementStockForm()
    
    return render(request, 'stock/mouvement_form.html', {
        'form': form,
        'user': user
    })

@custom_login_required
def historique_mouvements(request):
    user_id = request.session.get('user_id')
    user = User.objects.get(id=user_id)
    
    mouvements = MouvementStock.objects.select_related(
        'poisson', 'utilisateur', 'commande'
    ).order_by('-date_mouvement')
    
    # Filtres
    produit_id = request.GET.get('produit')
    if produit_id:
        mouvements = mouvements.filter(poisson_id=produit_id)
    
    type_mouvement = request.GET.get('type')
    if type_mouvement:
        mouvements = mouvements.filter(type_mouvement=type_mouvement)
    
    date_debut = request.GET.get('date_debut')
    date_fin = request.GET.get('date_fin')
    if date_debut:
        mouvements = mouvements.filter(date_mouvement__date__gte=date_debut)
    if date_fin:
        mouvements = mouvements.filter(date_mouvement__date__lte=date_fin)
    
    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(mouvements, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    produits = POISSON.objects.filter(actif=True).order_by('type')
    
    context = {
        'user': user,
        'page_obj': page_obj,
        'produits': produits,
        'filters': {
            'produit_id': produit_id,
            'type_mouvement': type_mouvement,
            'date_debut': date_debut,
            'date_fin': date_fin,
        }
    }
    
    return render(request, 'stock/historique_mouvements.html', context)

@custom_login_required
def api_stock_data(request):
    """API pour les données des graphiques"""
    periode = request.GET.get('periode', '7')  # jours
    
    try:
        jours = int(periode)
        date_debut = timezone.now() - timedelta(days=jours)
        
        # Mouvements par jour
        mouvements = MouvementStock.objects.filter(
            date_mouvement__gte=date_debut
        ).extra({'date': 'date(date_mouvement)'}).values(
            'date', 'type_mouvement'
        ).annotate(
            total=Sum('quantite')
        ).order_by('date')
        
        # Organiser les données
        data = {}
        dates_range = [(date_debut + timedelta(days=x)).date() for x in range(jours + 1)]
        
        for date_item in dates_range:
            date_str = date_item.strftime('%Y-%m-%d')
            data[date_str] = {'ENTREE': 0, 'SORTIE': 0, 'AJUSTEMENT': 0, 'RETOUR': 0}
        
        for mouvement in mouvements:
            date_str = mouvement['date'].strftime('%Y-%m-%d')
            if date_str in data:
                data[date_str][mouvement['type_mouvement']] = float(mouvement['total'])
        
        return JsonResponse({
            'success': True,
            'data': data
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@custom_login_required
def detail_produit(request, produit_id):
    user_id = request.session.get('user_id')
    user = User.objects.get(id=user_id)
    
    produit = get_object_or_404(POISSON, id=produit_id, actif=True)
    
    # Mouvements récents de ce produit
    mouvements = MouvementStock.objects.filter(
        poisson=produit
    ).select_related('utilisateur').order_by('-date_mouvement')[:20]
    
    # Statistiques du produit
    total_entrees = MouvementStock.objects.filter(
        poisson=produit,
        type_mouvement='ENTREE'
    ).aggregate(total=Sum('quantite'))['total'] or 0
    
    total_sorties = MouvementStock.objects.filter(
        poisson=produit,
        type_mouvement='SORTIE'
    ).aggregate(total=Sum('quantite'))['total'] or 0
    
    context = {
        'user': user,
        'produit': produit,
        'mouvements': mouvements,
        'total_entrees': total_entrees,
        'total_sorties': total_sorties,
        'est_en_alerte': produit.quantite_stock <= produit.seuil_alerte
    }
    
    return render(request, 'stock/detail_produit.html', context)

@custom_login_required
def rapport_stock(request):
    user_id = request.session.get('user_id')
    user = User.objects.get(id=user_id)
    
    # Rapport détaillé du stock
    produits = POISSON.objects.filter(actif=True).annotate(
        valeur_stock=F('quantite_stock') * F('prix')
    ).order_by('type')
    
    # Statistiques globales
    stats = {
        'total_produits': produits.count(),
        'valeur_totale': produits.aggregate(total=Sum('valeur_stock'))['total'] or 0,
        'produits_alerte': produits.filter(quantite_stock__lte=F('seuil_alerte')).count(),
        'stock_zero': produits.filter(quantite_stock=0).count(),
    }
    
    # Mouvements du mois
    premier_jour_mois = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    mouvements_mois = MouvementStock.objects.filter(
        date_mouvement__gte=premier_jour_mois
    ).values('type_mouvement').annotate(
        total=Sum('quantite'),
        count=Count('id')
    )
    
    context = {
        'user': user,
        'produits': produits,
        'stats': stats,
        'mouvements_mois': mouvements_mois,
    }
    
    return render(request, 'stock/rapport.html', context)

@custom_login_required
def rapport_stock_pdf(request):
    """Génère un rapport PDF du stock"""
    user_id = request.session.get('user_id')
    user = User.objects.get(id=user_id)
    
    # Créer la réponse HTTP pour PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="rapport_stock_{timezone.now().strftime("%Y%m%d_%H%M")}.pdf"'
    
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
    title = Paragraph("RAPPORT DE STOCK", title_style)
    story.append(title)
    story.append(Spacer(1, 12))
    
    # Date et heure
    date_rapport = Paragraph(f"Généré le {timezone.now().strftime('%d/%m/%Y à %H:%M')}", styles['Normal'])
    story.append(date_rapport)
    story.append(Spacer(1, 20))
    
    # Données du stock
    produits = POISSON.objects.filter(actif=True).annotate(
        valeur_stock=F('quantite_stock') * F('prix')
    ).order_by('type')
    
    # Statistiques globales
    stats = {
        'total_produits': produits.count(),
        'valeur_totale': produits.aggregate(total=Sum('valeur_stock'))['total'] or 0,
        'produits_alerte': produits.filter(quantite_stock__lte=F('seuil_alerte')).count(),
        'stock_zero': produits.filter(quantite_stock=0).count(),
    }
    
    # Tableau des statistiques
    stats_data = [
        ['Statistiques Générales', ''],
        ['Total produits actifs', str(stats['total_produits'])],
        ['Valeur totale du stock', f"{stats['valeur_totale']:.2f} MAD"],
        ['Produits en alerte', str(stats['produits_alerte'])],
        ['Produits en rupture', str(stats['stock_zero'])],
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
    
    # Titre détail des produits
    detail_title = Paragraph("DÉTAIL DES STOCKS", styles['Heading2'])
    story.append(detail_title)
    story.append(Spacer(1, 12))
    
    # Tableau des produits
    data = [['Code', 'Type', 'Prix Unit.', 'Stock', 'Seuil', 'Valeur', 'Statut']]
    
    for produit in produits:
        if produit.quantite_stock <= 0:
            statut = "RUPTURE"
        elif produit.quantite_stock <= produit.seuil_alerte:
            statut = "ALERTE"
        else:
            statut = "OK"
            
        data.append([
            produit.code_produit or "N/A",
            produit.type,
            f"{produit.prix:.2f}",
            f"{produit.quantite_stock:.2f}",
            f"{produit.seuil_alerte:.2f}",
            f"{float(produit.quantite_stock) * float(produit.prix):.2f}",
            statut
        ])
    
    # Ligne de total
    data.append([
        '', '', '', '', '', 
        f"{stats['valeur_totale']:.2f} MAD", 
        'TOTAL'
    ])
    
    table = Table(data, colWidths=[1*inch, 1.5*inch, 0.8*inch, 0.8*inch, 0.8*inch, 1*inch, 0.8*inch])
    table.setStyle(TableStyle([
        # En-tête
        ('BACKGROUND', (0, 0), (-1, 0), colors.navy),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        
        # Corps du tableau
        ('BACKGROUND', (0, 1), (-1, -2), colors.white),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        
        # Ligne de total
        ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        
        # Coloration conditionnelle pour les statuts
        ('TEXTCOLOR', (6, 1), (6, -2), colors.red),  # Colonne statut en rouge par défaut
    ]))
    
    # Appliquer les couleurs selon le statut
    for i, produit in enumerate(produits, 1):
        if produit.quantite_stock <= 0:
            table.setStyle(TableStyle([('BACKGROUND', (0, i), (-1, i), colors.pink)]))
        elif produit.quantite_stock <= produit.seuil_alerte:
            table.setStyle(TableStyle([('BACKGROUND', (0, i), (-1, i), colors.yellow)]))
    
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
        model_name='Stock',
        object_id=0,
        object_repr="Rapport stock PDF",
        details={'format': 'PDF', 'produits_count': produits.count()}
    )
    
    return response

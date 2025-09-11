from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count
from django.http import JsonResponse, HttpResponse, Http404
from django.utils import timezone
from django.core.files.storage import default_storage
from django.conf import settings
from django.template.loader import render_to_string
from django.http import FileResponse
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from .models import (
    Commande, LigneCommande, CLIENT, POISSON, User, Document, 
    Facture, Livraison, EtapeTransport, MouvementStock
)
from .forms import (
    CommandeForm, LigneCommandeForm, DocumentForm, FactureForm, 
    LivraisonForm, EtapeTransportForm
)
from decimal import Decimal
import os
from datetime import datetime, timedelta
from django.db import transaction

def commande_dashboard(request):
    """Dashboard des commandes avec statistiques"""
    if not request.session.get('user_id'):
        return redirect('login')
    
    # Statistiques générales
    total_commandes = Commande.objects.count()
    commandes_en_cours = Commande.objects.filter(
        statut__in=['BROUILLON', 'CONFIRMEE', 'PREPARATION', 'EXPEDIEE']
    ).count()
    commandes_livrees = Commande.objects.filter(statut='LIVREE').count()
    ca_total = Commande.objects.filter(statut='LIVREE').aggregate(
        total=Sum('lignecommande__total_ligne')
    )['total'] or 0
    
    # Commandes récentes
    commandes_recentes = Commande.objects.select_related('client').order_by('-date_creation')[:10]
    
    # Commandes par statut (pour graphique)
    stats_statut = Commande.objects.values('statut').annotate(
        count=Count('id')
    ).order_by('statut')
    
    # CA par mois (6 derniers mois)
    ca_mensuel = []
    for i in range(6):
        date_debut = timezone.now().replace(day=1) - timedelta(days=i*30)
        date_fin = date_debut + timedelta(days=30)
        ca = Commande.objects.filter(
            date_creation__range=[date_debut, date_fin],
            statut='LIVREE'
        ).aggregate(total=Sum('lignecommande__total_ligne'))['total'] or 0
        ca_mensuel.append({
            'mois': date_debut.strftime('%m/%Y'),
            'ca': float(ca)
        })
    
    context = {
        'total_commandes': total_commandes,
        'commandes_en_cours': commandes_en_cours,
        'commandes_livrees': commandes_livrees,
        'ca_total': ca_total,
        'commandes_recentes': commandes_recentes,
        'stats_statut': list(stats_statut),
        'ca_mensuel': list(reversed(ca_mensuel))
    }
    
    return render(request, 'commandes/dashboard.html', context)

def liste_commandes(request):
    """Liste des commandes avec filtres et pagination"""
    if not request.session.get('user_id'):
        return redirect('login')
    
    commandes = Commande.objects.select_related('client').order_by('-date_creation')
    
    # Filtres
    search = request.GET.get('search', '')
    statut_filter = request.GET.get('statut', '')
    type_filter = request.GET.get('type', '')
    client_filter = request.GET.get('client', '')
    date_debut = request.GET.get('date_debut', '')
    date_fin = request.GET.get('date_fin', '')
    
    if search:
        commandes = commandes.filter(
            Q(numero_commande__icontains=search) |
            Q(client__nom_societe__icontains=search) |
            Q(commentaire__icontains=search)
        )
    
    if statut_filter:
        commandes = commandes.filter(statut=statut_filter)
    
    if type_filter:
        commandes = commandes.filter(type_commande=type_filter)
    
    if client_filter:
        commandes = commandes.filter(client_id=client_filter)
    
    if date_debut:
        commandes = commandes.filter(date_creation__gte=date_debut)
    
    if date_fin:
        commandes = commandes.filter(date_creation__lte=date_fin)
    
    # Pagination
    paginator = Paginator(commandes, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Données pour les filtres
    clients = CLIENT.objects.filter(actif=True).order_by('nom_societe')
    statuts = Commande.STATUT_CHOICES
    types = Commande.TYPE_CHOICES
    
    context = {
        'page_obj': page_obj,
        'clients': clients,
        'statuts': statuts,
        'types': types,
        'search': search,
        'statut_filter': statut_filter,
        'type_filter': type_filter,
        'client_filter': client_filter,
        'date_debut': date_debut,
        'date_fin': date_fin,
    }
    
    return render(request, 'commandes/liste.html', context)

def ajouter_commande(request):
    """Ajouter une nouvelle commande"""
    if not request.session.get('user_id'):
        return redirect('login')
    
    if request.method == 'POST':
        form = CommandeForm(request.POST)
        if form.is_valid():
            commande = form.save(commit=False)
            user = User.objects.get(id=request.session['user_id'])
            commande.utilisateur_creation = user
            commande.save()
            
            messages.success(request, f'Commande {commande.numero_commande} créée avec succès.')
            return redirect('detail_commande', commande_id=commande.id)
    else:
        form = CommandeForm()
    
    return render(request, 'commandes/ajouter.html', {'form': form})

def detail_commande(request, commande_id):
    """Détail d'une commande avec ses lignes et documents"""
    if not request.session.get('user_id'):
        return redirect('login')
    
    commande = get_object_or_404(Commande, id=commande_id)
    lignes = LigneCommande.objects.filter(commande=commande).select_related('poisson')
    documents = Document.objects.filter(commande=commande).order_by('-date_ajout')
    factures = Facture.objects.filter(commande=commande)
    livraisons = Livraison.objects.filter(commande=commande)
    etapes_transport = EtapeTransport.objects.filter(commande=commande).order_by('date_depart')
    
    # Calcul du total
    total_commande = sum(ligne.total_ligne or 0 for ligne in lignes)
    
    context = {
        'commande': commande,
        'lignes': lignes,
        'documents': documents,
        'factures': factures,
        'livraisons': livraisons,
        'etapes_transport': etapes_transport,
        'total_commande': total_commande,
    }
    
    return render(request, 'commandes/detail.html', context)

def modifier_commande(request, commande_id):
    """Modifier une commande existante"""
    if not request.session.get('user_id'):
        return redirect('login')
    
    commande = get_object_or_404(Commande, id=commande_id)
    
    if request.method == 'POST':
        form = CommandeForm(request.POST, instance=commande)
        if form.is_valid():
            form.save()
            messages.success(request, 'Commande modifiée avec succès.')
            return redirect('detail_commande', commande_id=commande.id)
    else:
        form = CommandeForm(instance=commande)
    
    context = {
        'form': form,
        'commande': commande
    }
    
    return render(request, 'commandes/modifier.html', context)

def ajouter_ligne_commande(request, commande_id):
    """Ajouter une ligne à une commande"""
    if not request.session.get('user_id'):
        return redirect('login')
    
    commande = get_object_or_404(Commande, id=commande_id)
    
    if request.method == 'POST':
        form = LigneCommandeForm(request.POST)
        if form.is_valid():
            ligne = form.save(commit=False)
            ligne.commande = commande
            ligne.save()
            
            messages.success(request, 'Ligne ajoutée à la commande.')
            return redirect('detail_commande', commande_id=commande.id)
    else:
        form = LigneCommandeForm()
    
    context = {
        'form': form,
        'commande': commande
    }
    
    return render(request, 'commandes/ajouter_ligne.html', context)

def modifier_ligne_commande(request, ligne_id):
    """Modifier une ligne de commande"""
    if not request.session.get('user_id'):
        return redirect('login')
    
    ligne = get_object_or_404(LigneCommande, id=ligne_id)
    
    if request.method == 'POST':
        form = LigneCommandeForm(request.POST, instance=ligne)
        if form.is_valid():
            form.save()
            messages.success(request, 'Ligne modifiée avec succès.')
            return redirect('detail_commande', commande_id=ligne.commande.id)
    else:
        form = LigneCommandeForm(instance=ligne)
    
    context = {
        'form': form,
        'ligne': ligne,
        'commande': ligne.commande
    }
    
    return render(request, 'commandes/modifier_ligne.html', context)

def supprimer_ligne_commande(request, ligne_id):
    """Supprimer une ligne de commande"""
    if not request.session.get('user_id'):
        return redirect('login')
    
    ligne = get_object_or_404(LigneCommande, id=ligne_id)
    commande_id = ligne.commande.id
    
    if request.method == 'POST':
        ligne.delete()
        messages.success(request, 'Ligne supprimée avec succès.')
        return redirect('detail_commande', commande_id=commande_id)
    
    return render(request, 'commandes/supprimer_ligne.html', {'ligne': ligne})

# === GESTION DES DOCUMENTS ===

def ajouter_document(request, commande_id):
    """Ajouter un document à une commande"""
    if not request.session.get('user_id'):
        return redirect('login')
    
    commande = get_object_or_404(Commande, id=commande_id)
    
    if request.method == 'POST':
        form = DocumentForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save(commit=False)
            document.commande = commande
            user = User.objects.get(id=request.session['user_id'])
            document.utilisateur = user
            document.save()
            
            messages.success(request, 'Document ajouté avec succès.')
            return redirect('detail_commande', commande_id=commande.id)
    else:
        form = DocumentForm()
    
    context = {
        'form': form,
        'commande': commande
    }
    
    return render(request, 'commandes/ajouter_document.html', context)

def telecharger_document(request, document_id):
    """Télécharger un document"""
    if not request.session.get('user_id'):
        return redirect('login')
    
    document = get_object_or_404(Document, id=document_id)
    
    if default_storage.exists(document.fichier.name):
        response = HttpResponse(
            default_storage.open(document.fichier.name).read(),
            content_type='application/octet-stream'
        )
        response['Content-Disposition'] = f'attachment; filename="{document.nom_document}"'
        return response
    else:
        raise Http404("Document non trouvé")

def supprimer_document(request, document_id):
    """Supprimer un document"""
    if not request.session.get('user_id'):
        return redirect('login')
    
    document = get_object_or_404(Document, id=document_id)
    commande_id = document.commande.id
    
    if request.method == 'POST':
        # Supprimer le fichier physique
        if default_storage.exists(document.fichier.name):
            default_storage.delete(document.fichier.name)
        
        document.delete()
        messages.success(request, 'Document supprimé avec succès.')
        return redirect('detail_commande', commande_id=commande_id)
    
    return render(request, 'commandes/supprimer_document.html', {
        'document': document,
        'commande': document.commande
    })

# === GESTION DES FACTURES ===

def generer_facture(request, commande_id):
    """Générer une facture pour une commande"""
    if not request.session.get('user_id'):
        return redirect('login')
    
    commande = get_object_or_404(Commande, id=commande_id)
    lignes = LigneCommande.objects.filter(commande=commande)
    
    if request.method == 'POST':
        form = FactureForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                facture = form.save(commit=False)
                facture.commande = commande
                facture.client = commande.client
                user = User.objects.get(id=request.session['user_id'])
                facture.utilisateur_creation = user
                
                # Calculer les montants
                montant_ht = sum(ligne.total_ligne or 0 for ligne in lignes)
                facture.montant_ht = montant_ht
                
                # Générer numéro de facture
                timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
                facture.numero_facture = f"FAC{timestamp}"
                
                facture.save()
                
                # Associer les lignes de commande
                facture.ligne_commande.set(lignes)
                
                messages.success(request, f'Facture {facture.numero_facture} générée avec succès.')
                return redirect('detail_facture', facture_id=facture.id)
    else:
        # Pré-remplir le formulaire
        montant_ht = sum(ligne.total_ligne or 0 for ligne in lignes)
        initial_data = {
            'montant_ht': montant_ht,
            'date_echeance': timezone.now() + timedelta(days=30)
        }
        form = FactureForm(initial=initial_data)
    
    context = {
        'form': form,
        'commande': commande,
        'lignes': lignes,
        'montant_ht': sum(ligne.total_ligne or 0 for ligne in lignes)
    }
    
    return render(request, 'commandes/generer_facture.html', context)

def detail_facture(request, facture_id):
    """Détail d'une facture"""
    if not request.session.get('user_id'):
        return redirect('login')
    
    facture = get_object_or_404(Facture, id=facture_id)
    lignes = facture.ligne_commande.all()
    
    context = {
        'facture': facture,
        'lignes': lignes
    }
    
    return render(request, 'commandes/detail_facture.html', context)

def liste_factures(request):
    """Liste des factures"""
    if not request.session.get('user_id'):
        return redirect('login')
    
    factures = Facture.objects.select_related('client', 'commande').order_by('-date_emission')
    
    # Filtres
    search = request.GET.get('search', '')
    statut_filter = request.GET.get('statut', '')
    client_filter = request.GET.get('client', '')
    
    if search:
        factures = factures.filter(
            Q(numero_facture__icontains=search) |
            Q(client__nom_societe__icontains=search)
        )
    
    if statut_filter:
        factures = factures.filter(statut=statut_filter)
    
    if client_filter:
        factures = factures.filter(client_id=client_filter)
    
    # Pagination
    paginator = Paginator(factures, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search': search,
        'statut_filter': statut_filter,
        'client_filter': client_filter,
    }
    
    return render(request, 'commandes/liste_factures.html', context)

# === GESTION DES LIVRAISONS ===

def ajouter_livraison(request, commande_id):
    """Ajouter une livraison à une commande"""
    if not request.session.get('user_id'):
        return redirect('login')
    
    commande = get_object_or_404(Commande, id=commande_id)
    
    if request.method == 'POST':
        form = LivraisonForm(request.POST)
        if form.is_valid():
            livraison = form.save(commit=False)
            livraison.commande = commande
            livraison.save()
            
            messages.success(request, 'Livraison programmée avec succès.')
            return redirect('detail_commande', commande_id=commande.id)
    else:
        form = LivraisonForm()
    
    context = {
        'form': form,
        'commande': commande
    }
    
    return render(request, 'commandes/ajouter_livraison.html', context)

# === GESTION DU TRANSPORT ===

def ajouter_etape_transport(request, commande_id):
    """Ajouter une étape de transport"""
    if not request.session.get('user_id'):
        return redirect('login')
    
    commande = get_object_or_404(Commande, id=commande_id)
    
    # Vérifier que ce n'est pas une commande locale
    if commande.type_commande == 'LOCAL':
        messages.error(request, 'Les étapes de transport ne sont pas disponibles pour les commandes locales.')
        return redirect('detail_commande', commande_id=commande.id)
    
    if request.method == 'POST':
        form = EtapeTransportForm(request.POST)
        if form.is_valid():
            etape = form.save(commit=False)
            etape.commande = commande
            etape.save()
            
            messages.success(request, 'Étape de transport ajoutée avec succès.')
            return redirect('detail_commande', commande_id=commande.id)
    else:
        form = EtapeTransportForm()
    
    context = {
        'form': form,
        'commande': commande
    }
    
    return render(request, 'commandes/ajouter_etape_transport.html', context)

def changer_statut_commande(request, commande_id):
    """Changer le statut d'une commande"""
    if not request.session.get('user_id'):
        return redirect('login')
    
    commande = get_object_or_404(Commande, id=commande_id)
    nouveau_statut = request.POST.get('statut')
    ancien_statut = commande.statut
    
    if nouveau_statut in dict(Commande.STATUT_CHOICES):
        commande.statut = nouveau_statut
        commande.save()
        
        # Gestion automatique des mouvements de stock selon le type de commande
        if nouveau_statut == 'CONFIRMEE' and ancien_statut != 'CONFIRMEE':
            # Quand une commande est confirmée, gérer le stock selon le type
            for ligne in commande.lignecommande_set.all():
                if commande.type_commande == 'EXPORT':
                    # Pour l'export : diminuer le stock (sortie de produits)
                    if ligne.poisson.quantite_stock >= ligne.quantite:
                        MouvementStock.objects.create(
                            poisson=ligne.poisson,
                            type_mouvement='SORTIE',
                            quantite=ligne.quantite,
                            commande=commande,
                            utilisateur_id=request.session['user_id'],
                            motif=f'Confirmation commande EXPORT {commande.numero_commande}'
                        )
                        # Mettre à jour le stock
                        ligne.poisson.quantite_stock -= ligne.quantite
                        ligne.poisson.save()
                        
                        messages.info(request, f'Stock diminué de {ligne.quantite} {ligne.poisson.unite_mesure} pour {ligne.poisson.type}')
                    else:
                        messages.warning(request, f'Stock insuffisant pour {ligne.poisson.type} (disponible: {ligne.poisson.quantite_stock}, demandé: {ligne.quantite})')
                
                elif commande.type_commande == 'IMPORT':
                    # Pour l'import : augmenter le stock (entrée de produits)
                    MouvementStock.objects.create(
                        poisson=ligne.poisson,
                        type_mouvement='ENTREE',
                        quantite=ligne.quantite,
                        commande=commande,
                        utilisateur_id=request.session['user_id'],
                        motif=f'Confirmation commande IMPORT {commande.numero_commande}'
                    )
                    # Mettre à jour le stock
                    ligne.poisson.quantite_stock += ligne.quantite
                    ligne.poisson.save()
                    
                    messages.info(request, f'Stock augmenté de {ligne.quantite} {ligne.poisson.unite_mesure} pour {ligne.poisson.type}')
                
                elif commande.type_commande == 'LOCAL':
                    # Pour le local : diminuer le stock (vente locale)
                    if ligne.poisson.quantite_stock >= ligne.quantite:
                        MouvementStock.objects.create(
                            poisson=ligne.poisson,
                            type_mouvement='SORTIE',
                            quantite=ligne.quantite,
                            commande=commande,
                            utilisateur_id=request.session['user_id'],
                            motif=f'Confirmation commande LOCAL {commande.numero_commande}'
                        )
                        # Mettre à jour le stock
                        ligne.poisson.quantite_stock -= ligne.quantite
                        ligne.poisson.save()
                        
                        messages.info(request, f'Stock diminué de {ligne.quantite} {ligne.poisson.unite_mesure} pour {ligne.poisson.type}')
                    else:
                        messages.warning(request, f'Stock insuffisant pour {ligne.poisson.type} (disponible: {ligne.poisson.quantite_stock}, demandé: {ligne.quantite})')
        
        # Gestion pour annulation d'une commande confirmée (restaurer le stock)
        elif nouveau_statut == 'ANNULEE' and ancien_statut == 'CONFIRMEE':
            for ligne in commande.lignecommande_set.all():
                if commande.type_commande in ['EXPORT', 'LOCAL']:
                    # Restaurer le stock (annuler la sortie)
                    MouvementStock.objects.create(
                        poisson=ligne.poisson,
                        type_mouvement='RETOUR',
                        quantite=ligne.quantite,
                        commande=commande,
                        utilisateur_id=request.session['user_id'],
                        motif=f'Annulation commande {commande.type_commande} {commande.numero_commande}'
                    )
                    # Remettre le stock
                    ligne.poisson.quantite_stock += ligne.quantite
                    ligne.poisson.save()
                    
                    messages.info(request, f'Stock restauré: +{ligne.quantite} {ligne.poisson.unite_mesure} pour {ligne.poisson.type}')
                
                elif commande.type_commande == 'IMPORT':
                    # Annuler l'entrée de stock
                    MouvementStock.objects.create(
                        poisson=ligne.poisson,
                        type_mouvement='AJUSTEMENT',
                        quantite=-ligne.quantite,
                        commande=commande,
                        utilisateur_id=request.session['user_id'],
                        motif=f'Annulation commande IMPORT {commande.numero_commande}'
                    )
                    # Diminuer le stock (annuler l'import)
                    ligne.poisson.quantite_stock -= ligne.quantite
                    if ligne.poisson.quantite_stock < 0:
                        ligne.poisson.quantite_stock = 0
                    ligne.poisson.save()
                    
                    messages.info(request, f'Stock ajusté: -{ligne.quantite} {ligne.poisson.unite_mesure} pour {ligne.poisson.type}')
        
        # Gestion pour livraison (si pas déjà fait à la confirmation)
        elif nouveau_statut == 'LIVREE' and commande.type_commande in ['EXPORT', 'LOCAL'] and ancien_statut != 'CONFIRMEE':
            # Seulement si le stock n'a pas été déjà géré à la confirmation
            for ligne in commande.lignecommande_set.all():
                # Vérifier si un mouvement de stock existe déjà pour cette commande
                mouvement_existant = MouvementStock.objects.filter(
                    commande=commande,
                    poisson=ligne.poisson,
                    type_mouvement='SORTIE'
                ).exists()
                
                if not mouvement_existant:
                    if ligne.poisson.quantite_stock >= ligne.quantite:
                        MouvementStock.objects.create(
                            poisson=ligne.poisson,
                            type_mouvement='SORTIE',
                            quantite=ligne.quantite,
                            commande=commande,
                            utilisateur_id=request.session['user_id'],
                            motif=f'Livraison commande {commande.numero_commande}'
                        )
                        # Mettre à jour le stock
                        ligne.poisson.quantite_stock -= ligne.quantite
                        ligne.poisson.save()
                    else:
                        messages.warning(request, f'Stock insuffisant pour livraison: {ligne.poisson.type}')
        
        messages.success(request, f'Statut changé vers "{dict(Commande.STATUT_CHOICES)[nouveau_statut]}"')
    
    return redirect('detail_commande', commande_id=commande_id)

def rapport_commandes(request):
    """Rapport des commandes"""
    if not request.session.get('user_id'):
        return redirect('login')
    
    # Filtres de date
    date_debut = request.GET.get('date_debut', (timezone.now() - timedelta(days=30)).date())
    date_fin = request.GET.get('date_fin', timezone.now().date())
    
    commandes = Commande.objects.filter(
        date_creation__date__range=[date_debut, date_fin]
    ).select_related('client')
    
    # Statistiques
    ca_total = commandes.filter(statut='LIVREE').aggregate(
        total=Sum('lignecommande__total_ligne')
    )['total'] or 0
    
    total_commandes = commandes.count()
    panier_moyen = ca_total / total_commandes if total_commandes > 0 else 0
    
    stats = {
        'total_commandes': total_commandes,
        'ca_total': ca_total,
        'panier_moyen': panier_moyen,
        'commandes_par_statut': commandes.values('statut').annotate(
            count=Count('id')
        ),
        'commandes_par_type': commandes.values('type_commande').annotate(
            count=Count('id')
        ),
        'top_clients': commandes.values(
            'client__nom_societe'
        ).annotate(
            nb_commandes=Count('id'),
            ca=Sum('lignecommande__total_ligne')
        ).order_by('-ca')[:10]
    }
    
    context = {
        'commandes': commandes,
        'stats': stats,
        'date_debut': date_debut,
        'date_fin': date_fin,
    }
    
    return render(request, 'commandes/rapport.html', context)

def api_commandes_data(request):
    """API pour les données de commandes (graphiques)"""
    if not request.session.get('user_id'):
        return JsonResponse({'error': 'Non autorisé'}, status=401)
    
    periode = int(request.GET.get('periode', 30))
    date_debut = timezone.now() - timedelta(days=periode)
    
    # CA par jour
    ca_quotidien = {}
    for i in range(periode):
        date = (timezone.now() - timedelta(days=i)).date()
        ca = Commande.objects.filter(
            date_creation__date=date,
            statut='LIVREE'
        ).aggregate(total=Sum('lignecommande__total_ligne'))['total'] or 0
        ca_quotidien[date.isoformat()] = float(ca)
    
    return JsonResponse({
        'success': True,
        'ca_quotidien': ca_quotidien
    })

def telecharger_facture_pdf(request, facture_id):
    """Générer et télécharger une facture en PDF"""
    if not request.session.get('user_id'):
        return redirect('login')
    
    facture = get_object_or_404(Facture, id=facture_id)
    lignes = facture.ligne_commande.all()
    
    # Créer un buffer pour le PDF
    buffer = io.BytesIO()
    
    # Créer le document PDF
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72,
                           topMargin=72, bottomMargin=18)
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        textColor=colors.HexColor('#2563eb'),
        alignment=1  # Center alignment
    )
    
    header_style = ParagraphStyle(
        'HeaderStyle',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.HexColor('#1e40af'),
        spaceAfter=12
    )
    
    # Contenu du PDF
    elements = []
    
    # En-tête avec logo virtuel
    elements.append(Paragraph(f"FACTURE {facture.numero_facture}", title_style))
    elements.append(Spacer(1, 20))
    
    # Informations de l'entreprise et du client
    company_data = [
        ['VOTRE ENTREPRISE', f'Facturé à: {facture.client.nom_societe}'],
        ['Export/Import Poisson', facture.client.adresse or 'Adresse non renseignée'],
        ['Casablanca, Maroc', f'Email: {facture.client.email}'],
        ['Tél: +212 xxx xxx xxx', f'ICE: {facture.client.numero_ice or "N/A"}'],
        ['Email: contact@entreprise.ma', f'RC: {facture.client.numero_registre_commerce or "N/A"}'],
        ['', ''],
        ['Date émission:', facture.date_emission.strftime("%d/%m/%Y")],
        ['Date échéance:', facture.date_echeance.strftime("%d/%m/%Y")],
        ['Mode de paiement:', facture.get_mode_paiement_display()],
        ['Statut:', facture.get_statut_display()],
    ]
    
    company_table = Table(company_data, colWidths=[3*inch, 3*inch])
    company_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, 4), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BACKGROUND', (0, 0), (0, 4), colors.HexColor('#f0f9ff')),
        ('BACKGROUND', (1, 0), (1, 0), colors.HexColor('#f0f9ff')),
        ('LINEBELOW', (0, 5), (-1, 5), 1, colors.HexColor('#e2e8f0')),
        ('FONTNAME', (0, 6), (-1, -1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0, 6), (-1, -1), colors.HexColor('#2563eb')),
    ]))
    
    elements.append(company_table)
    elements.append(Spacer(1, 30))
    
    # Titre du tableau des articles
    elements.append(Paragraph("DÉTAIL DES ARTICLES", header_style))
    elements.append(Spacer(1, 10))
    
    # Tableau des articles
    articles_data = [['Produit', 'Code', 'Quantité', 'Prix Unitaire', 'Total HT']]
    
    for ligne in lignes:
        articles_data.append([
            ligne.poisson.type,
            ligne.poisson.code_produit,
            f"{ligne.quantite} {ligne.poisson.unite_mesure}",
            f"{ligne.prix_unitaire} MAD",
            f"{ligne.total_ligne} MAD"
        ])
    
    articles_table = Table(articles_data, colWidths=[2*inch, 1*inch, 1.5*inch, 1.5*inch, 1.5*inch])
    articles_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2563eb')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('TOPPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
        ('ALIGN', (3, 1), (-1, -1), 'RIGHT'),  # Aligner les montants à droite
    ]))
    
    elements.append(articles_table)
    elements.append(Spacer(1, 30))
    
    # Totaux
    totaux_data = [
        ['', '', '', 'Sous-total HT:', f"{facture.montant_ht} MAD"],
        ['', '', '', f'TVA ({facture.taux_tva}%):', f"{facture.montant_tva} MAD"],
        ['', '', '', 'Total TTC:', f"{facture.montant_ttc} MAD"],
    ]
    
    totaux_table = Table(totaux_data, colWidths=[1.5*inch, 1.5*inch, 1.5*inch, 1.5*inch, 1.5*inch])
    totaux_table.setStyle(TableStyle([
        ('ALIGN', (3, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (3, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (3, 0), (-1, -1), 11),
        ('FONTNAME', (3, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (3, -1), (-1, -1), 14),
        ('BACKGROUND', (3, -1), (-1, -1), colors.HexColor('#f0fdf4')),
        ('TEXTCOLOR', (3, -1), (-1, -1), colors.HexColor('#059669')),
        ('LINEABOVE', (3, -1), (-1, -1), 2, colors.HexColor('#059669')),
        ('BOTTOMPADDING', (3, 0), (-1, -1), 10),
        ('TOPPADDING', (3, 0), (-1, -1), 10),
        ('GRID', (3, 0), (-1, -1), 1, colors.HexColor('#e2e8f0')),
    ]))
    
    elements.append(totaux_table)
    elements.append(Spacer(1, 40))
    
    # Pied de page avec conditions
    footer_text = """
    <para align="center" fontSize="8" textColor="#6b7280">
    <b>CONDITIONS DE PAIEMENT:</b><br/>
    Paiement à réception de facture - Tout retard de paiement entraînera des pénalités<br/>
    En cas de retard de paiement, une pénalité de 3 fois le taux d'intérêt légal sera appliquée<br/>
    <br/>
    <b>Merci de votre confiance</b>
    </para>
    """
    elements.append(Paragraph(footer_text, styles['Normal']))
    
    # Construire le PDF
    doc.build(elements)
    
    # Récupérer le contenu du buffer
    buffer.seek(0)
    
    # Créer la réponse HTTP avec headers pour forcer le téléchargement
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    filename = f"facture_{facture.numero_facture}_{facture.client.nom_societe.replace(' ', '_')}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response['Content-Length'] = len(buffer.getvalue())
    
    return response

def generer_bon_commande(request, commande_id):
    """Générer un bon de commande en PDF et le stocker automatiquement"""
    if not request.session.get('user_id'):
        return redirect('login')
    
    commande = get_object_or_404(Commande, id=commande_id)
    lignes = LigneCommande.objects.filter(commande=commande).select_related('poisson')
    
    # Vérifier si un bon de commande existe déjà
    bon_existant = Document.objects.filter(
        commande=commande,
        type='bon_commande'
    ).first()
    
    if bon_existant:
        messages.warning(request, 'Un bon de commande existe déjà pour cette commande.')
        return redirect('detail_commande', commande_id=commande.id)
    
    try:
        # Créer un buffer pour le PDF
        buffer = io.BytesIO()
        
        # Créer le document PDF
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72,
                               topMargin=72, bottomMargin=18)
        
        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            textColor=colors.HexColor('#2563eb'),
            alignment=1  # Center alignment
        )
        
        header_style = ParagraphStyle(
            'HeaderStyle',
            parent=styles['Normal'],
            fontSize=12,
            textColor=colors.HexColor('#1e40af'),
            spaceAfter=12
        )
        
        # Contenu du PDF
        elements = []
        
        # En-tête
        elements.append(Paragraph(f"BON DE COMMANDE N° {commande.numero_commande}", title_style))
        elements.append(Spacer(1, 20))
        
        # Informations de l'entreprise et du client
        company_data = [
            ['VOTRE ENTREPRISE', f'Client: {commande.client.nom_societe}'],
            ['Export/Import Poisson', commande.client.adresse or 'Adresse non renseignée'],
            ['Casablanca, Maroc', f'Email: {commande.client.email}'],
            ['Tél: +212 xxx xxx xxx', f'Téléphone: {commande.client.telephone or "N/A"}'],
            ['Email: contact@entreprise.ma', f'ICE: {commande.client.numero_ice or "N/A"}'],
            ['', ''],
            ['Date de commande:', commande.date_creation.strftime("%d/%m/%Y")],
            ['Type de commande:', commande.get_type_commande_display()],
            ['Statut:', commande.get_statut_display()],
        ]
        
        # Ajouter Incoterm seulement pour Export/Import
        if commande.type_commande != 'LOCAL':
            company_data.append(['Incoterm:', commande.get_incoterm_display() if commande.incoterm else "N/A"])
        
        company_table = Table(company_data, colWidths=[3*inch, 3*inch])
        company_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, 4), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BACKGROUND', (0, 0), (0, 4), colors.HexColor('#f0f9ff')),
            ('BACKGROUND', (1, 0), (1, 0), colors.HexColor('#f0f9ff')),
            ('LINEBELOW', (0, 5), (-1, 5), 1, colors.HexColor('#e2e8f0')),
            ('FONTNAME', (0, 6), (-1, -1), 'Helvetica-Bold'),
            ('TEXTCOLOR', (0, 6), (-1, -1), colors.HexColor('#2563eb')),
        ]))
        
        elements.append(company_table)
        elements.append(Spacer(1, 30))
        
        # Titre du tableau des articles
        elements.append(Paragraph("DÉTAIL DE LA COMMANDE", header_style))
        elements.append(Spacer(1, 10))
        
        # Tableau des articles
        articles_data = [['Produit', 'Code', 'Quantité', 'Prix Unitaire (MAD)', 'Total (MAD)']]
        
        total_general = 0
        for ligne in lignes:
            total_ligne = ligne.total_ligne or 0
            total_general += total_ligne
            articles_data.append([
                ligne.poisson.type,
                ligne.poisson.code_produit,
                f"{ligne.quantite} {ligne.poisson.unite_mesure}",
                f"{ligne.prix_unitaire}",
                f"{total_ligne}"
            ])
        
        # Ajouter ligne de total
        articles_data.append(['', '', '', 'TOTAL GÉNÉRAL:', f"{total_general}"])
        
        articles_table = Table(articles_data, colWidths=[2*inch, 1*inch, 1.5*inch, 1.5*inch, 1.5*inch])
        articles_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2563eb')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('TOPPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ROWBACKGROUNDS', (0, 1), (-2, -1), [colors.white, colors.HexColor('#f8fafc')]),
            ('ALIGN', (3, 1), (-1, -1), 'RIGHT'),
            # Style pour la ligne de total
            ('BACKGROUND', (-1, -1), (-1, -1), colors.HexColor('#f0fdf4')),
            ('FONTNAME', (-2, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (-2, -1), (-1, -1), 11),
        ]))
        
        elements.append(articles_table)
        elements.append(Spacer(1, 30))
        
        # Commentaires si disponibles
        if commande.commentaire:
            elements.append(Paragraph("COMMENTAIRES:", header_style))
            elements.append(Paragraph(commande.commentaire, styles['Normal']))
            elements.append(Spacer(1, 20))
        
        # Conditions générales
        conditions_text = """
        <para align="left" fontSize="10" textColor="#374151">
        <b>CONDITIONS GÉNÉRALES:</b><br/>
        • Les prix sont exprimés en dirhams marocains (MAD)<br/>
        • La livraison sera effectuée selon les termes convenus<br/>
        • Toute modification de cette commande doit faire l'objet d'un avenant<br/>
        • Ce bon de commande est valable 30 jours à compter de sa date d'émission<br/>
        <br/>
        <b>Signature et cachet du client requis pour validation</b>
        </para>
        """
        elements.append(Paragraph(conditions_text, styles['Normal']))
        
        # Construire le PDF
        doc.build(elements)
        
        # Récupérer le contenu du buffer
        buffer.seek(0)
        pdf_content = buffer.getvalue()
        buffer.close()
        
        # Créer le fichier temporaire
        import tempfile
        import os
        from django.core.files.base import ContentFile
        
        # Nom du fichier
        filename = f"bon_commande_{commande.numero_commande}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        # Créer le document dans la base de données
        document = Document()
        document.commande = commande
        document.nom_document = f"Bon de commande - {commande.numero_commande}"
        document.type = 'bon_commande'
        document.numero_document = commande.numero_commande
        document.utilisateur = User.objects.get(id=request.session['user_id'])
        
        # Sauvegarder le fichier PDF
        document.fichier.save(
            filename,
            ContentFile(pdf_content),
            save=True
        )
        
        messages.success(request, f'Bon de commande généré et enregistré avec succès: {filename}')
        return redirect('detail_commande', commande_id=commande.id)
        
    except Exception as e:
        messages.error(request, f'Erreur lors de la génération du bon de commande: {str(e)}')
        return redirect('detail_commande', commande_id=commande.id)

def telecharger_bon_commande(request, commande_id):
    """Télécharger le bon de commande existant ou le générer s'il n'existe pas"""
    if not request.session.get('user_id'):
        return redirect('login')
    
    commande = get_object_or_404(Commande, id=commande_id)
    
    # Chercher le bon de commande existant
    bon_commande = Document.objects.filter(
        commande=commande,
        type='bon_commande'
    ).first()
    
    if bon_commande:
        # Télécharger le bon existant
        if default_storage.exists(bon_commande.fichier.name):
            response = HttpResponse(
                default_storage.open(bon_commande.fichier.name).read(),
                content_type='application/pdf'
            )
            response['Content-Disposition'] = f'attachment; filename="bon_commande_{commande.numero_commande}.pdf"'
            return response
        else:
            messages.error(request, 'Le fichier du bon de commande est introuvable.')
            return redirect('detail_commande', commande_id=commande.id)
    else:
        # Générer un nouveau bon de commande
        return generer_bon_commande(request, commande_id)

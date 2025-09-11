from django.urls import path
from . import views
from .Stock import (
    stock_dashboard, liste_produits, ajouter_produit, 
    mouvement_stock_form, historique_mouvements, 
    api_stock_data, detail_produit, rapport_stock, rapport_stock_pdf
)
from .Client import (
    client_dashboard, liste_clients, ajouter_client, detail_client,
    modifier_client, desactiver_client, rapport_clients_pdf, api_clients_stats
)
from .Commande import (
    commande_dashboard, liste_commandes, ajouter_commande, detail_commande,
    modifier_commande, ajouter_ligne_commande, modifier_ligne_commande,
    supprimer_ligne_commande, ajouter_document, telecharger_document,
    supprimer_document, generer_facture, detail_facture, liste_factures,
    ajouter_livraison, ajouter_etape_transport, changer_statut_commande,
    rapport_commandes, api_commandes_data, telecharger_facture_pdf,
    generer_bon_commande, telecharger_bon_commande
)

urlpatterns = [
    # Home page
    path('', views.home_view, name='home'),
    
    # Authentication URLs
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('profile/', views.profile_view, name='profile'),
    
    # Stock management URLs
    path('stock/', stock_dashboard, name='stock_dashboard'),
    path('stock/produits/', liste_produits, name='liste_produits'),
    path('stock/produits/ajouter/', ajouter_produit, name='ajouter_produit'),
    path('stock/produits/<int:produit_id>/', detail_produit, name='detail_produit'),
    path('stock/mouvements/', historique_mouvements, name='historique_mouvements'),
    path('stock/mouvements/ajouter/', mouvement_stock_form, name='mouvement_stock_form'),
    path('stock/rapport/', rapport_stock, name='rapport_stock'),
    path('stock/rapport/pdf/', rapport_stock_pdf, name='rapport_stock_pdf'),
    path('api/stock/data/', api_stock_data, name='api_stock_data'),

    # Client management URLs
    path('clients/', client_dashboard, name='client_dashboard'),
    path('clients/liste/', liste_clients, name='liste_clients'),
    path('clients/ajouter/', ajouter_client, name='ajouter_client'),
    path('clients/<int:client_id>/', detail_client, name='detail_client'),
    path('clients/<int:client_id>/modifier/', modifier_client, name='modifier_client'),
    path('clients/<int:client_id>/desactiver/', desactiver_client, name='desactiver_client'),
    path('clients/rapport/pdf/', rapport_clients_pdf, name='rapport_clients_pdf'),
    path('api/clients/stats/', api_clients_stats, name='api_clients_stats'),

    # Order management URLs
    path('commandes/', commande_dashboard, name='commande_dashboard'),
    path('commandes/liste/', liste_commandes, name='liste_commandes'),
    path('commandes/ajouter/', ajouter_commande, name='ajouter_commande'),
    path('commandes/<int:commande_id>/', detail_commande, name='detail_commande'),
    path('commandes/<int:commande_id>/modifier/', modifier_commande, name='modifier_commande'),
    path('commandes/<int:commande_id>/statut/', changer_statut_commande, name='changer_statut_commande'),
    
    # Bon de commande
    path('commandes/<int:commande_id>/bon-commande/generer/', generer_bon_commande, name='generer_bon_commande'),
    path('commandes/<int:commande_id>/bon-commande/telecharger/', telecharger_bon_commande, name='telecharger_bon_commande'),
    
    # Order lines management
    path('commandes/<int:commande_id>/lignes/ajouter/', ajouter_ligne_commande, name='ajouter_ligne_commande'),
    path('commandes/lignes/<int:ligne_id>/modifier/', modifier_ligne_commande, name='modifier_ligne_commande'),
    path('commandes/lignes/<int:ligne_id>/supprimer/', supprimer_ligne_commande, name='supprimer_ligne_commande'),
    
    # Document management
    path('commandes/<int:commande_id>/documents/ajouter/', ajouter_document, name='ajouter_document'),
    path('documents/<int:document_id>/telecharger/', telecharger_document, name='telecharger_document'),
    path('documents/<int:document_id>/supprimer/', supprimer_document, name='supprimer_document'),
    
    # Invoice management
    path('commandes/<int:commande_id>/facture/generer/', generer_facture, name='generer_facture'),
    path('factures/<int:facture_id>/', detail_facture, name='detail_facture'),
    path('factures/<int:facture_id>/pdf/', telecharger_facture_pdf, name='telecharger_facture_pdf'),
    path('factures/', liste_factures, name='liste_factures'),
    
    # Delivery and transport
    path('commandes/<int:commande_id>/livraison/ajouter/', ajouter_livraison, name='ajouter_livraison'),
    path('commandes/<int:commande_id>/transport/ajouter/', ajouter_etape_transport, name='ajouter_etape_transport'),
    
    # Reports and API
    path('commandes/rapport/', rapport_commandes, name='rapport_commandes'),
    path('api/commandes/data/', api_commandes_data, name='api_commandes_data'),
]

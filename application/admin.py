from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    User, CLIENT, POISSON, Commande, LigneCommande, 
    EtapeTransport, Document, Vehicule, Livraison, 
    Facture, Notification, Historique, Rapport, 
    Expedition, MouvementStock, Tarif, AuditLog, 
    Comptabilite
)

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'user_email', 'role', 'actif', 'date_creation')
    list_filter = ('role', 'actif', 'date_creation')
    search_fields = ('username', 'user_email')
    readonly_fields = ('date_creation', 'date_modification')
    fieldsets = (
        ('Informations de base', {
            'fields': ('username', 'user_email', 'role', 'actif')
        }),
        ('Dates', {
            'fields': ('date_creation', 'date_modification'),
            'classes': ('collapse',)
        }),
    )

@admin.register(CLIENT)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('code_client', 'nom_societe', 'email', 'pays', 'role', 'actif')
    list_filter = ('role', 'pays', 'actif', 'date_creation')
    search_fields = ('nom_societe', 'email', 'code_client')
    readonly_fields = ('code_client', 'date_creation', 'date_modification')
    fieldsets = (
        ('Informations générales', {
            'fields': ('code_client', 'nom_societe', 'email', 'role', 'actif')
        }),
        ('Coordonnées', {
            'fields': ('telephone', 'adresse', 'pays')
        }),
        ('Informations légales', {
            'fields': ('numero_registre_commerce', 'numero_ice'),
            'classes': ('collapse',)
        }),
        ('Dates', {
            'fields': ('date_creation', 'date_modification'),
            'classes': ('collapse',)
        }),
    )

@admin.register(POISSON)
class PoissonAdmin(admin.ModelAdmin):
    list_display = ('code_produit', 'type', 'prix', 'quantite_stock', 'unite_mesure', 'seuil_alerte', 'actif')
    list_filter = ('unite_mesure', 'actif', 'date_creation')
    search_fields = ('type', 'code_produit')
    readonly_fields = ('code_produit', 'date_creation', 'date_modification')
    fieldsets = (
        ('Informations produit', {
            'fields': ('code_produit', 'type', 'prix', 'unite_mesure', 'actif')
        }),
        ('Stock', {
            'fields': ('quantite_stock', 'seuil_alerte')
        }),
        ('Dates', {
            'fields': ('date_creation', 'date_modification'),
            'classes': ('collapse',)
        }),
    )

class LigneCommandeInline(admin.TabularInline):
    model = LigneCommande
    extra = 1
    readonly_fields = ('total_ligne',)

@admin.register(Commande)
class CommandeAdmin(admin.ModelAdmin):
    list_display = ('numero_commande', 'client', 'type_commande', 'statut', 'total_display', 'date_creation')
    list_filter = ('type_commande', 'statut', 'date_creation', 'incoterm')
    search_fields = ('numero_commande', 'client__nom_societe')
    readonly_fields = ('numero_commande', 'total_display', 'date_creation', 'date_modification')
    inlines = [LigneCommandeInline]
    
    def total_display(self, obj):
        return f"{obj.total} MAD"
    total_display.short_description = "Total"
    
    fieldsets = (
        ('Informations commande', {
            'fields': ('numero_commande', 'client', 'type_commande', 'statut')
        }),
        ('Détails', {
            'fields': ('incoterm', 'date_expedition', 'commentaire')
        }),
        ('Suivi', {
            'fields': ('utilisateur_creation', 'total_display'),
            'classes': ('collapse',)
        }),
        ('Dates', {
            'fields': ('date_creation', 'date_modification'),
            'classes': ('collapse',)
        }),
    )

@admin.register(LigneCommande)
class LigneCommandeAdmin(admin.ModelAdmin):
    list_display = ('commande', 'poisson', 'quantite', 'prix_unitaire', 'total_ligne')
    list_filter = ('commande__type_commande', 'poisson__type')
    search_fields = ('commande__numero_commande', 'poisson__type')
    readonly_fields = ('total_ligne',)

@admin.register(EtapeTransport)
class EtapeTransportAdmin(admin.ModelAdmin):
    list_display = ('commande', 'mode_transport', 'transporteur', 'date_depart', 'statut', 'FraisTransport')
    list_filter = ('mode_transport', 'statut', 'transporteur', 'date_depart')
    search_fields = ('commande__numero_commande', 'numero_suivi')
    readonly_fields = ('date_creation', 'date_modification')

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('nom_document', 'commande', 'type', 'numero_document', 'envoye_agence', 'date_ajout')
    list_filter = ('type', 'envoye_agence', 'date_ajout')
    search_fields = ('nom_document', 'numero_document', 'commande__numero_commande')
    readonly_fields = ('date_ajout',)

@admin.register(Vehicule)
class VehiculeAdmin(admin.ModelAdmin):
    list_display = ('nom', 'immatriculation', 'conducteur', 'capacite', 'actif')
    list_filter = ('actif', 'date_creation')
    search_fields = ('nom', 'immatriculation', 'conducteur')
    readonly_fields = ('date_creation', 'date_modification')

@admin.register(Livraison)
class LivraisonAdmin(admin.ModelAdmin):
    list_display = ('numero_livraison', 'commande', 'vehicule', 'statut', 'frais_livraison', 'date_livraison')
    list_filter = ('statut', 'date_livraison')
    search_fields = ('numero_livraison', 'commande__numero_commande', 'chauffeur')
    readonly_fields = ('numero_livraison',)

@admin.register(Facture)
class FactureAdmin(admin.ModelAdmin):
    list_display = ('numero_facture', 'client', 'commande', 'montant_ttc', 'statut', 'date_emission')
    list_filter = ('statut', 'mode_paiement', 'date_emission')
    search_fields = ('numero_facture', 'client__nom_societe', 'commande__numero_commande')
    readonly_fields = ('montant_tva', 'montant_ttc', 'date_emission')
    
    fieldsets = (
        ('Informations facture', {
            'fields': ('numero_facture', 'client', 'commande', 'statut')
        }),
        ('Montants', {
            'fields': ('montant_ht', 'taux_tva', 'montant_tva', 'montant_ttc')
        }),
        ('Paiement', {
            'fields': ('mode_paiement', 'date_echeance')
        }),
        ('Relations', {
            'fields': ('ligne_commande', 'livraison', 'utilisateur_creation'),
            'classes': ('collapse',)
        }),
        ('Dates', {
            'fields': ('date_emission',),
            'classes': ('collapse',)
        }),
    )

@admin.register(MouvementStock)
class MouvementStockAdmin(admin.ModelAdmin):
    list_display = ('poisson', 'type_mouvement', 'quantite', 'date_mouvement', 'utilisateur')
    list_filter = ('type_mouvement', 'date_mouvement', 'poisson__type')
    search_fields = ('poisson__type', 'motif', 'commande__numero_commande')
    readonly_fields = ('date_mouvement',)

@admin.register(Tarif)
class TarifAdmin(admin.ModelAdmin):
    list_display = ('poisson', 'type_tarif', 'prix', 'devise', 'date_debut', 'date_fin', 'actif')
    list_filter = ('type_tarif', 'devise', 'actif', 'date_debut')
    search_fields = ('poisson__type',)
    readonly_fields = ('date_creation',)

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('utilisateur', 'message_preview', 'lu', 'date_notification')
    list_filter = ('lu', 'date_notification')
    search_fields = ('utilisateur__username', 'message')
    readonly_fields = ('date_notification',)
    
    def message_preview(self, obj):
        return obj.message[:50] + "..." if len(obj.message) > 50 else obj.message
    message_preview.short_description = "Message"

@admin.register(Historique)
class HistoriqueAdmin(admin.ModelAdmin):
    list_display = ('utilisateur', 'action', 'date_action')
    list_filter = ('date_action',)
    search_fields = ('utilisateur__username', 'action')
    readonly_fields = ('date_action',)

@admin.register(Rapport)
class RapportAdmin(admin.ModelAdmin):
    list_display = ('titre', 'auteur', 'date_creation')
    list_filter = ('date_creation', 'auteur')
    search_fields = ('titre', 'contenu')
    readonly_fields = ('date_creation',)

@admin.register(Expedition)
class ExpeditionAdmin(admin.ModelAdmin):
    list_display = ('numero_expedition', 'destinataire', 'transporteur', 'statut', 'date_expedition')
    list_filter = ('statut', 'transporteur', 'date_expedition')
    search_fields = ('numero_expedition', 'destinataire')
    readonly_fields = ('date_creation', 'date_modification')

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('utilisateur', 'action', 'model_name', 'object_repr', 'date_action')
    list_filter = ('action', 'model_name', 'date_action')
    search_fields = ('utilisateur__username', 'object_repr')
    readonly_fields = ('date_action',)

@admin.register(Comptabilite)
class ComptabiliteAdmin(admin.ModelAdmin):
    list_display = ('commande', 'facture', 'montant_total', 'export_comptable', 'date_enregistrement')
    list_filter = ('export_comptable', 'date_enregistrement')
    search_fields = ('commande__numero_commande', 'facture__numero_facture')
    readonly_fields = ('date_enregistrement',)

# Customize admin site
admin.site.site_header = "Administration FishFlow Manager"
admin.site.site_title = "FishFlow Admin"
admin.site.index_title = "Gestion Export/Import Poisson"

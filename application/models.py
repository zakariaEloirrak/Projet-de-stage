from datetime import date
from django.db import models
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.functional import cached_property
from decimal import Decimal
import uuid

class User(models.Model):
    ROLE_CHOICES = [
        ('ADMIN', 'Administrator'),
        ('COMPTABLE', 'Comptable'),
        ('GESTIONNAIRE', 'Gestionnaire'),
    ]
        
    username = models.CharField(max_length=100, unique=True)
    user_email = models.EmailField(max_length=254, unique=True)
    password = models.CharField(max_length=128)
    role = models.CharField(max_length=15, choices=ROLE_CHOICES, default='GESTIONNAIRE')
    date_creation = models.DateTimeField(default=timezone.now)
    date_modification = models.DateTimeField(auto_now=True)
    actif = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if not self.password.startswith('pbkdf2_'):
            self.password = make_password(self.password)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.username} ({self.role})"

class CLIENT(models.Model):
    ROLE_CHOICES = [
        ('CLIENT', 'ACHETEUR'),
        ('FOURNISSEUR', 'FOURNISSEUR'),
    ]

    # Add unique identifier for data circulation
    code_client = models.CharField(max_length=20, unique=True, null=True, blank=True)
    nom_societe = models.CharField(max_length=100,)
    pays = models.CharField(max_length=100, blank=True, null=True, default="Morocco")
    email = models.EmailField(null=False, blank=False)
    telephone = models.CharField(max_length=15, blank=True, null=True)
    adresse = models.CharField(max_length=255, blank=True, null=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='CLIENT')
    # Add fields for data circulation
    numero_registre_commerce = models.CharField(max_length=50, blank=True, null=True)
    numero_ice = models.CharField(max_length=20, blank=True, null=True)
    date_creation = models.DateTimeField(default=timezone.now)
    date_modification = models.DateTimeField(auto_now=True)
    actif = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if not self.code_client:
            # Generate a unique code using current timestamp
            timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
            self.code_client = f"CLI{timestamp}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code_client} - {self.nom_societe}"

class POISSON(models.Model):
    # Add unique identifier
    code_produit = models.CharField(max_length=20, unique=True, null=True, blank=True)
    type = models.CharField(max_length=100)
    prix = models.DecimalField(max_digits=10, decimal_places=2)
    quantite_stock = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    # Add fields for better stock management
    unite_mesure = models.CharField(max_length=10, default='KG')
    seuil_alerte = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    date_creation = models.DateTimeField(default=timezone.now)
    date_modification = models.DateTimeField(auto_now=True)
    actif = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if not self.code_produit:
            # Generate a unique code using current timestamp
            timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
            self.code_produit = f"PROD{timestamp}"
        super().save(*args, **kwargs)
        
    def __str__(self):
        return f"{self.code_produit} - {self.type} - {self.quantite_stock} {self.unite_mesure} - {self.prix} MAD"

class Commande(models.Model):
    TYPE_CHOICES = [
        ('EXPORT', 'Export'),
        ('IMPORT', 'Import'),
        ('LOCAL', 'Local'),
    ]
    STATUT_CHOICES = [
        ('BROUILLON', 'Brouillon'),
        ('CONFIRMEE', 'Confirmée'),
        ('PREPARATION', 'En préparation'),
        ('EXPEDIEE', 'Expédiée'),
        ('LIVREE', 'Livrée'),
        ('ANNULEE', 'Annulée'),
    ]
    INCOTERM_CHOICES = [
        ('EXW', 'Ex Works'),
        ('FOB', 'Free On Board'),
        ('CIF', 'Cost Insurance Freight'),
        ('DDP', 'Delivered Duty Paid'),
    ]

    # Add unique identifier for data circulation
    numero_commande = models.CharField(max_length=30, unique=True, null=True, blank=True)
    type_commande = models.CharField(max_length=10, choices=TYPE_CHOICES, default='EXPORT')
    client = models.ForeignKey(CLIENT, on_delete=models.CASCADE)
    date_creation = models.DateTimeField(default=timezone.now)
    date_expedition = models.DateField(null=True, blank=True)
    statut = models.CharField(max_length=15, choices=STATUT_CHOICES, default='BROUILLON')
    incoterm = models.CharField(max_length=5, choices=INCOTERM_CHOICES, blank=True, null=True)
    commentaire = models.TextField(blank=True, null=True)
    # Add user tracking
    utilisateur_creation = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='commandes_creees')
    date_modification = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.numero_commande:
            # Generate a unique command number
            timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
            self.numero_commande = f"CMD{timestamp}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.numero_commande} - {self.client.nom_societe}"

    @property
    def total(self):
        lignes = self.lignecommande_set.all()
        return sum(ligne.total_ligne or 0 for ligne in lignes)

class LigneCommande(models.Model):
    commande = models.ForeignKey(Commande, on_delete=models.CASCADE)
    poisson = models.ForeignKey(POISSON, on_delete=models.CASCADE)  # Fixed naming
    quantite = models.DecimalField(max_digits=10, decimal_places=2)
    prix_unitaire = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    total_ligne = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.prix_unitaire:
            self.prix_unitaire = self.poisson.prix
        self.total_ligne = self.quantite * self.prix_unitaire
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.commande.numero_commande} - {self.poisson.type} - {self.quantite}"

class EtapeTransport(models.Model):
    TRANSPORT_CHOICES = [
        ('BATEAU', 'Bateau'),
        ('CAMION', 'Camion'),
        ('AVION', 'Avion'),
    ]
    STATUT_CHOICES = [
        ('EN_ATTENTE', 'En attente'),
        ('EN_TRANSIT', 'En transit'),
        ('LIVREE', 'Livrée'),
    ]
    transporteur_choices = [
        ('Transporteur A', 'Transporteur A'),
        ('Transporteur B', 'Transporteur B'),
        ('Transporteur C', 'Transporteur C'),
    ]

    commande = models.ForeignKey(Commande, on_delete=models.CASCADE, related_name='etapes_transport')
    mode_transport = models.CharField(max_length=10, choices=TRANSPORT_CHOICES)
    transporteur = models.CharField(max_length=100, choices=transporteur_choices, default='Transporteur A')
    date_depart = models.DateField()
    num_conteneur = models.CharField(max_length=50, blank=True, null=True)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='EN_ATTENTE')
    FraisTransport = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    # Add tracking fields
    numero_suivi = models.CharField(max_length=50, blank=True, null=True)
    date_creation = models.DateTimeField(default=timezone.now)
    date_modification = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.mode_transport} - {self.transporteur} ({self.date_depart})"

class Document(models.Model):
    TYPE_CHOICES = [
        ('facture', 'Facture'),
        ('bon_livraison', 'Bon de Livraison'),
        ('bon_commande', 'Bon de Commande'),
        ('certificat_origine', 'Certificat d\'Origine'),
        ('licence_export', 'Licence d\'Export'),
        ('connaissement', 'Connaissement'),
        ('autre', 'Autre')
    ]
    
    commande = models.ForeignKey(Commande, on_delete=models.CASCADE)
    fichier = models.FileField(upload_to='documents/')
    nom_document = models.CharField(max_length=100)
    type = models.CharField(max_length=50, choices=TYPE_CHOICES)
    numero_document = models.CharField(max_length=50, blank=True, null=True)
    date_ajout = models.DateTimeField(default=timezone.now)
    utilisateur = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    # For data circulation tracking
    envoye_agence = models.BooleanField(default=False)
    date_envoi_agence = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.nom_document} - Commande {self.commande.numero_commande}"

class Vehicule(models.Model):
    TYPE_CHOICES = [
        ('CAMION', 'Camion'),   
        ('VOITURE', 'Voiture'),
        ('MOTO', 'Moto'),
    ]
    nom = models.CharField(max_length=100)
    conducteur = models.CharField(max_length=100, blank=True, null=True)
    capacite = models.PositiveIntegerField(help_text="Capacité en KG")
    immatriculation = models.CharField(max_length=15, unique=True)

    # Add tracking fields
    date_creation = models.DateTimeField(default=timezone.now)
    date_modification = models.DateTimeField(auto_now=True)
    actif = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.nom} - {self.immatriculation} ({self.capacite} KG)"

class Livraison(models.Model):
    commande = models.ForeignKey(Commande, on_delete=models.CASCADE)
    vehicule = models.ForeignKey(Vehicule, on_delete=models.CASCADE)
    numero_livraison = models.CharField(max_length=30, unique=True, null=True, blank=True)
    date_livraison = models.DateTimeField(default=timezone.now)
    adresse_livraison = models.CharField(max_length=255)
    frais_livraison = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    statut = models.CharField(max_length=20, choices=[
        ('en_attente', 'En attente'),
        ('en_cours', 'En cours'),
        ('terminee', 'Terminée'),
        ('annulee', 'Annulée')
    ], default='en_attente')
    
    # Add user tracking
    chauffeur = models.CharField(max_length=100, blank=True, null=True)
    signature_client = models.TextField(blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.numero_livraison:
            timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
            self.numero_livraison = f"LIV{timestamp}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.numero_livraison} - Commande {self.commande.numero_commande} - {self.vehicule.nom}"

class Facture(models.Model):
    commande = models.ForeignKey(Commande, on_delete=models.CASCADE)
    client = models.ForeignKey(CLIENT, on_delete=models.CASCADE)
    ligne_commande = models.ManyToManyField(LigneCommande, blank=True)
    livraison = models.ForeignKey(Livraison, on_delete=models.CASCADE, blank=True, null=True)
    numero_facture = models.CharField(max_length=50, unique=True)    
    montant_ht = models.DecimalField(max_digits=10, decimal_places=2)
    taux_tva = models.DecimalField(max_digits=5, decimal_places=2, default=20)
    montant_tva = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    montant_ttc = models.DecimalField(max_digits=10, decimal_places=2)
    date_emission = models.DateTimeField(default=timezone.now)
    date_echeance = models.DateTimeField()
    mode_paiement = models.CharField(max_length=50, choices=[
        ('carte_bancaire', 'Carte Bancaire'),
        ('virement', 'Virement'),
        ('cheque', 'Chèque'),
        ('especes', 'Espèces')
    ])
    statut = models.CharField(max_length=20, choices=[
        ('brouillon', 'Brouillon'),
        ('emise', 'Émise'),
        ('envoyee', 'Envoyée'),
        ('payee', 'Payée'),
        ('annulee', 'Annulée')
    ], default='brouillon')
    
    # Add user tracking
    utilisateur_creation = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    def save(self, *args, **kwargs):
        self.montant_tva = self.montant_ht * (self.taux_tva / 100)
        self.montant_ttc = self.montant_ht + self.montant_tva
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Facture {self.numero_facture} - {self.client.nom_societe}"

class Notification(models.Model):
    utilisateur = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    date_notification = models.DateTimeField(default=timezone.now)
    lu = models.BooleanField(default=False)

    def __str__(self):
        return f"Notification {self.id} - Utilisateur {self.utilisateur.username} - {self.date_notification.strftime('%Y-%m-%d %H:%M:%S')}"

class Historique(models.Model):
    utilisateur = models.ForeignKey(User, on_delete=models.CASCADE)
    action = models.CharField(max_length=255)
    date_action = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Historique {self.id} - Utilisateur {self.utilisateur.username} - {self.date_action.strftime('%Y-%m-%d %H:%M:%S')}"

class Rapport(models.Model):
    titre = models.CharField(max_length=255)
    contenu = models.TextField()
    date_creation = models.DateTimeField(default=timezone.now)
    auteur = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return f"Rapport {self.titre} - {self.date_creation.strftime('%Y-%m-%d %H:%M:%S')} - Auteur: {self.auteur.username}"

class Expedition(models.Model):
    STATUTS_CHOICES = [
        ('En préparation', 'En préparation'),
        ('Expédié', 'Expédié'),
        ('En transit', 'En transit'),
        ('En cours de livraison', 'En cours de livraison'),
        ('Livré', 'Livré'),
        ('Retardé', 'Retardé'),
        ('Problème', 'Problème'),
    ]
    
    numero_expedition = models.CharField(max_length=50, unique=True, verbose_name="Numéro d'expédition")
    destinataire = models.CharField(max_length=200, verbose_name="Destinataire")
    adresse = models.TextField(verbose_name="Adresse de livraison")
    transporteur = models.CharField(max_length=100, verbose_name="Transporteur")
    date_expedition = models.DateField(default=date.today, verbose_name="Date d'expédition")
    statut = models.CharField(max_length=50, choices=STATUTS_CHOICES, default='En préparation', verbose_name="Statut")
    date_livraison_prevue = models.DateTimeField(null=True, blank=True, verbose_name="Date de livraison prévue")
    date_livraison_reelle = models.DateTimeField(null=True, blank=True, verbose_name="Date de livraison réelle")
    notes = models.TextField(blank=True, verbose_name="Notes")
    date_creation = models.DateTimeField(default=timezone.now)
    date_modification = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date_creation']
        verbose_name = "Expédition"
        verbose_name_plural = "Expéditions"
    
    def __str__(self):
        return f"{self.numero_expedition} - {self.destinataire}"
    
class MouvementStock(models.Model):
    TYPE_MOUVEMENT_CHOICES = [
        ('ENTREE', 'Entrée'),
        ('SORTIE', 'Sortie'),
        ('AJUSTEMENT', 'Ajustement'),
        ('RETOUR', 'Retour'),
    ]
    
    poisson = models.ForeignKey(POISSON, on_delete=models.CASCADE)
    type_mouvement = models.CharField(max_length=15, choices=TYPE_MOUVEMENT_CHOICES)
    quantite = models.DecimalField(max_digits=10, decimal_places=2)
    date_mouvement = models.DateTimeField(default=timezone.now)
    commande = models.ForeignKey(Commande, on_delete=models.SET_NULL, null=True, blank=True)
    utilisateur = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    motif = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.type_mouvement} - {self.poisson.type} - {self.quantite}"

class Tarif(models.Model):
    TYPE_TARIF_CHOICES = [
        ('ACHAT', 'Prix d\'achat'),
        ('VENTE', 'Prix de vente'),
        ('TRANSPORT', 'Frais de transport'),
    ]
    
    poisson = models.ForeignKey(POISSON, on_delete=models.CASCADE, null=True, blank=True)
    type_tarif = models.CharField(max_length=15, choices=TYPE_TARIF_CHOICES)
    prix = models.DecimalField(max_digits=10, decimal_places=2)
    devise = models.CharField(max_length=5, default='MAD')
    date_debut = models.DateField()
    date_fin = models.DateField(null=True, blank=True)
    actif = models.BooleanField(default=True)
    date_creation = models.DateTimeField(default=timezone.now)
    utilisateur_creation = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    def __str__(self):
        return f"{self.type_tarif} - {self.prix} {self.devise}"

class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('CREATE', 'Création'),
        ('UPDATE', 'Modification'),
        ('DELETE', 'Suppression'),
        ('VIEW', 'Consultation'),
        ('EXPORT', 'Export'),
        ('IMPORT', 'Import'),
    ]
    
    utilisateur = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    model_name = models.CharField(max_length=50)
    object_id = models.PositiveIntegerField()
    object_repr = models.CharField(max_length=200)
    date_action = models.DateTimeField(default=timezone.now)
    adresse_ip = models.GenericIPAddressField(null=True, blank=True)
    details = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['-date_action']
    
    def __str__(self):
        return f"{self.action} - {self.model_name} - {self.utilisateur}"

# Fix comptabilite class name
class Comptabilite(models.Model):
    commande = models.ForeignKey(Commande, on_delete=models.CASCADE)
    facture = models.ForeignKey(Facture, on_delete=models.CASCADE, blank=True, null=True)
    montant_total = models.DecimalField(max_digits=10, decimal_places=2)
    date_enregistrement = models.DateTimeField(default=timezone.now)
    utilisateur = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    # Add fields for accounting circulation
    export_comptable = models.BooleanField(default=False)
    date_export_comptable = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Comptabilité"
        verbose_name_plural = "Comptabilités"

    def __str__(self):
        return f"Comptabilité {self.id} - Commande {self.commande.numero_commande}"
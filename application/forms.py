from django import forms
from django.core.exceptions import ValidationError
from .models import (
    User, CLIENT, POISSON, Commande, LigneCommande, Document, 
    Facture, Livraison, EtapeTransport, Vehicule, MouvementStock
)

class LoginForm(forms.Form):
    username = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nom d\'utilisateur',
            'required': True
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Mot de passe',
            'required': True
        })
    )

class RegisterForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Mot de passe'
        })
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirmer le mot de passe'
        })
    )

    class Meta:
        model = User
        fields = ['username', 'user_email', 'role']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nom d\'utilisateur'
            }),
            'user_email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Email'
            }),
            'role': forms.Select(attrs={
                'class': 'form-control'
            })
        }

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exists():
            raise ValidationError('Ce nom d\'utilisateur existe déjà.')
        return username

    def clean_user_email(self):
        email = self.cleaned_data['user_email']
        if User.objects.filter(user_email=email).exists():
            raise ValidationError('Cet email est déjà utilisé.')
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and confirm_password:
            if password != confirm_password:
                raise ValidationError('Les mots de passe ne correspondent pas.')
        
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.password = self.cleaned_data['password']
        if commit:
            user.save()
        return user

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'user_email']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'readonly': True
            }),
            'user_email': forms.EmailInput(attrs={
                'class': 'form-control'
            })
        }

class ChangePasswordForm(forms.Form):
    current_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Mot de passe actuel'
        })
    )
    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nouveau mot de passe'
        })
    )
    confirm_new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirmer le nouveau mot de passe'
        })
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_current_password(self):
        current_password = self.cleaned_data['current_password']
        from django.contrib.auth.hashers import check_password
        if not check_password(current_password, self.user.password):
            raise ValidationError('Mot de passe actuel incorrect.')
        return current_password

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        confirm_new_password = cleaned_data.get('confirm_new_password')

        if new_password and confirm_new_password:
            if new_password != confirm_new_password:
                raise ValidationError('Les nouveaux mots de passe ne correspondent pas.')
        
        return cleaned_data

class UserForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput())
    
    class Meta:
        model = User
        fields = ['username', 'user_email', 'password', 'role']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'user_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-control'}),
        }

class ClientForm(forms.ModelForm):
    class Meta:
        model = CLIENT
        fields = [
            'nom_societe', 'email', 'telephone', 'pays', 'adresse', 
            'role', 'numero_registre_commerce', 'numero_ice'
        ]
        widgets = {
            'nom_societe': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'telephone': forms.TextInput(attrs={'class': 'form-control'}),
            'pays': forms.TextInput(attrs={'class': 'form-control'}),
            'adresse': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'role': forms.Select(attrs={'class': 'form-control'}),
            'numero_registre_commerce': forms.TextInput(attrs={'class': 'form-control'}),
            'numero_ice': forms.TextInput(attrs={'class': 'form-control'}),
        }

class PoissonForm(forms.ModelForm):
    class Meta:
        model = POISSON
        fields = ['type', 'prix', 'quantite_stock', 'unite_mesure', 'seuil_alerte']
        widgets = {
            'type': forms.TextInput(attrs={'class': 'form-control'}),
            'prix': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'quantite_stock': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'unite_mesure': forms.Select(choices=[
                ('KG', 'Kilogrammes'),
                ('T', 'Tonnes'),
                ('PIECES', 'Pièces'),
            ], attrs={'class': 'form-control'}),
            'seuil_alerte': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }

class MouvementStockForm(forms.ModelForm):
    class Meta:
        model = MouvementStock
        fields = ['poisson', 'type_mouvement', 'quantite', 'commande', 'motif']
        widgets = {
            'poisson': forms.Select(attrs={'class': 'form-control'}),
            'type_mouvement': forms.Select(attrs={'class': 'form-control'}),
            'quantite': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'commande': forms.Select(attrs={'class': 'form-control'}),
            'motif': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

# === COMMANDES FORMS ===

class CommandeForm(forms.ModelForm):
    class Meta:
        model = Commande
        fields = [
            'type_commande', 'client', 'date_expedition', 
            'incoterm', 'commentaire'
        ]
        widgets = {
            'type_commande': forms.Select(attrs={'class': 'form-control'}),
            'client': forms.Select(attrs={'class': 'form-control'}),
            'date_expedition': forms.DateInput(attrs={
                'class': 'form-control', 
                'type': 'date'
            }),
            'incoterm': forms.Select(attrs={'class': 'form-control'}),
            'commentaire': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3, 
                'placeholder': 'Commentaires sur la commande...'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['client'].queryset = CLIENT.objects.filter(actif=True)

class LigneCommandeForm(forms.ModelForm):
    class Meta:
        model = LigneCommande
        fields = ['poisson', 'quantite', 'prix_unitaire']
        widgets = {
            'poisson': forms.Select(attrs={'class': 'form-control'}),
            'quantite': forms.NumberInput(attrs={
                'class': 'form-control', 
                'step': '0.01',
                'min': '0'
            }),
            'prix_unitaire': forms.NumberInput(attrs={
                'class': 'form-control', 
                'step': '0.01',
                'min': '0'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['poisson'].queryset = POISSON.objects.filter(actif=True)
        self.fields['prix_unitaire'].required = False

class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ['fichier', 'nom_document', 'type', 'numero_document']
        widgets = {
            'fichier': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.doc,.docx,.jpg,.jpeg,.png,.xls,.xlsx'
            }),
            'nom_document': forms.TextInput(attrs={'class': 'form-control'}),
            'type': forms.Select(attrs={'class': 'form-control'}),
            'numero_document': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Numéro du document (optionnel)'
            }),
        }

class FactureForm(forms.ModelForm):
    class Meta:
        model = Facture
        fields = [
            'montant_ht', 'taux_tva', 'date_echeance', 
            'mode_paiement', 'statut'
        ]
        widgets = {
            'montant_ht': forms.NumberInput(attrs={
                'class': 'form-control', 
                'step': '0.01',
                'readonly': True
            }),
            'taux_tva': forms.NumberInput(attrs={
                'class': 'form-control', 
                'step': '0.01',
                'value': '20'
            }),
            'date_echeance': forms.DateTimeInput(attrs={
                'class': 'form-control', 
                'type': 'datetime-local'
            }),
            'mode_paiement': forms.Select(attrs={'class': 'form-control'}),
            'statut': forms.Select(attrs={'class': 'form-control'}),
        }

class LivraisonForm(forms.ModelForm):
    class Meta:
        model = Livraison
        fields = [
            'vehicule', 'date_livraison', 'adresse_livraison', 
            'frais_livraison', 'chauffeur'
        ]
        widgets = {
            'vehicule': forms.Select(attrs={'class': 'form-control'}),
            'date_livraison': forms.DateTimeInput(attrs={
                'class': 'form-control', 
                'type': 'datetime-local'
            }),
            'adresse_livraison': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3
            }),
            'frais_livraison': forms.NumberInput(attrs={
                'class': 'form-control', 
                'step': '0.01'
            }),
            'chauffeur': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['vehicule'].queryset = Vehicule.objects.filter(actif=True)

class EtapeTransportForm(forms.ModelForm):
    class Meta:
        model = EtapeTransport
        fields = [
            'mode_transport', 'transporteur', 'date_depart', 
            'num_conteneur', 'FraisTransport', 'numero_suivi'
        ]
        widgets = {
            'mode_transport': forms.Select(attrs={'class': 'form-control'}),
            'transporteur': forms.Select(attrs={'class': 'form-control'}),
            'date_depart': forms.DateInput(attrs={
                'class': 'form-control', 
                'type': 'date'
            }),
            'num_conteneur': forms.TextInput(attrs={'class': 'form-control'}),
            'FraisTransport': forms.NumberInput(attrs={
                'class': 'form-control', 
                'step': '0.01'
            }),
            'numero_suivi': forms.TextInput(attrs={'class': 'form-control'}),
        }

class VehiculeForm(forms.ModelForm):
    class Meta:
        model = Vehicule
        fields = ['nom', 'conducteur', 'capacite', 'immatriculation']
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-control'}),
            'conducteur': forms.TextInput(attrs={'class': 'form-control'}),
            'capacite': forms.NumberInput(attrs={'class': 'form-control'}),
            'immatriculation': forms.TextInput(attrs={'class': 'form-control'}),
        }

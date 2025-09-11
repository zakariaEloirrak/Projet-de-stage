# CSS pour les Commandes

Ce dossier contient les fichiers CSS spécifiques pour le module des commandes.

## Structure des fichiers

### `commandes.css`
Fichier CSS principal contenant tous les styles de base pour les commandes :
- Variables CSS personnalisées
- Styles pour les formulaires
- Styles pour les tableaux
- Badges et statuts
- Boutons d'action
- Layout et grilles
- Design responsive

### `dashboard.css`
Fichier CSS spécifique pour le dashboard des commandes :
- Statistiques avancées avec animations
- Actions rapides améliorées
- Graphiques et charts
- États de chargement
- Tooltips
- Animations d'entrée

### `factures.css`
Fichier CSS spécifique pour les factures :
- Styles pour les tableaux de factures
- Statuts de facture spécifiques
- Montants et éléments financiers
- Génération et prévisualisation de factures
- Rapports de factures
- Styles d'impression

## Variables CSS

Le système utilise des variables CSS personnalisées pour maintenir la cohérence :

```css
:root {
    --commande-primary: #2563eb;
    --commande-primary-dark: #1d4ed8;
    --commande-success: #059669;
    --commande-warning: #d97706;
    --commande-danger: #dc2626;
    --commande-info: #0ea5e9;
    --commande-text-primary: #1e293b;
    --commande-text-secondary: #64748b;
    --commande-border: #e2e8f0;
    --commande-bg: #f8fafc;
    --commande-surface: #ffffff;
    --commande-radius-sm: 0.375rem;
    --commande-radius-md: 0.5rem;
    --commande-radius-lg: 0.75rem;
    --commande-shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
    --commande-shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
    --commande-shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1);
}
```

## Utilisation dans les templates

### Template de base
```html
{% block extra_css %}
<link rel="stylesheet" href="{% static 'css/commandes/commandes.css' %}">
{% endblock %}
```

### Dashboard des commandes
```html
{% block extra_css %}
<link rel="stylesheet" href="{% static 'css/commandes/dashboard.css' %}">
{% endblock %}
```

### Factures
```html
{% block extra_css %}
<link rel="stylesheet" href="{% static 'css/commandes/factures.css' %}">
{% endblock %}
```

## Classes CSS principales

### Layout
- `.page-header` - En-tête de page avec breadcrumb
- `.form-container` - Conteneur de formulaire
- `.detail-grid` - Grille pour les détails
- `.content-grid` - Grille de contenu principal

### Formulaires
- `.form-grid` - Grille de formulaire responsive
- `.form-group` - Groupe de champ de formulaire
- `.form-actions` - Actions du formulaire

### Tableaux
- `.orders-table` - Tableau des commandes
- `.factures-table` - Tableau des factures
- `.lignes-table` - Tableau des lignes de commande

### Badges et statuts
- `.status-badge` - Badge de statut
- `.type-badge` - Badge de type
- `.status-badge.brouillon` - Statut brouillon
- `.status-badge.confirmee` - Statut confirmée
- `.status-badge.preparation` - Statut en préparation
- `.status-badge.expediee` - Statut expédiée
- `.status-badge.livree` - Statut livrée
- `.status-badge.annulee` - Statut annulée

### Actions
- `.action-buttons` - Conteneur de boutons d'action
- `.action-btn` - Bouton d'action
- `.action-card` - Carte d'action

### États
- `.empty-state` - État vide
- `.loading-skeleton` - État de chargement

## Responsive Design

Le CSS est entièrement responsive avec des breakpoints :
- Mobile : < 480px
- Tablette : < 768px
- Desktop : > 768px

## Animations

Le dashboard inclut des animations CSS :
- `fadeInUp` - Animation d'entrée
- `loading` - Animation de chargement
- Transitions sur les hover

## Maintenance

Pour maintenir la cohérence :
1. Utiliser les variables CSS définies
2. Suivre la structure des classes existantes
3. Tester sur différentes tailles d'écran
4. Vérifier l'accessibilité
5. Maintenir la compatibilité avec les navigateurs modernes

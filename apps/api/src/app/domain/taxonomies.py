"""Taxonomies métier (constantes) portées du POC `config.py` / `data_cleaner.py`.

Ces référentiels sont injectés dans les prompts LLM (secteur imposé) et servent
à la normalisation (compétences, villes) et au calcul de séniorité.
"""

# Seuils de séniorité : (min inclus, max exclus, label). Ordre croissant.
# ⚠️ Le POC avait 3 barèmes divergents (fiche / recherche / dashboard) : on
# unifie ici sur CE barème comme source de vérité unique.
SENIORITE_THRESHOLDS: list[tuple[float, float, str]] = [
    (0.0, 0.5, "Stage / Junior"),  # < 6 mois
    (0.5, 3.0, "Junior"),  # 6 mois à 3 ans
    (3.0, 6.0, "Intermédiaire"),  # 3 à 6 ans
    (6.0, 10.0, "Senior"),  # 6 à 10 ans
    (10.0, 100.0, "Lead / Expert"),  # > 10 ans
]

# Secteurs valides (imposés au LLM). 16 entrées.
SECTEURS_VALIDES: list[str] = [
    "Informatique / Tech",
    "Finance / Banque / Assurance",
    "Marketing / Communication",
    "Commerce / Vente",
    "Ressources Humaines",
    "Industrie / Production",
    "Santé / Médical",
    "Éducation / Formation",
    "Juridique / Legal",
    "Logistique / Supply Chain",
    "BTP / Immobilier",
    "Hôtellerie / Restauration",
    "Art / Design / Création",
    "Agriculture / Environnement",
    "Conseil / Audit",
    "Autre",
]

# Normalisation des compétences : alias en minuscules -> forme canonique.
SKILL_MAPPINGS: dict[str, str] = {
    # Langages
    "js": "JavaScript",
    "ts": "TypeScript",
    "py": "Python",
    "cpp": "C++",
    "c#": "C#",
    "golang": "Go",
    # Frameworks / libs
    "reactjs": "React",
    "react.js": "React",
    "vuejs": "Vue.js",
    "vue.js": "Vue.js",
    "node": "Node.js",
    "nodejs": "Node.js",
    "django framework": "Django",
    # Outils / cloud
    "aws": "Amazon Web Services",
    "gcp": "Google Cloud Platform",
    "azure": "Microsoft Azure",
    "docker container": "Docker",
    "k8s": "Kubernetes",
    # Soft skills
    "travail d'équipe": "Travail en équipe",
    "esprit d'équipe": "Travail en équipe",
    "team player": "Travail en équipe",
    "autonome": "Autonomie",
}

# Villes du Maroc : ville principale -> quartiers connus (pour ramener un
# quartier à sa ville). Comparaison en minuscules.
CITY_MAPPINGS: dict[str, list[str]] = {
    "casablanca": [
        "ain sebaa",
        "sidi moumen",
        "sidi bernoussi",
        "maarif",
        "racine",
        "gauthier",
        "californie",
        "bouskoura",
        "dar bouazza",
        "tit mellil",
        "mohammedia",
        "nouaceur",
        "hay mohammadi",
        "bernoussi",
        "roches noires",
        "belvedere",
        "ourgounda",
    ],
    "rabat": ["agdal", "hay riad", "souissi", "temara", "skhirat", "hassan", "ocean"],
    "tanger": ["malabata", "boukhalef"],
    "marrakech": ["gueliz", "hivernage"],
}

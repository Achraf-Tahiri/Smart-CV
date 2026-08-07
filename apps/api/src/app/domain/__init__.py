"""Logique métier PURE (aucune I/O, ni DB, ni FastAPI).

Portée fidèlement du POC « Smart CV » (voir `docs/portage-poc.md`) :
normalisation des dates, calcul d'expérience/séniorité, taxonomies, nettoyage.
Ces fonctions sont déterministes et testées unitairement sans base de données.
"""

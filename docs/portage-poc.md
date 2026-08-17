# Spécification de portage — logique métier du POC « Smart CV »

> Ce document décrit **fidèlement** la logique métier du POC Streamlit
> (`Smart_CV/`, à la racine du dépôt d'origine) à porter dans la nouvelle app
> FastAPI (Phase 2). Les numéros de ligne renvoient au code du POC. Il sert de
> référence pour porter le métier **sans relire le POC**, et signale les **bugs à
> ne PAS reproduire**.

## 1. `date_normalizer.py` — Normalisation des dates (LOGIQUE PURE)

Classe `DateNormalizer` (93 lignes), dépendances `re` + `datetime` uniquement.
→ destination : `domain/date_normalizer.py` (fonction pure + tests repris).

### `MONTHS_MAP` (l.13-24) — mois FR/EN, complets + abrégés, en minuscules
FR complets : janvier, fevrier/**février**, mars, avril, mai, juin, juillet, aout/**août**,
septembre, octobre, novembre, decembre/**décembre**. FR abrégés : janv, fevr/févr, avr,
juil, sept, oct, nov, dec/déc. EN complets : january…december. EN abrégés : jan…dec.
Lookup via `.lower()`. Accents gérés.

### `normalize_date(date_str) -> "YYYY-MM" | None` (l.26-81)
`date_str.lower().strip()`, puis regex dans l'ordre (1er match gagne) :
1. `YYYY[-/. ]MM` (l.45) — valide `1950<=year<=2100`, `1<=month<=12` → `f"{year}-{month:02d}"`.
2. `MM[-/. ]YYYY` (inversion, l.52) — mêmes validations.
3. `mois_texte + année` (l.60) via `MONTHS_MAP` (ex. « Août 2012 »).
4. Année seule stricte `^\s*(\d{4})\s*$` (l.68) → **défaut janvier** `f"{year}-01"`.
5. Année « loose » n'importe où (l.75) → `f"{year}-01"` (ex. « depuis 2012 »).
Sinon `None`.

**Pièges** : `None`/vide → `None`. « PRESENT »/« Aujourd'hui » **non gérés ici** (l'appelant les
traite). Range « 2020-2021 » : patterns 1-2 échouent (mois invalides), le fallback renvoie
**`2020-01`** (perte de l'année de fin) → d'où le pré-découpage regex dans le calcul d'expérience.
Année hors [1950, 2100] rejetée.

### `parse_to_datetime(date_str) -> datetime | None` (l.84-93)
`normalize_date` puis `datetime.strptime(x, "%Y-%m")`. Porte d'entrée utilisée dans `analyzer.py`.

## 2. Calcul d'expérience & séniorité (`analyzer.py`)

### Seuils `SENIORITE_THRESHOLDS` (`config.py` l.8-14) — tuples (min_inclus, max_exclus, label)
```
(0.0, 0.5, "Stage / Junior")   # < 6 mois
(0.5, 3.0, "Junior")           # 6 mois à 3 ans
(3.0, 6.0, "Intermédiaire")    # 3 à 6 ans
(6.0, 10.0, "Senior")          # 6 à 10 ans
(10.0, 100.0, "Lead / Expert") # > 10 ans
```
`_calculate_seniorite(x)` (l.698-703) : 1er intervalle `min<=x<max`, fallback `"Expert"`.

⚠️ **3 barèmes de séniorité INCOHÉRENTS** dans le POC — **à unifier** au portage :
1. `SENIORITE_THRESHOLDS` (affichage fiche, ci-dessus).
2. Prompt de recherche IA (l.849-852) : Débutant/Junior→max_exp=2 ; Confirmé→min_exp=2 ; Expert/Senior→min_exp=5.
3. Bins dashboard (`app.py` l.783-786) : [0,2,5,10,100] → « 0-2 Junior / 2-5 Confirmé / 5-10 Senior / 10+ Expert ».

### `_calculate_experience_v2(experiences) -> (float, str)` (l.483-601)
Pour chaque expérience :
1. **Début** (l.494-517) : `raw_debut`. **Pré-découpage range** (l.500) regex `(\d{4})\s*[^a-zA-Z0-9]\s*(\d{4})` →
   si match : `raw_debut=group(1)` ET **on écrase `date_fin=group(2)`** (le range explicite prime). Puis
   `parse_to_datetime(raw_debut)` ; non parsable/vide → `continue`.
2. **Fin** (l.519-546) : mots-clés présent `["PRESENT","ACTUELLEMENT","AUJOURD'HUI","NOW","CURRENT","EN COURS"]` →
   `datetime.now()`. **Fin vide ≠ présent.** Année seule = même année que début → `31 décembre` (année pleine),
   sinon janvier. Non parsable → `continue`.
3. **Cohérence** (l.548-556) : `debut>fin` → swap ; `debut > now+30j` → `continue` ; sinon `periods.append`.

Puis : `merged = _merge_overlapping_periods(periods)` ; `total_months = Σ relativedelta` ;
**plancher** : si 0 mois mais périodes existantes → 1 mois ; `annees = round(total_months/12, 2)` ;
texte « X mois » / « 1 an » / « X ans » / « X an(s) et Y mois ».

⚠️ **Effet de bord** : v2 **mute les dicts en place** (dates réécrites) → repris dans le JSON stocké.
Au portage : **fonction pure** retournant périodes + expériences normalisées séparément.

### `_merge_overlapping_periods(periods)` (l.603-628)
Tri par date de début, fusion des intervalles qui se chevauchent (`start<=last_end` → `max(last_end,end)`).
Fonction pure, à porter telle quelle.

### `_normalize_extra_activities` (l.630-696)
Nettoie faux « null/none/nan/nit/n/a » → `""` ; gère « Depuis 2023 » → début 2023-01 + fin PRESENT.

## 3. `config.py` — Taxonomies

- **`SECTEURS_VALIDES`** (l.17-34, **16**) : Informatique / Tech · Finance / Banque / Assurance ·
  Marketing / Communication · Commerce / Vente · Ressources Humaines · Industrie / Production ·
  Santé / Médical · Éducation / Formation · Juridique / Legal · Logistique / Supply Chain ·
  BTP / Immobilier · Hôtellerie / Restauration · Art / Design / Création ·
  Agriculture / Environnement · Conseil / Audit · Autre.
- **`SKILL_MAPPINGS`** (l.37-67, **22** alias→canonique) : js→JavaScript, ts→TypeScript, py→Python,
  cpp→C++, c#→C#, golang→Go, reactjs/react.js→React, vuejs/vue.js→Vue.js, node/nodejs→Node.js,
  django framework→Django, aws→Amazon Web Services, gcp→Google Cloud Platform, azure→Microsoft Azure,
  docker container→Docker, k8s→Kubernetes, travail d'équipe/esprit d'équipe/team player→Travail en équipe,
  autonome→Autonomie.
- **Villes Maroc** — `DataCleaner.CITY_MAPPINGS` (`data_cleaner.py` l.63-68, **4 villes, 28 quartiers**) :
  casablanca (ain sebaa, sidi moumen, sidi bernoussi, maarif, racine, gauthier, californie, bouskoura,
  dar bouazza, tit mellil, mohammedia, nouaceur, hay mohammadi, bernoussi, roches noires, belvedere, ourgounda) ;
  rabat (agdal, hay riad, souissi, temara, skhirat, hassan, ocean) ; tanger (malabata, boukhalef) ;
  marrakech (gueliz, hivernage).

## 4. Prompt d'extraction LLM (`analyzer.py` l.348-425)

`secteurs_list = ", ".join(SECTEURS_VALIDES)` injecté ; CV injecté **tronqué à 4000 car.** (l.422, `{text[:4000]}`).
Schéma JSON attendu (racine) : `prenom, nom, email, telephone, ville, poste_actuel, secteur` (obligatoire, dans la
taxonomie), `specialite`, `experiences[]{poste,entreprise,date_debut,date_fin,description}`,
`activites_extra[]{titre,organisation,date_debut,date_fin,description}`, `formations[]{diplome,ecole,annee}`,
`hard_skills[]`, `soft_skills[]`, `langues[]`.

Règles clés du prompt (à conserver au portage) : secteur OBLIGATOIRE dans la liste ; dates « YYYY-MM » ou
« YYYY » (jamais de mois par défaut) ; « 2023-2024 » → fin=2024 (pas PRESENT) ; **séparation stricte**
expérience / formation / associatif ; valeurs manquantes → `null` (jamais la chaîne « null ») ; ville sans quartier.

⚠️ **Bugs à NE PAS reproduire** : clé **`"langues"` dupliquée** (l.802-803) ; **troncature 4000 car.** (l.422) ;
**`max_retries=0`** (l.302, tout le backoff est mort) ; parsing JSON **regex + `ast.literal_eval`** (l.115-137,
`NameError` latent sur `json_str`). → **remplacer par sorties structurées (function calling / JSON schema Pydantic).**

## 5. Cascade LLM (`analyzer.py` l.139-161)
`_call_llm(prompt, is_search)` : **Groq** (uniquement si `is_search=True`, modèle défaut `llama-3.3-70b-versatile`) →
**Gemini** (`gemini-1.5-flash`, `temperature=0.1`) → **HF** (`meta-llama/Llama-3.1-8B-Instruct`, `max_tokens=2000`).
Chaque provider tenté seulement si sa clé est présente ; 1er non-`None` gagne. → réécrire en interface propre.

## 6. `data_cleaner.py` — Nettoyage
- `normalize_skill` : `SKILL_MAPPINGS[skill.strip().lower()]` sinon inchangé.
- `clean_skills_list` : split `,`, strip, `normalize_skill`, **dédup insensible à la casse en gardant l'ordre**, re-join `", "`.
- `format_title` : `text.title().strip()` (effet : « IBM »→« Ibm »).
- `normalize_city` (l.70-94) : si ville principale ou quartier ∈ texte → ville principale `.title()` ;
  sinon retire chiffres + ponctuation (hors tiret) + `.title()`.

⚠️ **email/téléphone NON normalisés** dans le POC (stockés bruts) — contrairement à ce que suggérait le brief.
Si une normalisation est voulue, elle est **à créer**.

## 7. `database.py` — Recherche (à réécrire en SQL/ORM propre)
- Table unique dénormalisée `candidats` (skills/langues en **CSV**, `details_json`).
- `advanced_search(criteria)` (l.393-472) : filtres `ville/secteur/poste` (LIKE), `min/max_experience`, `keywords`.
  ⚠️ **BUG d'indentation (l.431-432)** : la boucle mots-clés est **piégée dans le bloc `max_experience`** →
  le filtre keywords n'est appliqué **que si `max_experience` est fourni** + `KeyError` possible. **À corriger** :
  désindenter, `.get('keywords', [])`, `LIMIT` paramétré.
- « Recherche IA » : `parse_search_query` (l.817-919) → JSON `{keywords, ville, secteur, poste, min/max_experience, limit}`.
  Post-traitements code-level à conserver : **AMBIGUOUS_NAMES** {doha, sofia, alexandria, victoria, charlotte,
  virginia, austin, orlando} (ville↔prénom) ; **STOP_WORDS** (candidat/profil/cv/… + tous les termes de niveau).

## 8. Synthèse de portage
- **(a) Porter quasi tel quel** (pur) : `DateNormalizer`, `_merge_overlapping_periods`,
  `_calculate_experience_v2` + `_calculate_seniorite` (rendre purs), taxonomies, `DataCleaner`.
- **(b) Réécrire proprement** : extraction LLM (sorties structurées), `parse_search_query`,
  recherche hybride (Postgres full-text + pgvector, **corriger le bug keywords**), extraction PDF/OCR, pipeline `analyze_cv`.
- **(c) Jeter** : tout `app.py` (Streamlit), `worker.py` (PID/threads/sleep), `drive_connector.py`
  (réécrire en Phase 3 si Drive au périmètre ; circuit breaker `sleep(600)`/`sleep(86400)` à bannir),
  `cleanup_manager.py`, `user_settings.py`, SQLite + logs maison.

**Points de vigilance** : mutation in-place des dates ; skills/langues en CSV (dédup ordonnée) ;
email/tel non normalisés ; **3 barèmes séniorité à unifier** ; bug indentation `advanced_search` ;
parsing JSON fragile → structuré.

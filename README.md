# Dar Zaytoun — site vitrine multilingue

Site vitrine d'un restaurant méditerranéen **fictif**, réalisé comme projet de portfolio.

- 4 langues : français, anglais, arabe (RTL), espagnol
- HTML, CSS et JavaScript natifs, **sans framework**
- Un générateur Python (`build.py`) **sans dépendance** produit les 4 pages à partir d'un gabarit unique
- Responsive (mobile d'abord), accessible (WCAG 2.1 AA, 0 erreur axe-core), animations légères
- SEO : `lang`, `hreflang`, `canonical`, descriptions traduites, Open Graph, sitemap, données structurées schema.org
- Prêt pour GitHub Pages (déploiement automatique inclus)

---

## Démarrage rapide

Prérequis : Python 3.8 ou plus récent. Rien d'autre à installer.

```bash
python3 build.py                 # génère le site dans dist/
python3 -m http.server -d dist   # puis ouvrir http://localhost:8000
```

> Ouvrez le site via un petit serveur local (comme ci-dessus), pas en double-cliquant sur
> le fichier : la page racine redirige vers `fr/`, et certains navigateurs limitent les
> pages ouvertes en `file://`.

Option : `python3 build.py --site-url https://moi.github.io/dar-zaytoun` pour préciser
l'URL publique. Elle sert aux balises `hreflang`/`canonical` et au sitemap.
Sinon, c'est la valeur `site_url` de `src/data/site.json` qui est utilisée.

---

## Structure du projet

```
dar-zaytoun/
├── build.py                  Générateur : gabarit + traductions → dist/
├── src/
│   ├── template.html         LE gabarit HTML unique (toutes les langues)
│   ├── data/site.json        Données communes : langues, prix, contact, horaires, galerie
│   ├── i18n/                 Les textes, un fichier par langue
│   │   ├── fr.json           ← langue de référence
│   │   ├── en.json
│   │   ├── ar.json
│   │   └── es.json
│   └── assets/
│       ├── css/style.css     Styles (propriétés logiques, mobile d'abord)
│       ├── js/main.js        Menu mobile, animations, langues, galerie, formulaire
│       └── img/              Illustrations SVG originales + favicon
├── dist/                     GÉNÉRÉ — ne jamais modifier à la main
│   ├── index.html            Redirige vers /fr/ (en conservant l'ancre #…)
│   ├── fr/ en/ ar/ es/       Une page par langue
│   ├── assets/               Copie de src/assets
│   ├── 404.html  sitemap.xml  robots.txt  .nojekyll
└── .github/workflows/deploy.yml   Build + publication sur GitHub Pages
```

**Où modifier quoi ?**

| Je veux changer…                         | Fichier                         |
|------------------------------------------|---------------------------------|
| un texte (titre, description, bouton…)   | `src/i18n/<langue>.json`        |
| un prix, le téléphone, l'adresse, les horaires « machine » | `src/data/site.json` |
| la structure HTML d'une section          | `src/template.html`             |
| les couleurs, polices, espacements       | `src/assets/css/style.css` (bloc « Design tokens » en haut) |
| un comportement (menu, formulaire…)      | `src/assets/js/main.js`         |

Après chaque modification : `python3 build.py`.

---

## Comment fonctionne `build.py`

1. Il lit `site.json` et les fichiers de traduction.
2. Il **vérifie** que chaque langue contient toutes les clés de `fr.json` (la langue de
   référence). S'il manque un texte, le build s'arrête et liste précisément les clés manquantes.
3. Pour chaque langue, il prépare un *contexte*, c'est-à-dire tout ce que le gabarit peut afficher :
   les textes traduits, les prix formatés selon la langue (`14 €`, `€14`, `7,50 €`),
   les liens vers les autres langues et les données structurées schema.org.
4. Il remplit `template.html` avec ce contexte et écrit `dist/<langue>/index.html`.
5. Il copie les assets et génère la redirection racine, la page 404, le sitemap et `robots.txt`.

### Syntaxe du gabarit

Le moteur fait environ 80 lignes, à lire dans `build.py`, section 1 :

| Syntaxe                                   | Rôle                                         |
|-------------------------------------------|----------------------------------------------|
| `{{ hero.title }}`                        | Affiche une valeur, échappée pour le HTML (sûr) |
| `{{{ json_ld }}}`                         | Affiche une valeur brute (réservé au JSON-LD) |
| `{% for item in cat.items %} … {% endfor %}` | Boucle sur une liste                      |
| `{% if item.veg %} … {% else %} … {% endif %}` | Condition (`if not …` accepté)          |
| `{# note #}`                              | Commentaire retiré du HTML final             |

Une clé inexistante provoque une erreur explicite, par exemple
`[es] Clé introuvable : « hero.titel »`. On ne publie donc jamais une page avec un trou.

---

## Modifier les textes

Ouvrez `src/i18n/fr.json` (ou une autre langue), modifiez la valeur entre guillemets, puis relancez
`python3 build.py`.

```json
"hero": {
  "tagline": "La maison de l'olivier : une cuisine généreuse…"
}
```

Points d'attention :
- C'est du JSON : guillemets doubles, pas de virgule après le dernier élément.
  En cas de faute, le build indique la ligne et la colonne.
- Les guillemets typographiques (« », “ ”) sont autorisés dans le texte.
  Un guillemet droit `"` doit être écrit `\"`.
- Dans les messages du formulaire, `{name}`, `{date}`, `{time}`, `{guests}` et `{count}`
  sont remplacés automatiquement : gardez-les tels quels.
- Les heures limites du formulaire (12:00–22:30) sont définies dans `site.json > booking`.
  Si vous les changez, mettez aussi à jour les textes `booking.hints.time` et `booking.errors.time`.

### Ajouter ou modifier un plat

1. Dans `src/data/site.json` > `menu`, ajoutez une ligne dans la bonne catégorie :
   ```json
   { "id": "chakchouka", "price": 15, "veg": true }
   ```
2. Dans **chaque** fichier de traduction, ajoutez le texte dans `menu.items` :
   ```json
   "chakchouka": { "name": "Chakchouka", "desc": "Poivrons, tomates, œufs pochés." }
   ```
Le prix n'est écrit qu'une fois. Si une traduction manque, le build le signale.

### Remplacer les illustrations par des photos

Déposez vos images dans `src/assets/img/`, de préférence en `.webp` d'environ 1600 px de large
pour l'accueil et 800 px pour la galerie. Mettez ensuite à jour `file`, `width` et `height`
dans `site.json > gallery`, et le chemin de `hero.svg` / `about.svg` dans `template.html`.
Pensez à adapter les textes alternatifs (`alt`) dans chaque traduction.
Sources libres de droits : Unsplash, Pexels.

---

## Ajouter une langue (exemple : italien)

1. **Copier** `src/i18n/fr.json` vers `src/i18n/it.json`.
2. **Adapter le bloc `_meta`** :
   ```jsonc
   "_meta": {
     "lang": "it",                 // code utilisé pour lang="" et hreflang
     "dir": "ltr",                 // "rtl" pour l'arabe, l'hébreu, le persan…
     "script": "latin",            // famille de polices : "latin" ou "arabic" (cf. site.json > fonts)
     "locale": "it_IT",            // Open Graph
     "intl_locale": "it-IT",       // format des dates dans le message de confirmation
     "price_format": "{price} €",
     "decimal_separator": ","
   }
   ```
3. **Traduire** toutes les autres valeurs, sans toucher aux clés.
4. **Déclarer la langue** dans `src/data/site.json` > `languages` :
   ```json
   { "code": "it", "label": "IT", "name": "Italiano" }
   ```
   L'ordre de cette liste est celui du sélecteur de langue.
5. Lancer `python3 build.py`. La page `dist/it/` est créée et le sélecteur, les balises `hreflang`,
   le sitemap et la page 404 de toutes les langues sont mis à jour automatiquement.

Pour une langue qui utilise un autre alphabet (grec, cyrillique, hébreu…), ajoutez une entrée
dans `site.json > fonts` (par ex. `"hebrew": "<url Google Fonts>"`), utilisez-la dans
`_meta.script`, et ajoutez dans `style.css` un bloc `:root:lang(he) { --font-heading: …; }`
sur le modèle du bloc arabe.

---

## Multilingue et RTL : les choix techniques

- **Une URL par langue** (`/fr/`, `/ar/`…) : c'est ce que recommande Google, et chaque page
  porte ses balises `hreflang` vers les autres langues, plus un `x-default` vers le français.
- **Le sélecteur garde la section** : les identifiants (`#menu`, `#booking`…) sont identiques
  dans toutes les langues. `main.js` détecte la section visible et réécrit les liens du
  sélecteur (`../en/` devient `../en/#menu`). Sans JavaScript, le lien mène simplement en haut de la page traduite.
- **RTL sans feuille de style séparée** : `style.css` n'utilise **que des propriétés logiques**
  (`margin-inline-start`, `padding-inline`, `inset-inline-end`, `border-inline-start`,
  `text-align: start`…). Avec `dir="rtl"` sur `<html>`, toute la mise en page s'inverse.
  Seuls quelques détails demandent une règle `[dir="rtl"]` :
  - le retournement des icônes flèches (`.icon--flip`) ;
  - l'origine du soulignement animé de la navigation ;
  - le sens des flèches du clavier dans la visionneuse (géré dans `main.js`).
- **Typographie arabe** : polices Amiri (titres) et Cairo (texte), interlignage plus grand,
  et **aucun `letter-spacing`**, car il casse les liaisons entre lettres arabes.
- **Contenus mixtes** : les prix et numéros de téléphone sont isolés avec `dir="ltr"` pour
  garder un ordre correct au milieu d'un texte arabe.

---

## Accessibilité

- Lien d'évitement « Aller au contenu principal », structure de titres h1 → h4 cohérente.
- Navigation 100 % clavier, focus visible partout. L'anneau de focus change de couleur sur
  les fonds sombres pour rester contrasté.
- Menu mobile : `aria-expanded`, fermeture avec Échap, ordre de tabulation logique.
- Visionneuse en `<dialog>` natif : focus piégé, Échap, retour du focus sur la vignette.
- Formulaire : `label` sur chaque champ, erreurs reliées par `aria-describedby`,
  `aria-invalid`, résumé annoncé dans une zone `role="status"`, focus déplacé sur le premier champ en erreur.
- Contrastes vérifiés : texte ≥ 4,5:1, bordures des champs ≥ 3:1.
- `prefers-reduced-motion` respecté : toutes les animations sont coupées.
- Le site reste utilisable sans JavaScript (contenu visible, navigation affichée en ligne).

### Palette

| Rôle            | Couleur   | Contraste mesuré                    |
|-----------------|-----------|-------------------------------------|
| Olive profond   | `#2E3520` | texte sable dessus : 11,9:1         |
| Olive           | `#55622F` | sur fond sable : 6,2:1              |
| Terre cuite     | `#A8462A` | texte blanc dessus : 5,9:1          |
| Safran          | `#E0B252` | sur olive profond : 6,5:1           |
| Sable clair     | `#FBF7EF` | fond principal                      |
| Sable           | `#F3EADA` | sections alternées                  |
| Encre           | `#22201B` | sur sable clair : 15,2:1            |
| Encre secondaire| `#57524A` | sur sable clair : 7,3:1             |

---

## Mise en ligne sur GitHub Pages

### Option A : automatique (recommandée)

1. Poussez le projet sur un dépôt GitHub (branche `main`).
2. Dans le dépôt : **Settings → Pages → Build and deployment → Source : « GitHub Actions »**.
3. À chaque `git push`, le workflow `.github/workflows/deploy.yml` lance `build.py` avec la
   bonne URL publique, puis publie `dist/`. Le site est en ligne à
   `https://<utilisateur>.github.io/<dépôt>/` et redirige vers `/fr/`.

### Option B : manuelle

Retirez `dist/` du `.gitignore`, lancez `python3 build.py --site-url https://<utilisateur>.github.io/<dépôt>`,
puis publiez le contenu de `dist/` sur une branche `gh-pages` (Settings → Pages → Source : branche `gh-pages`).

Tous les chemins internes sont relatifs (`../assets/…`). Le site fonctionne donc à la racine d'un
domaine comme dans un sous-dossier.

---

## Formulaire de réservation

La validation est faite côté navigateur uniquement : champs obligatoires, format de l'e-mail,
date non passée, fermeture du lundi, plage horaire, nombre de personnes, consentement.
L'envoi est **simulé**. Pour recevoir réellement les demandes, remplacez le `setTimeout`
de `initBookingForm()` dans `main.js` par un `fetch()` vers un service comme Formspree,
Basin ou une fonction serverless.

---

*Restaurant, adresse, téléphone et personnes fictifs. Illustrations originales créées pour ce projet.*

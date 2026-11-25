#!/usr/bin/env python3
"""
build.py — Générateur statique multilingue du site Dar Zaytoun.

Principe :
    src/template.html  (UN seul gabarit HTML)
  + src/i18n/*.json    (les textes, une langue par fichier)
  + src/data/site.json (les données communes : prix, contact, langues…)
  = dist/<langue>/index.html pour chaque langue

Utilisation :
    python3 build.py                                   # URL du site lue dans site.json
    python3 build.py --site-url https://moi.github.io/dar-zaytoun

Aucune dépendance externe : seule la bibliothèque standard de Python est utilisée.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import sys
from datetime import date
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Chemins du projet
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
DIST = ROOT / "dist"
TEMPLATE_FILE = SRC / "template.html"
I18N_DIR = SRC / "i18n"
SITE_FILE = SRC / "data" / "site.json"
ASSETS_DIR = SRC / "assets"


class BuildError(Exception):
    """Erreur « propre » : affichée sans trace Python, avec un message clair."""


# ===========================================================================
# 1. MINI MOTEUR DE GABARIT
# ---------------------------------------------------------------------------
# Syntaxe reconnue dans template.html :
#   {{ chemin.vers.valeur }}       -> valeur échappée (sûre pour le HTML)
#   {{{ chemin }}}                 -> valeur brute, NON échappée (JSON-LD…)
#   {% for x in liste %}…{% endfor %}
#   {% if valeur %}…{% else %}…{% endif %}   (accepte aussi « if not valeur »)
#   {# commentaire #}              -> retiré du HTML final
#
# Le gabarit est d'abord découpé en « jetons », puis transformé en arbre
# (parse), puis rendu avec un contexte (render). Une clé absente provoque une
# erreur explicite : cela évite de publier une page avec un texte manquant.
# ===========================================================================

TOKEN_RE = re.compile(r"({{{.*?}}}|{{.*?}}|{%.*?%})", re.S)
# {# commentaire #} : notes pour le développeur, supprimées du HTML généré
COMMENT_RE = re.compile(r"{#.*?#}\n?", re.S)


def parse_template(source: str) -> list:
    """Transforme le texte du gabarit en une liste de nœuds (arbre)."""
    source = COMMENT_RE.sub("", source)
    root: list = []
    # Pile des blocs ouverts : (type, liste_où_ajouter, nœud)
    stack: list = [("root", root, None)]

    for token in TOKEN_RE.split(source):
        if not token:
            continue
        target = stack[-1][1]

        if token.startswith("{{{"):
            target.append({"type": "raw", "path": token[3:-3].strip()})
        elif token.startswith("{{"):
            target.append({"type": "var", "path": token[2:-2].strip()})
        elif token.startswith("{%"):
            words = token[2:-2].split()
            keyword = words[0] if words else ""

            if keyword == "for":
                if len(words) != 4 or words[2] != "in":
                    raise BuildError(f"Syntaxe invalide : {token!r} (attendu : {{% for x in liste %}})")
                node = {"type": "for", "var": words[1], "iter": words[3], "body": []}
                target.append(node)
                stack.append(("for", node["body"], node))
            elif keyword == "if":
                node = {"type": "if", "expr": " ".join(words[1:]), "body": [], "else": []}
                target.append(node)
                stack.append(("if", node["body"], node))
            elif keyword == "else":
                kind, _, node = stack.pop()
                if kind != "if":
                    raise BuildError("{% else %} sans {% if %} correspondant")
                stack.append(("else", node["else"], node))
            elif keyword == "endfor":
                if stack.pop()[0] != "for":
                    raise BuildError("{% endfor %} sans {% for %} correspondant")
            elif keyword == "endif":
                if stack.pop()[0] not in ("if", "else"):
                    raise BuildError("{% endif %} sans {% if %} correspondant")
            else:
                raise BuildError(f"Instruction inconnue dans le gabarit : {token!r}")
        else:
            target.append({"type": "text", "value": token})

    if len(stack) != 1:
        raise BuildError(f"Bloc {{% {stack[-1][0]} %}} non fermé dans le gabarit")
    return root


def resolve(path: str, scopes: list[dict]) -> Any:
    """Cherche « a.b.c » dans les portées, de la plus locale à la plus globale.

    Les index de liste sont acceptés : « gallery_items.0.file ».
    """
    first, *rest = path.split(".")
    for scope in reversed(scopes):
        if first in scope:
            value = scope[first]
            break
    else:
        raise BuildError(f"Clé introuvable : « {path} »")

    for part in rest:
        if isinstance(value, dict) and part in value:
            value = value[part]
        elif isinstance(value, list) and part.isdigit() and int(part) < len(value):
            value = value[int(part)]
        else:
            raise BuildError(f"Clé introuvable : « {path} » (bloque sur « {part} »)")
    return value


def render_nodes(nodes: list, scopes: list[dict]) -> str:
    """Produit le HTML final à partir de l'arbre et du contexte."""
    out: list[str] = []
    for node in nodes:
        kind = node["type"]
        if kind == "text":
            out.append(node["value"])
        elif kind == "var":
            out.append(html.escape(str(resolve(node["path"], scopes)), quote=True))
        elif kind == "raw":
            out.append(str(resolve(node["path"], scopes)))
        elif kind == "for":
            items = resolve(node["iter"], scopes)
            for item in items:
                out.append(render_nodes(node["body"], scopes + [{node["var"]: item}]))
        elif kind == "if":
            expr = node["expr"]
            negate = expr.startswith("not ")
            value = bool(resolve(expr[4:].strip() if negate else expr, scopes))
            branch = node["body"] if value != negate else node["else"]
            out.append(render_nodes(branch, scopes))
    return "".join(out)


# ===========================================================================
# 2. CHARGEMENT ET VÉRIFICATION DES DONNÉES
# ===========================================================================

def load_json(path: Path) -> Any:
    """Charge un fichier JSON avec un message d'erreur lisible en cas de faute."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise BuildError(f"Fichier introuvable : {path.relative_to(ROOT)}")
    except json.JSONDecodeError as err:
        raise BuildError(
            f"JSON invalide dans {path.relative_to(ROOT)}, ligne {err.lineno}, "
            f"colonne {err.colno} : {err.msg}"
        )


def missing_keys(reference: Any, other: Any, prefix: str = "") -> list[str]:
    """Liste les clés présentes dans la langue de référence mais absentes ailleurs.

    Très utile quand on ajoute une langue : le build indique précisément
    quels textes il reste à traduire.
    """
    missing: list[str] = []
    if isinstance(reference, dict):
        if not isinstance(other, dict):
            return [prefix or "(racine)"]
        for key, ref_value in reference.items():
            path = f"{prefix}.{key}" if prefix else key
            if key not in other:
                missing.append(path)
            else:
                missing.extend(missing_keys(ref_value, other[key], path))
    return missing


def format_price(price: float, meta: dict) -> str:
    """14 -> « 14 € » (fr) ou « €14 » (en) ; 7.5 -> « 7,50 € » (fr)."""
    if float(price).is_integer():
        amount = str(int(price))
    else:
        amount = f"{price:.2f}".replace(".", meta.get("decimal_separator", "."))
    return meta["price_format"].format(price=amount)


# ===========================================================================
# 3. CONSTRUCTION DU CONTEXTE D'UNE PAGE
# ---------------------------------------------------------------------------
# Le contexte = tout ce que le gabarit peut afficher pour une langue donnée :
# les textes traduits + les données communes + quelques valeurs calculées
# (liens entre langues, menu avec prix formatés, données structurées SEO…).
# ===========================================================================

def build_context(code: str, translations: dict[str, dict], site: dict, site_url: str) -> dict:
    tr = translations[code]
    meta = tr["_meta"]
    default_lang = site["default_lang"]

    # --- Liens vers chaque langue (sélecteur + balises hreflang) -----------
    languages = []
    for lang in site["languages"]:
        lang_meta = translations[lang["code"]]["_meta"]
        languages.append({
            **lang,
            "url": f"../{lang['code']}/",              # lien relatif (sélecteur)
            "abs_url": f"{site_url}/{lang['code']}/",  # URL absolue (SEO)
            "dir": lang_meta["dir"],
            "locale": lang_meta["locale"],
            "current": lang["code"] == code,
        })

    # --- Menu : on fusionne prix (site.json) et textes (traduction) --------
    menu_categories = []
    for category in site["menu"]:
        items = []
        for item in category["items"]:
            text = tr["menu"]["items"].get(item["id"])
            if text is None:
                raise BuildError(f"[{code}] Plat sans traduction : menu.items.{item['id']}")
            items.append({
                **text,
                "id": item["id"],
                "price": format_price(item["price"], meta),
                "veg": item.get("veg", False),
            })
        menu_categories.append({
            "id": category["id"],
            "title": tr["menu"]["categories"][category["id"]],
            "items": items,
        })

    # --- Galerie : fichier + dimensions (site.json) et textes (traduction) -
    gallery_items = [
        {**image, **tr["gallery"]["items"][image["id"]]}
        for image in site["gallery"]
    ]

    page_url = f"{site_url}/{code}/"
    contact = site["contact"]

    # --- Données structurées schema.org (comprises par Google) -------------
    json_ld = {
        "@context": "https://schema.org",
        "@type": "Restaurant",
        "name": tr["brand"]["name"],
        "description": tr["seo"]["description"],
        "url": page_url,
        "image": f"{site_url}/assets/img/hero.svg",
        "inLanguage": meta["lang"],
        "servesCuisine": tr["seo"]["cuisine"],
        "priceRange": site["price_range"],
        "telephone": contact["phone_href"],
        "email": contact["email"],
        "acceptsReservations": True,
        "address": {
            "@type": "PostalAddress",
            "streetAddress": contact["street"],
            "postalCode": contact["postal_code"],
            "addressLocality": contact["city"],
            "addressCountry": contact["country"],
        },
        "openingHoursSpecification": [
            {"@type": "OpeningHoursSpecification", **spec}
            for spec in site["opening_hours"]
        ],
    }
    # « </ » est échappé pour ne jamais fermer la balise <script> par erreur.
    json_ld_str = json.dumps(json_ld, ensure_ascii=False, indent=2).replace("</", "<\\/")

    return {
        **tr,
        "site": site,
        "lang": meta["lang"],
        "dir": meta["dir"],
        "languages": languages,
        "menu_categories": menu_categories,
        "gallery_items": gallery_items,
        "json_ld": json_ld_str,
        "year": date.today().year,
        "page": {
            "url": page_url,
            "default_url": f"{site_url}/{default_lang}/",
            "fonts_url": site["fonts"][meta["script"]],
        },
    }


# ===========================================================================
# 4. FICHIERS ANNEXES : redirection racine, 404, sitemap, robots
# ===========================================================================

def root_redirect(site: dict, site_url: str) -> str:
    """Page racine : redirige immédiatement vers la langue par défaut."""
    lang = site["default_lang"]
    return f"""<!doctype html>
<html lang="{lang}">
<head>
  <meta charset="utf-8">
  <title>Dar Zaytoun</title>
  <meta name="robots" content="noindex">
  <link rel="canonical" href="{site_url}/{lang}/">
  <!-- Redirection sans JavaScript -->
  <meta http-equiv="refresh" content="0; url={lang}/">
  <!-- Redirection JavaScript : conserve l'ancre éventuelle (#menu…) -->
  <script>location.replace("{lang}/" + location.hash);</script>
</head>
<body>
  <p><a href="{lang}/">Dar Zaytoun</a></p>
</body>
</html>
"""


def not_found_page(site: dict, translations: dict, site_url: str) -> str:
    """Page 404 de GitHub Pages, autonome (styles intégrés), en 4 langues."""
    blocks = []
    for lang in site["languages"]:
        tr = translations[lang["code"]]
        nf = tr["not_found"]
        blocks.append(
            f'<section lang="{lang["code"]}" dir="{tr["_meta"]["dir"]}">'
            f'<h2>{html.escape(nf["title"])}</h2>'
            f'<p><a href="{site_url}/{lang["code"]}/">{html.escape(nf["link"])}</a></p>'
            f"</section>"
        )
    return f"""<!doctype html>
<html lang="{site['default_lang']}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="noindex">
  <title>404 — Dar Zaytoun</title>
  <style>
    body {{ margin: 0; min-height: 100vh; display: grid; place-content: center; gap: 1.5rem;
           padding: 2rem; background: #2E3520; color: #FBF7EF; text-align: center;
           font-family: system-ui, sans-serif; }}
    h1 {{ font-family: Georgia, serif; font-size: 4rem; margin: 0; color: #E0B252; }}
    h2 {{ font-size: 1.1rem; margin: 0 0 .25rem; }}
    p {{ margin: 0; }}
    a {{ color: #E0B252; }}
    a:focus-visible {{ outline: 3px solid #E0B252; outline-offset: 3px; }}
  </style>
</head>
<body>
  <h1>404</h1>
  {''.join(blocks)}
</body>
</html>
"""


def sitemap(site: dict, site_url: str) -> str:
    """Sitemap avec les alternatives hreflang de chaque page."""
    alternates = "".join(
        f'\n    <xhtml:link rel="alternate" hreflang="{l["code"]}" href="{site_url}/{l["code"]}/"/>'
        for l in site["languages"]
    )
    urls = "".join(
        f"\n  <url>\n    <loc>{site_url}/{l['code']}/</loc>{alternates}\n  </url>"
        for l in site["languages"]
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
        'xmlns:xhtml="http://www.w3.org/1999/xhtml">'
        f"{urls}\n</urlset>\n"
    )


# ===========================================================================
# 5. ORCHESTRATION
# ===========================================================================

def build(site_url: str | None) -> None:
    site = load_json(SITE_FILE)
    site_url = (site_url or os.environ.get("SITE_URL") or site["site_url"]).rstrip("/")
    codes = [lang["code"] for lang in site["languages"]]

    # 1) Charger toutes les traductions
    translations = {code: load_json(I18N_DIR / f"{code}.json") for code in codes}

    # 2) Vérifier qu'aucune langue n'oublie un texte (référence = langue par défaut)
    reference = translations[site["default_lang"]]
    problems = []
    for code in codes:
        for key in missing_keys(reference, translations[code]):
            problems.append(f"  - {code}.json : clé manquante « {key} »")
    if problems:
        raise BuildError("Traductions incomplètes :\n" + "\n".join(problems))

    # 3) Repartir d'un dossier dist/ propre
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir()
    shutil.copytree(ASSETS_DIR, DIST / "assets")

    # 4) Générer une page par langue
    template = parse_template(TEMPLATE_FILE.read_text(encoding="utf-8"))
    for code in codes:
        context = build_context(code, translations, site, site_url)
        try:
            page = render_nodes(template, [context])
        except BuildError as err:
            raise BuildError(f"[{code}] {err}")
        out_dir = DIST / code
        out_dir.mkdir()
        (out_dir / "index.html").write_text(page, encoding="utf-8")
        print(f"  ✓ dist/{code}/index.html")

    # 5) Fichiers annexes
    (DIST / "index.html").write_text(root_redirect(site, site_url), encoding="utf-8")
    (DIST / "404.html").write_text(not_found_page(site, translations, site_url), encoding="utf-8")
    (DIST / "sitemap.xml").write_text(sitemap(site, site_url), encoding="utf-8")
    (DIST / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {site_url}/sitemap.xml\n", encoding="utf-8")
    # .nojekyll : indique à GitHub Pages de servir les fichiers tels quels
    (DIST / ".nojekyll").write_text("", encoding="utf-8")
    print("  ✓ dist/index.html (redirection), 404.html, sitemap.xml, robots.txt")
    print(f"Terminé : {len(codes)} langues générées pour {site_url}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Génère le site Dar Zaytoun dans dist/.")
    parser.add_argument("--site-url", help="URL publique du site, ex. https://moi.github.io/dar-zaytoun")
    args = parser.parse_args()
    try:
        build(args.site_url)
    except BuildError as err:
        print(f"Erreur : {err}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

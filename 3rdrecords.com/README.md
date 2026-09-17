# 3rdrecords.com

Site statique du label 3rd Records, sans traceur ni cookie.

Pages générées : accueil, `/catalog/`, `/releases/<slug>/`, `/artists/`, `/artists/<slug>/`, `/news/`, `/contact/` (+ `/duck/` et le portfolio).
Le script `js/site.js` ajoute les interactions : menu mobile, apparitions au scroll, vinyle à « scratcher », égaliseur, carrousel du catalogue (flèches du clavier), filtre par artiste, lecteurs Spotify chargés au clic, copie de l'adresse e-mail. Toutes les pages restent lisibles sans JavaScript.

- `site.json` : le contenu (texte du label, artistes, dernière sortie et liens d'écoute).
- `assets/*.svg` : les logos vectorisés (marque 3RD, mot « records », logo rond).
- `fonts/` : Avigea (titres) et Roboto (texte), sous-ensembles latin en woff2.
- `js/site.js` : les interactions (copié tel quel dans `dist/js/`).
- `build.py` : génère `dist/`. Il faut Python 3.9+ ainsi que `pip install pillow cairosvg`.

Pour une nouvelle sortie, ajoute-la en tête de `releases` dans `site.json` puis pousse sur `main` : GitHub Actions reconstruit et redéploie le site.
Les pochettes et photos d'artistes sont servies depuis le site de l'artiste (djouher.com/img/…).

## Portfolio Lead Major (3rdrecords.com/portfolio/leadmajor/)

- Contenu : `portfolio/leadmajor.json` (projets du carrousel, playlist SYNC, discographie, contact).
- Générateur : `portfolio/portfolio.py`, appelé par `build.py`.
- Les images distantes (Canva, Apple, YouTube) sont téléchargées et converties en WebP pendant le build. Pour remplacer une image, dépose un fichier `portfolio/img/<clé>.webp` (clés : portrait, braquass, ikh, showreel, kingdom, lbb, lastnight).
- Polices : `portfolio/fonts/` (Bricolage Grotesque, Inter, JetBrains Mono, licence OFL).

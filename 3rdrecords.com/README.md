# 3rdrecords.com

Site statique du label 3rd Records, sans traceur ni cookie.

Pages générées : accueil, `/catalog/`, `/releases/<slug>/`, `/artists/`, `/artists/<slug>/`, `/news/`, `/submit/`, `/contact/`, `/legal/` (+ `/duck/` et le portfolio).
Le script `js/site.js` ajoute les interactions : menu mobile, apparitions au scroll, vinyle à « scratcher », égaliseur, carrousel du catalogue (flèches du clavier), filtre par artiste, lecteurs Spotify chargés au clic, copie de l'adresse e-mail. Toutes les pages restent lisibles sans JavaScript.

- `site.json` : le contenu (texte du label, artistes, dernière sortie et liens d'écoute).
- `assets/*.svg` : les logos vectorisés (marque 3RD, mot « records », logo rond).
- `fonts/` : Avigea (titres) et Roboto (texte), sous-ensembles latin en woff2.
- `js/site.js` : les interactions ; `js/scratch.js` : le son de scratch du vinyle (AudioWorklet). Copiés tels quels dans `dist/js/`.
- `build.py` : génère `dist/`. Il faut Python 3.9+ ainsi que `pip install pillow cairosvg`.

Pour une nouvelle sortie, ajoute-la en tête de `releases` dans `site.json` puis pousse sur `main` : GitHub Actions reconstruit et redéploie le site.
Les pochettes et photos d'artistes sont servies depuis le site de l'artiste (djouher.com/img/…).

## Portfolio Lead Major (3rdrecords.com/portfolio/leadmajor/)

- Contenu : `portfolio/leadmajor.json` (projets du carrousel, playlist SYNC, discographie, contact).
- Générateur : `portfolio/portfolio.py`, appelé par `build.py`.
- Les images distantes (Canva, Apple, YouTube) sont téléchargées et converties en WebP pendant le build. Pour remplacer une image, dépose un fichier `portfolio/img/<clé>.webp` (clés : portrait, braquass, ikh, showreel, kingdom, lbb, lastnight).
- Polices : `portfolio/fonts/` (Bricolage Grotesque, Inter, JetBrains Mono, licence OFL).

## Formulaire de submissions (3rdrecords.com/submit/)

- Le formulaire envoie les données au script Google Apps Script « 3rd Records Duck Scoreboard » (compte awen.vannier@gmail.com), le même que le scoreboard du jeu. URL dans `site.json` → `submit_api`.
- Chaque envoi ajoute une ligne dans la Google Sheet « 3rd Records Submissions » (onglet `submissions`) et envoie un e-mail à contact@3rdrecords.com (répondre au mail répond directement à l'artiste).
- Champs : titre, genre (Pop, Bedroom pop, Lofi, Hip-hop, Other), lien d'écoute, nom d'artiste, e-mail, Instagram, profil streaming, description, case droits.
- Anti-spam : champ piège invisible, envoi refusé avant 4 s, 3 envois max par e-mail sur 6 h, 60 envois max par heure.
- Code du script : `scoreboard/Code.gs`. Après modification : Déployer → Gérer les déploiements → modifier → Nouvelle version.

## Mentions legales (3rdrecords.com/legal/)

- Les informations (SIRET, forme juridique, RCS, code APE, hebergeur, duree de conservation des submissions) sont dans `site.json` -> `legal`. La date « Last updated » vient de `legal.updated`.
- La page couvre : mentions legales, politique de submissions (rien n'est utilise sans accord ecrit, suppression apres 12 mois), vie privee (Google Sheet + boite mail, droits RGPD, pas de tracker, lecteurs Spotify au clic, scoreboard du jeu public) et droits sur les contenus.
- Lien dans le pied de page de toutes les pages et sous le formulaire de submissions.

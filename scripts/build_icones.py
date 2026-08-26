"""Engendre les icônes de l'application installable.

Les icônes ne sont pas dessinées à la main : elles sont TRACÉES ici, à partir
des couleurs du site (`assets/css/style.css`), pour qu'un changement de teinte
ne laisse pas derrière lui une icône qui dit l'ancienne. Même doctrine que
`build_methode.py` pour la page de méthode.

Le tracé est fait quatre fois trop grand puis réduit : c'est ce qui donne
l'anticrénelage, `ImageDraw` n'en faisant aucun.

Usage :
    python3 scripts/build_icones.py
"""

import os

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEST = os.path.join(ROOT, "assets", "icones")

FOND = (26, 54, 93)        # --accent-vif : le bleu institutionnel du site
MARQUE = (255, 255, 255)
SS = 4                     # facteur de suréchantillonnage


def tracer(taille, part_marque=0.52, rayon_coin=0.22):
    """Un carré bleu, coins arrondis, portant un € blanc.

    `part_marque` est la largeur du € rapportée au côté. Une icône masquable
    la réduit : Android peut rogner jusqu'au cercle inscrit à 80 %, tout ce
    qui dépasse de la zone sûre est perdu.
    """
    c = taille * SS
    img = Image.new("RGBA", (c, c), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    if rayon_coin > 0:
        d.rounded_rectangle([0, 0, c - 1, c - 1], radius=int(c * rayon_coin), fill=FOND)
    else:
        d.rectangle([0, 0, c - 1, c - 1], fill=FOND)

    # Le € : un arc ouvert à droite, barré de deux traits horizontaux.
    r = c * part_marque / 2
    cx, cy = c / 2 + r * 0.16, c / 2
    trait = max(2, int(r * 0.30))
    boite = [cx - r, cy - r, cx + r, cy + r]
    d.arc(boite, start=38, end=322, fill=MARQUE, width=trait)

    demi = trait / 2
    for dy in (-r * 0.30, r * 0.30):
        y = cy + dy
        d.rounded_rectangle([cx - r * 1.32, y - demi, cx + r * 0.26, y + demi],
                            radius=demi, fill=MARQUE)

    return img.resize((taille, taille), Image.LANCZOS)


def ecrire(img, nom, opaque=False):
    if opaque:                      # iOS n'aime pas la transparence : il la noircit.
        fond = Image.new("RGB", img.size, FOND)
        fond.paste(img, mask=img.split()[3])
        img = fond
    chemin = os.path.join(DEST, nom)
    img.save(chemin, optimize=True)
    print(f"  {nom}  {os.path.getsize(chemin) / 1024:.1f} Ko")


def main():
    os.makedirs(DEST, exist_ok=True)
    print("Icônes de l'application installable\n")
    ecrire(tracer(32), "favicon-32.png")
    ecrire(tracer(180, rayon_coin=0), "apple-touch-icon.png", opaque=True)
    ecrire(tracer(192), "icone-192.png")
    ecrire(tracer(512), "icone-512.png")
    # Masquable : plein cadre, marque rentrée dans la zone sûre des 80 %.
    ecrire(tracer(512, part_marque=0.40, rayon_coin=0), "icone-maskable-512.png")


if __name__ == "__main__":
    main()

# Andy Café — Preview Dark Luxury Editorial · v2

**Le Cabinet de Torréfaction** — direction artistique éditoriale dark luxury.

Captures du rendu généré depuis `preview/index.html` via Chromium headless.

## Identité

- **Display** : Fraunces (variable, opsz 144, SOFT 100, WONK 1 pour les italiques)
- **UI / corps** : Bricolage Grotesque (variable)
- **Palette** : coal `#07060a`, ink, cocoa, smoke, accents or champagne `#c9a35a`, oxblood `#5a1c1c`
- **Numérotation** : `01 — Le Cabinet`, `02 — Histoire`, `03 — Univers`…
- **Ornements** : lettres italiques géantes en filigrane (le `a` du hero, le `&` de la story)
- **Cursor** : custom (point + ring qui s'élargit sur les liens)
- **Animations** : reveal mot par mot dans le hero, mask reveal images, parallax, magnetic, 3D tilt, counters

## Vue complète

| Desktop (1440px) | Mobile (390px) |
|---|---|
| ![Desktop full](screenshots/desktop-full.jpg) | ![Mobile full](screenshots/mobile-full.jpg) |

## Sections — Desktop

### 01 — Hero (cinematic, ornement géant)
![Hero](screenshots/desktop-01-hero.jpg)

### Marquee italique (Fraunces 144 wonk)
![Marquee](screenshots/desktop-02-marquee.jpg)

### 02 — Story (split asymétrique, image clip-corner, ornement `&`)
![Story](screenshots/desktop-03-story.jpg)

### 03 — Univers / Collections (mosaïque cassée 12-col, numéros)
![Collections](screenshots/desktop-04-collections.jpg)

### 04 — Cuvées (grille éditoriale alternant 1 large + 2 small)
![Products](screenshots/desktop-05-products.jpg)

### Méthode (cream-light contrast — iv étapes)
![Méthode](screenshots/desktop-05b-methode.jpg)

### Cuvée du moment (oxblood color punch)
![Band](screenshots/desktop-05c-band.jpg)

### 06 — Engagements (bento mixed grid)
![Bento](screenshots/desktop-05d-bento.jpg)

### Quote band (guillemet géant ornement)
![Quote](screenshots/desktop-06-quote.jpg)

### 05 — Témoignages (zig-zag offset cards)
![Reviews](screenshots/desktop-07-reviews.jpg)

### 06 — Lettre (split editorial layout)
![Newsletter](screenshots/desktop-08-newsletter.jpg)

### Footer
![Footer](screenshots/desktop-09-footer.jpg)

## Sections — Mobile

| Hero | Marquee | Story |
|---|---|---|
| ![Hero](screenshots/mobile-01-hero.jpg) | ![Marquee](screenshots/mobile-02-marquee.jpg) | ![Story](screenshots/mobile-03-story.jpg) |

| Collections | Produits | Quote |
|---|---|---|
| ![Collections](screenshots/mobile-04-collections.jpg) | ![Products](screenshots/mobile-05-products.jpg) | ![Quote](screenshots/mobile-06-quote.jpg) |

| Reviews | Newsletter | Footer |
|---|---|---|
| ![Reviews](screenshots/mobile-07-reviews.jpg) | ![Newsletter](screenshots/mobile-08-newsletter.jpg) | ![Footer](screenshots/mobile-09-footer.jpg) |

## Interactions live (visibles uniquement en navigateur)

- **Custom cursor** desktop : point crème + ring qui s'élargit avec teinte or sur tous les éléments interactifs (mix-blend-mode: difference)
- **Hero reveal** : titre dévoilé mot par mot (clip-mask + translateY) avec stagger
- **Cursor-following gradient** : le hero suit la souris avec un orbe doré qui s'éloigne du curseur
- **Magnetic CTAs** : tous les boutons et liens éditoriaux suivent le curseur
- **3D tilt** : les cartes produits/collections s'inclinent au passage de souris
- **Header solidify** : nav devient plus opaque + blur après 24px de scroll
- **Counters** : 12, 47, 98 s'animent au scroll dans la section histoire
- **Parallax** : background hero glisse plus lentement que le scroll

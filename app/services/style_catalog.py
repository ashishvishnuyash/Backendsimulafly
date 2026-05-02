"""Static catalog of design-style templates (Living Room, Bedroom, etc.).

Source: `Docs/eof.docx` — the editorial style spec.

The catalog is hardcoded (not DB-backed) because:
  - it changes at the speed of editorial decisions, not user actions;
  - it's small (~95 entries) — a JSON read on every request would be more
    code than this module;
  - shipping it with the source means it's versioned with the API.

Images live under `Backendsimulafly/data/styles/img_XXX.jpg` and are served
statically from `/static/styles/...` (mounted in `app.main`). Each style
points at one image; if a style has no image yet, `image_url` is `None`
and the client renders a striped placeholder.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class StyleTemplate:
    slug: str
    name: str
    category: str  # "Living Room" | "Bedroom" | ... — also the display section.
    vibe: str
    image_filename: str | None = None
    trending: bool = False


# Image filenames (relative to `data/styles/`). 50 available.
def _img(n: int) -> str:
    return f"img_{n:03d}.jpg"


# ──────────────────────────────────────────────────────────────────────────────
# 1. Living Room
# ──────────────────────────────────────────────────────────────────────────────

_LIVING = [
    StyleTemplate(
        "modern-indian-elegance",
        "Modern Indian Elegance",
        "Living Room",
        "Rich walnut woods, subtle brass accents, jewel-toned upholstery.",
        _img(1),
        trending=True,
    ),
    StyleTemplate(
        "mid-century-modern",
        "Mid-Century Modern",
        "Living Room",
        "Tapered furniture legs, mustard accents, clean functional lines.",
        _img(2),
        trending=True,
    ),
    StyleTemplate(
        "japandi",
        "Japandi",
        "Living Room",
        "Light oak, slatted wall panels, calming neutral fabrics.",
        _img(3),
    ),
    StyleTemplate(
        "boho-chic",
        "Boho Chic",
        "Living Room",
        "Rattan, macramé, layered rugs, abundant indoor plants.",
        _img(4),
        trending=True,
    ),
    StyleTemplate(
        "contemporary-luxe",
        "Contemporary Luxe",
        "Living Room",
        "High-gloss marble, fluted panels, gold or champagne trims.",
        _img(5),
    ),
    StyleTemplate(
        "chettinad-twist",
        "Heritage / Chettinad Twist",
        "Living Room",
        "Carved dark wood, block-print cushions, traditional Indian art.",
        _img(6),
    ),
    StyleTemplate(
        "warm-minimalist",
        "Warm Minimalist",
        "Living Room",
        "Clutter-free, soft curved furniture, earthy beige or terracotta.",
        _img(7),
    ),
    StyleTemplate(
        "tropical-oasis",
        "Tropical / Urban Oasis",
        "Living Room",
        "Cane furniture, bold botanicals, vibrant emerald greens.",
        _img(8),
    ),
    StyleTemplate(
        "pastel-scandinavian",
        "Pastel & Scandinavian",
        "Living Room",
        "Light woods, blush pinks or mint greens, airy windows.",
        _img(9),
    ),
    StyleTemplate(
        "industrial-loft",
        "Industrial Loft",
        "Living Room",
        "Exposed brick, distressed leather, matte black fixtures.",
        _img(10),
    ),
]

# ──────────────────────────────────────────────────────────────────────────────
# 2. Bedroom
# ──────────────────────────────────────────────────────────────────────────────

_BEDROOM = [
    StyleTemplate(
        "zen-sanctuary",
        "Zen Sanctuary",
        "Bedroom",
        "Low-profile beds, bamboo textures, distraction-free layout.",
        _img(11),
        trending=True,
    ),
    StyleTemplate(
        "boutique-hotel-luxe",
        "Boutique Hotel Luxe",
        "Bedroom",
        "Upholstered headboards, warm cove lighting, plush velvet.",
        _img(12),
    ),
    StyleTemplate(
        "bedroom-modern-minimalist",
        "Modern Minimalist",
        "Bedroom",
        "Handleless wardrobes, floating side tables, crisp white linens.",
        _img(13),
    ),
    StyleTemplate(
        "royal-indian-heritage",
        "Royal Indian Heritage",
        "Bedroom",
        "Four-poster beds, silk fabrics, intricate floral wallpapers.",
        _img(14),
    ),
    StyleTemplate(
        "cozy-reading-nook",
        "Cozy Reading Nook",
        "Bedroom",
        "Layered throws, warm lamps, overstuffed accent chairs.",
        _img(15),
    ),
    StyleTemplate(
        "earthy-terracotta",
        "Earthy Terracotta",
        "Bedroom",
        "Baked clay tones, linen fabrics, sun-drenched aesthetics.",
        _img(16),
    ),
    StyleTemplate(
        "classic-victorian-twist",
        "Classic Victorian Twist",
        "Bedroom",
        "Wainscoting, muted pastels, vintage bedside lamps.",
        _img(17),
    ),
    StyleTemplate(
        "compact-smart-space",
        "Compact Smart-Space",
        "Bedroom",
        "Integrated study desks, hidden storage beds, efficient layouts.",
        _img(18),
    ),
    StyleTemplate(
        "moody-and-dramatic",
        "Moody & Dramatic",
        "Bedroom",
        "Deep navy or charcoal walls, amber lighting, rich wood tones.",
        _img(19),
        trending=True,
    ),
    StyleTemplate(
        "scandinavian-calm",
        "Scandinavian Calm",
        "Bedroom",
        "Cool greys, bright whites, textured wool or cotton fabrics.",
        _img(20),
    ),
]

# ──────────────────────────────────────────────────────────────────────────────
# 3. Kitchen
# ──────────────────────────────────────────────────────────────────────────────

_KITCHEN = [
    StyleTemplate(
        "modern-handleless",
        "Modern Handleless",
        "Kitchen",
        "Seamless gloss cabinets, integrated appliances, easy clean-up.",
        _img(21),
    ),
    StyleTemplate(
        "indian-traditional-wood",
        "Indian Traditional Wood",
        "Kitchen",
        "Solid teak, brass hardware, warm granite countertops.",
        _img(22),
    ),
    StyleTemplate(
        "two-tone-contemporary",
        "Two-Tone Contemporary",
        "Kitchen",
        "Navy lower cabinets, crisp white uppers, bright quartz top.",
        _img(23),
    ),
    StyleTemplate(
        "classic-shaker",
        "Classic Shaker",
        "Kitchen",
        "Paneled cabinet doors, warm undertones, inviting family feel.",
        _img(24),
    ),
    StyleTemplate(
        "luxe-marble-clad",
        "Luxe Marble-Clad",
        "Kitchen",
        "Marble-veined backsplashes, profile lighting, gold accents.",
        _img(25),
    ),
    StyleTemplate(
        "minimalist-white",
        "Minimalist White",
        "Kitchen",
        "All-white matte cabinets, invisible hardware, expansive feel.",
        _img(26),
    ),
    StyleTemplate(
        "industrial-edge",
        "Industrial Edge",
        "Kitchen",
        "Concrete-textured laminates, matte black handles, open shelves.",
        _img(27),
    ),
    StyleTemplate(
        "pastel-and-bright",
        "Pastel & Bright",
        "Kitchen",
        "Soft mint or butter-yellow cabinets, cheerful airy vibe.",
        _img(28),
    ),
    StyleTemplate(
        "wood-and-grey-fusion",
        "Wood & Grey Fusion",
        "Kitchen",
        "Slate grey matte paired with warm walnut wood lofts.",
        _img(29),
    ),
    StyleTemplate(
        "compact-modular",
        "Compact Modular Efficiency",
        "Kitchen",
        "Floor-to-ceiling storage, magic pull-outs, optimised counters.",
        _img(30),
    ),
]

# ──────────────────────────────────────────────────────────────────────────────
# 4. Bathroom
# ──────────────────────────────────────────────────────────────────────────────

_BATHROOM = [
    StyleTemplate(
        "modern-spa-retreat",
        "Modern Spa Retreat",
        "Bathroom",
        "Stone-finish tiles, rain shower, recessed cove lighting.",
        _img(31),
    ),
    StyleTemplate(
        "classic-marble-luxe",
        "Classic Marble Luxe",
        "Bathroom",
        "Italian marble, brass or gold fixtures, backlit vanity mirrors.",
        _img(32),
    ),
    StyleTemplate(
        "minimalist-monochrome",
        "Minimalist Monochrome",
        "Bathroom",
        "Matte black fittings, white subway tiles, frameless glass.",
        _img(33),
    ),
    StyleTemplate(
        "tropical-bath",
        "Tropical Oasis",
        "Bathroom",
        "Wood-finish porcelain, indoor plants, pebble floor accents.",
        _img(34),
    ),
    StyleTemplate(
        "contemporary-neutral-bath",
        "Contemporary Neutral",
        "Bathroom",
        "Beige or soft grey tiles, floating vanities, easy-to-wipe lines.",
        _img(35),
    ),
    StyleTemplate(
        "moroccan-vibe",
        "Moroccan Vibe",
        "Bathroom",
        "Encaustic tiles, arched mirrors, antique brass accents.",
        _img(36),
    ),
    StyleTemplate(
        "earthy-terracotta-bath",
        "Earthy Terracotta",
        "Bathroom",
        "Baked-clay tones, textured walls, matte copper hardware.",
        _img(37),
    ),
    StyleTemplate(
        "compact-smart-bath",
        "Compact Smart Bath",
        "Bathroom",
        "Wall-hung commodes, mirror storage, bright space-expanding light.",
        _img(38),
    ),
    StyleTemplate(
        "neo-classic-elegance",
        "Neo-Classic Elegance",
        "Bathroom",
        "Tile wainscoting, ornate frames, freestanding tub.",
        _img(39),
    ),
    StyleTemplate(
        "brutalist-chic",
        "Brutalist Chic",
        "Bathroom",
        "Concrete-look finishes, raw textures, matte black fixtures.",
        _img(40),
    ),
]

# ──────────────────────────────────────────────────────────────────────────────
# 5. Dining Room
# ──────────────────────────────────────────────────────────────────────────────

_DINING = [
    StyleTemplate(
        "indian-heritage",
        "Indian Heritage",
        "Dining Room",
        "Carved teak tables, brass tableware, traditional artwork.",
        _img(41),
    ),
    StyleTemplate(
        "warm-minimalist-dining",
        "Warm Minimalist",
        "Dining Room",
        "Light oak table, upholstered chairs, singular pendant.",
        _img(42),
    ),
    StyleTemplate(
        "contemporary-glam",
        "Contemporary Glam",
        "Dining Room",
        "Marble or onyx top, velvet chairs, crystal chandelier.",
        _img(43),
    ),
    StyleTemplate(
        "open-plan-seamless",
        "Open-Plan Seamless",
        "Dining Room",
        "Flows into the living area, matching wood tones, low-profile seating.",
        _img(44),
    ),
    StyleTemplate(
        "mid-century-dining",
        "Mid-Century Modern",
        "Dining Room",
        "Tapered legs, cane-back chairs, geometric light fixtures.",
        _img(45),
    ),
    StyleTemplate(
        "rustic-farmhouse",
        "Rustic Farmhouse",
        "Dining Room",
        "Live-edge wood, bench seating, warm industrial lighting.",
        _img(46),
    ),
    StyleTemplate(
        "japandi-dining",
        "Japandi Dining",
        "Dining Room",
        "Low chairs, light woods, wabi-sabi ceramics.",
        _img(47),
    ),
    StyleTemplate(
        "eclectic-bohemian",
        "Eclectic Bohemian",
        "Dining Room",
        "Mix-and-match chairs, handloom runner, rattan pendants.",
        _img(48),
    ),
    StyleTemplate(
        "compact-bistro",
        "Compact Bistro",
        "Dining Room",
        "Round tables, armless chairs, floating buffet unit.",
        _img(49),
    ),
    StyleTemplate(
        "modern-luxury-dining",
        "Modern Luxury",
        "Dining Room",
        "Tinted glass top, gold base, premium leather seating.",
        _img(50),
    ),
]

# ──────────────────────────────────────────────────────────────────────────────
# 6. Study / Home Office  (cycle images 1-10 since the docx has 50)
# ──────────────────────────────────────────────────────────────────────────────

_STUDY = [
    StyleTemplate("executive-modern", "Executive Modern", "Study",
        "Dark wood executive desk, leather chair, built-in bookshelf.", _img(1)),
    StyleTemplate("minimalist-focus", "Minimalist Focus", "Study",
        "White floating desk, hidden cables, neutral walls.", _img(2)),
    StyleTemplate("creative-studio", "Creative Studio", "Study",
        "Pegboard walls, drafting tables, vibrant accent colors.", _img(3)),
    StyleTemplate("biophilic-workspace", "Biophilic Workspace", "Study",
        "Natural light, indoor plants, raw wood textures.", _img(4)),
    StyleTemplate("cozy-library", "Cozy Library", "Study",
        "Floor-to-ceiling bookshelves, reading armchair, brass lamps.", _img(5)),
    StyleTemplate("industrial-tech", "Industrial Tech", "Study",
        "Metal-pipe legs, dual monitor mounts, exposed brick.", _img(6)),
    StyleTemplate("mid-century-study", "Mid-Century Study", "Study",
        "Walnut desk, hairpin legs, retro task lamps, cognac leather.", _img(7)),
    StyleTemplate("compact-nook", "Compact Nook", "Study",
        "Fold-out wall desks, vertical shelves, optimised corners.", _img(8)),
    StyleTemplate("zen-workspace", "Zen Workspace", "Study",
        "Clean lines, muted greens or beige, clutter-free surfaces.", _img(9)),
    StyleTemplate("premium-classic", "Premium Classic", "Study",
        "Mahogany desk, wainscoting, tufted leather guest chair.", _img(10)),
]

# ──────────────────────────────────────────────────────────────────────────────
# 7. Garden / Balcony
# ──────────────────────────────────────────────────────────────────────────────

_GARDEN = [
    StyleTemplate("urban-balcony-oasis", "Urban Balcony Oasis", "Balcony",
        "Vertical gardens, rattan seating, fairy string lights.", _img(11)),
    StyleTemplate("traditional-angan", "Traditional Angan", "Balcony",
        "Terracotta tiles, central Tulsi planter, carved Jhoola.", _img(12)),
    StyleTemplate("zen-courtyard", "Zen Courtyard", "Balcony",
        "Pebbles, water feature, bamboo screens, minimal seating.", _img(13)),
    StyleTemplate("tropical-patio", "Tropical Patio", "Balcony",
        "Palms, teak loungers, washable outdoor rugs.", _img(14)),
    StyleTemplate("modern-terrace", "Modern Terrace", "Balcony",
        "Frameless glass railings, metal dining set, BBQ counter.", _img(15)),
    StyleTemplate("boho-retreat", "Boho Retreat", "Balcony",
        "Macramé hammocks, floor cushions, overhead string lights.", _img(16)),
    StyleTemplate("manicured-lawn", "Manicured Lawn", "Garden",
        "Trimmed grass, stone path, wrought-iron bench.", _img(17)),
    StyleTemplate("desert-scape", "Desert Scape", "Garden",
        "Cacti, gravel beds, sand-toned hardscaping.", _img(18)),
    StyleTemplate("entertainers-deck", "Entertainer's Deck", "Garden",
        "Wooden decking, outdoor bar, weather-resistant sectional.", _img(19)),
    StyleTemplate("kitchen-garden", "Kitchen Garden", "Garden",
        "Raised herb beds, climber trellis, rustic stools.", _img(20)),
]

_ALL: tuple[StyleTemplate, ...] = (
    *_LIVING, *_BEDROOM, *_KITCHEN, *_BATHROOM, *_DINING, *_STUDY, *_GARDEN,
)

_BY_SLUG: dict[str, StyleTemplate] = {s.slug: s for s in _ALL}


# ──────────────────────────────────────────────────────────────────────────────
# Public helpers
# ──────────────────────────────────────────────────────────────────────────────

def all_styles() -> Iterable[StyleTemplate]:
    return _ALL


def get(slug: str) -> StyleTemplate | None:
    return _BY_SLUG.get(slug)


def categories() -> list[str]:
    """Stable display order, matching the editorial doc."""
    seen: list[str] = []
    for s in _ALL:
        if s.category not in seen:
            seen.append(s.category)
    return seen


def by_category(category: str) -> list[StyleTemplate]:
    return [s for s in _ALL if s.category == category]

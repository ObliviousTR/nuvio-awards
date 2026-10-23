"""Discover > Hidden Gems: curated MDBList lists served through AIOMetadata (hidden-gem rails removed elsewhere).

Each list was opened through the MDBList API and judged on its actual titles:
  164980 Underrated Comedies (Reddit)       - Tucker & Dale vs Evil, Hot Rod, Popstar, Palm Springs
  164919 Underrated Sci-Fi                  - Coherence, Primer, Moon, Vivarium, Upgrade
  198591 Hidden Gems & Binge-Worthy TV      - Detroiters, The Other Two, Shtisel, Pachinko
  148283 Hidden Gems (TV)                   - Fellow Travelers, Mystery Road, Maniac, Little America
228941 (Underrated & Cult Films) was dropped: MDBList no longer has it (404).
Rejected: the dynamic "Hidden Gems" movie lists (they are just top-rated: Shawshank, Dark Knight).
"""
GEMS = [  # (rail title, media, mdblist id)
    ("Underrated Comedies", "MOVIE", 164980),
    ("Underrated Sci-Fi", "MOVIE", 164919),
    ("Hidden Gem Series", "TV", 198591),
    ("Under-the-Radar Series", "TV", 148283),
    ("Anime Hidden Gems", "TV", 230335),  # our own static list: mdblist.com/lists/mr.psmst/anime-hidden-gems
]

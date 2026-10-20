"""Reality TV row: the 6 agreed folders (master list) with Kaptain's rail line-up mapped onto them.

Rails are native TMDB discover rails (TV). Keyword names are resolved to TMDB ids once (reality_ids.json, made by
the resolver in the nuvio-awards repo). Default rail: Reality genre (10764), English, from the US / UK / Australia,
no animation. Korean rails are the agreed exception (master list: US / UK / AU / KR).
Fields: kw = keyword names (OR), net = TMDB network ids, country = origin countries, lang = original language,
genres = TMDB TV genres (default 10764), sort = pop|top|new|votes, vc = minimum votes, since = first aired from year,
until = first aired up to year.
"""
ANGLO = "US|GB|AU"
EXCLUDE = ["wrestling", "professional wrestling", "wwe"]  # wrestling is tagged Reality on TMDB

FOLDERS = [
    ("Trending & New Reality", "Discover Reality TV", [
        ("Popular Reality Right Now", dict(sort="pop", vc=20, since=2023)),
        ("New Reality Releases", dict(sort="new", vc=3)),
        ("Biggest Reality Hits", dict(sort="votes", vc=50)),
        ("Top Rated Reality", dict(sort="top", vc=150)),
        ("Reality Competition Hits", dict(kw=["reality competition", "competition", "elimination"], sort="pop", vc=30)),
        ("Docusoaps & Social Experiments", dict(kw=["docusoap", "social experiment", "docuseries", "celebrity", "reality star"], sort="pop", vc=5)),
        ("Popular in the US", dict(country="US", sort="pop", vc=20)),
        ("Popular in the UK", dict(country="GB", sort="pop", vc=10)),
        ("Popular in Australia", dict(country="AU", sort="pop", vc=5)),
        ("Korean Reality", dict(country="KR", lang="ko", sort="pop", vc=5)),
    ]),
    ("Strategy, Mind Games & Survival", "High-Stakes Competition & Survival", [
        ("Island Survival & Outlast", dict(kw=["survival", "survival competition", "island", "wilderness", "stranded"], sort="votes", vc=10)),
        ("Strategy, Lock-Ins & Mind Games", dict(kw=["strategy", "deception", "manipulation", "betrayal", "alliance", "big brother", "confinement"], sort="votes", vc=10)),
        ("Global Race & Travel Challenges", dict(kw=["race", "travel competition", "around the world"], sort="votes", vc=10)),
        ("Extreme Jobs & Real Danger", dict(kw=["dangerous job", "occupation", "fishing", "gold mining", "trucking"], sort="votes", vc=10)),
        ("Physical Challenge Shows", dict(kw=["physical competition", "obstacle course", "athlete"], sort="votes", vc=10)),
        ("MTV Competition & Chaos", dict(net="33", kw=["competition", "reality competition"], sort="votes", vc=10)),
        ("Korean Survival & Mind Games", dict(country="KR", lang="ko", kw=["survival", "survival competition", "competition", "strategy"], sort="votes", vc=3)),
        ("New Competition Series", dict(kw=["reality competition", "competition", "survival competition"], sort="new", vc=3)),
    ]),
    ("Culinary & Cooking Battles", "Culinary Battles & Cooking Shows", [
        ("Restaurant & Chef Battles", dict(kw=["cooking competition", "chef", "restaurant", "culinary"], sort="votes", vc=10)),
        ("Baking Competitions", dict(kw=["baking", "baking competition", "cake", "pastry"], sort="votes", vc=5)),
        ("Food Network Favorites", dict(net="143", sort="votes", vc=5, genres=None)),
        ("Top Rated Culinary Shows", dict(kw=["cooking", "cooking competition", "chef", "baking", "food"], sort="top", vc=50)),
        ("Food & Travel Adventures", dict(kw=["food", "cuisine", "travel", "street food"], genres="10764|99", sort="votes", vc=20)),
        ("MasterChef Around the World", dict(kw=["masterchef", "cooking competition"], country="US|GB|AU", sort="votes", vc=5)),
        ("Korean Culinary Battles", dict(country="KR", lang="ko", kw=["cooking", "cooking competition", "chef", "food"], sort="votes", vc=2)),
        ("New Culinary Releases", dict(kw=["cooking", "cooking competition", "chef", "baking", "food"], sort="new", vc=2)),
    ]),
    ("British Panel, Quiz & Comedy Shows", "Game Shows, Talent & Trivia", [
        ("British Panel Shows", dict(country="GB", kw=["panel show", "panel game"], genres="35|10767|10764", sort="votes", vc=10)),
        ("Comedy Challenges & Taskmaster", dict(country="GB|AU|US", kw=["task", "comedian", "improvisation", "stand-up comedy"], genres="10764|10767", sort="votes", vc=10)),
        ("U&Dave & Channel 4 Entertainment", dict(net="388|26", genres="10764|10767", sort="votes", vc=10)),
        ("Quiz & Trivia", dict(kw=["quiz show", "quiz", "trivia"], genres="10764|10767|35", sort="votes", vc=5)),
        ("Popular Game Shows", dict(kw=["game show"], genres="10764|10767|35", sort="pop", vc=10)),
        ("Singing & Talent Competitions", dict(kw=["talent show", "singing competition", "talent competition", "singing"], sort="votes", vc=10)),
        ("Classic Game Shows", dict(kw=["game show", "quiz show"], genres="10764|10767|35", sort="votes", vc=5, until=1999)),
        ("New Game & Quiz Shows", dict(kw=["game show", "quiz show", "panel show"], genres="10764|10767|35", sort="new", vc=2)),
    ]),
    ("Dating, Social Experiment & Drama", "Juicy Drama, Dating & Relationship", [
        ("Blind Dating & Social Experiments", dict(kw=["dating", "blind date", "social experiment", "dating show"], sort="votes", vc=10)),
        ("Streaming Dating Sensations", dict(net="213|1024|453|2739|3353", kw=["dating", "dating show", "relationship"], sort="pop", vc=5)),
        ("Love Island & UK Dating", dict(country="GB|AU", kw=["dating", "dating show", "love"], sort="votes", vc=5)),
        ("Top Rated Dating Shows", dict(kw=["dating", "dating show", "blind date"], sort="top", vc=30)),
        ("High-Society & City Drama", dict(net="74|76|158", kw=["housewife", "socialite", "wealth", "rich", "high society", "celebrity", "drama"], sort="votes", vc=10)),
        ("Family & Relationship Docusoaps", dict(net="84|34|129", kw=["family", "marriage", "relationship", "wedding", "large family", "parenting"], sort="votes", vc=3)),
        ("Korean Dating Shows", dict(country="KR", lang="ko", kw=["dating", "dating show", "romance", "love"], sort="votes", vc=2)),
        ("New Dating Releases", dict(kw=["dating", "dating show", "blind date", "relationship"], sort="new", vc=2)),
    ]),
    ("Makeover, Motors & Craft Battles", "Real Estate, Home & Lifestyle Makeovers", [
        ("Cars, Motors & Garage Builds", dict(kw=["car", "automobile", "car restoration", "motorcycle", "garage"], sort="votes", vc=10, genres="10764|99")),
        ("Craft & Maker Battles", dict(kw=["craft", "blacksmith", "bladesmith", "glassblowing", "woodworking", "artisan", "pottery", "sewing", "art competition", "design competition", "maker"], genres="10764|99", sort="votes", vc=2)),
        ("Countryside & Farm Life", dict(kw=["farm", "farming", "countryside", "rural life", "ranch", "cowboy", "homestead", "country life"], genres="10764|99", sort="votes", vc=3)),
        ("Home Renovation & Transformation", dict(kw=["home renovation", "renovation", "home improvement", "interior design"], sort="votes", vc=10)),
        ("HGTV & Magnolia Favorites", dict(net="210|4519", sort="votes", vc=5)),
        ("Luxury Real Estate", dict(kw=["real estate", "luxury", "realtor"], sort="votes", vc=5)),
        ("Makeovers & Style Transformations", dict(kw=["makeover", "fashion", "style", "transformation"], sort="votes", vc=10)),
        ("New Lifestyle & Home Releases", dict(kw=["home renovation", "real estate", "makeover", "car restoration", "craft"], sort="new", vc=2)),
    ]),
]

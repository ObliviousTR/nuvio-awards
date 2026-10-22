"""Final step: row order (agreed with Ozzy, 2026-10-21) and, later, folder order inside each row.
usage: python3 apply_order.py in.json out.json
"""
import re, sys
from common import load, save

ROWS = ["Favourites", "Spotlight", "Discover", "Streaming Services", "Networks", "Genres", "Anime", "Moods & Vibes",
        "Universes & Franchises", "Film Collections", "Kids & Family", "Studios", "Iconic Actors", "Legendary Directors",
        "Awards & Festivals", "Based On", "By Decade", "International Cinema", "Reality TV", "Documentaries"]
FOLDERS = {  # row title -> folder titles in order (unlisted folders keep their place after the listed ones)
    "Favourites": ["My Simkl", "Doctor Who", "One Pace", "Live Sport"],
    "Spotlight": ["The Headliner", "The Visionary", "The Cultural Pulse", "The Saga", "The Powerhouse",
                  "The Prestige Darling", "Yerli Yıldız", "The Living Legend", "Retro Rewind"],
    "Discover": ["Trending Movies", "Trending Series", "New Movies", "New Series", "Box Office Champions",
                 "Certified Fresh & Must-See", "Hidden Gems", "Awards & Prestige", "All-Time Top Rated"],
    "Streaming Services": ["Netflix", "Apple TV+", "HBO Max", "Disney+", "Prime Video", "Exxen", "GAİN", "Crunchyroll",
                           "Mubi", "Discovery+", "Hulu", "Paramount+", "Shudder", "tabii"],
    "Networks": ["HBO", "FX", "AMC", "Showtime", "Sky Atlantic", "BBC", "ITV", "Channel 4", "U&Dave", "NBC", "ABC", "CBS",
                 "FOX", "USA Network", "Syfy", "Comedy Central", "Adult Swim", "Cartoon Network", "TV Tokyo",
                 "Fuji TV / MBS", "Discovery Channel", "National Geographic", "History Channel", "Food Network"],
    "Genres": ["Action & Adventure", "Sci-Fi & Fantasy", "Comedy", "Animation", "Drama", "Crime", "Horror",
               "Mystery & Thriller", "Romance & Rom-Com", "Stand-Up Comedy", "Superhero", "Martial Arts", "History & War",
               "Western"],
    "Anime": ["Seasonal & Currently Airing", "Shonen & High-Octane Action", "Seinen, Dark & Psychological",
              "Isekai, Magic & Fantasy Worlds", "Romance, Comedy & Slice of Life", "All-Time Top Rated Anime",
              "Anime Movies & Feature Films", "Anime Film Collections", "Studio Spotlight"],
    "Moods & Vibes": ["Feel-Good", "Cozy & Comforting", "Adrenaline Rush", "Epic & Sweeping", "Mind-Bending", "Slow Burn",
                      "Dark & Gritty", "Spooky & Creepy", "Tearjerkers", "80s & 90s Vibes"],
    "Universes & Franchises": ["Marvel Cinematic Universe", "DC Universe", "Batman & Gotham", "Spider-Verse",
                               "X-Men & Mutants", "Middle-earth", "Star Wars", "Wizarding World", "Dune", "Star Trek",
                               "007 James Bond", "Mission: Impossible", "The World of John Wick", "The Fast Saga", "Mad Max Saga",
                               "Indiana Jones", "The Matrix", "Alien & Predator", "Godzilla & Kong", "Jurassic Park",
                               "Planet of the Apes", "Terminator", "Transformers", "The Conjuring & Insidious"],
    "Film Collections": ["Action Collections", "Sci-Fi Collections", "Fantasy Collections", "Comedy Collections",
                         "Family & Animation Collections", "Drama Collections", "Crime Collections", "Horror Collections",
                         "Mystery Collections", "Thriller Collections", "War Collections"],
    "Kids & Family": ["Discover Family", "Family Movie Night", "Saturday Morning & Classic Cartoons",
                      "Disney & Pixar Magic", "DreamWorks & Illumination", "Studio Spotlight"],
    # by generation (legends -> today's greats -> new generation), best known first inside each
    "Iconic Actors": [
        "Al Pacino", "Robert De Niro", "Jack Nicholson", "Anthony Hopkins", "Meryl Streep", "Tom Hanks", "Harrison Ford",
        "Denzel Washington", "Daniel Day-Lewis", "Morgan Freeman", "Robin Williams", "Gary Oldman", "Samuel L. Jackson",
        "Jim Carrey", "Jackie Chan", "Frances McDormand",
        "Leonardo DiCaprio", "Brad Pitt", "Christian Bale", "Tom Cruise", "Keanu Reeves", "Joaquin Phoenix", "Matt Damon",
        "Robert Downey Jr.", "Cate Blanchett", "Nicole Kidman", "Kate Winslet", "Matthew McConaughey", "Hugh Jackman",
        "Charlize Theron", "Natalie Portman", "Scarlett Johansson", "Tom Hardy", "Ryan Gosling", "Jake Gyllenhaal",
        "Cillian Murphy", "Edward Norton", "Philip Seymour Hoffman", "Viola Davis", "Amy Adams", "Anne Hathaway",
        "Emma Stone", "Margot Robbie", "Bryan Cranston", "Willem Dafoe", "Christoph Waltz", "Mads Mikkelsen",
        "Javier Bardem", "Tilda Swinton", "Toni Collette", "Ethan Hawke", "Sam Rockwell", "Steve Carell", "Simon Pegg",
        "Song Kang-ho", "Oscar Isaac", "Pedro Pascal", "Robert Pattinson",
        "Florence Pugh", "Anya Taylor-Joy", "Timothée Chalamet", "Zendaya", "Tom Holland", "Austin Butler"],
    "Legendary Directors": [
        "Alfred Hitchcock", "Stanley Kubrick", "Akira Kurosawa", "Francis Ford Coppola", "Steven Spielberg",
        "Martin Scorsese", "Sergio Leone", "Billy Wilder", "David Lynch", "Hayao Miyazaki", "Ridley Scott", "James Cameron",
        "Clint Eastwood", "Peter Jackson", "Tim Burton", "Michael Mann", "George Miller",
        "Christopher Nolan", "Quentin Tarantino", "David Fincher", "Denis Villeneuve", "Paul Thomas Anderson",
        "Joel & Ethan Coen", "Wes Anderson", "Guillermo del Toro", "Bong Joon-ho", "Park Chan-wook", "Alfonso Cuarón",
        "Alejandro González Iñárritu", "Darren Aronofsky", "Kathryn Bigelow", "Edgar Wright", "Guy Ritchie",
        "Sofia Coppola",
        "Yorgos Lanthimos", "Alex Garland", "Jordan Peele", "Robert Eggers", "Ari Aster", "Greta Gerwig"],
    "Awards & Festivals": ["The Oscars", "Golden Globes & BAFTA", "Cannes, Venice & Sundance", "The Emmy Awards",
                           "Criterion Collection & Arthouse"],
    "International Cinema": ["Türkiye", "UK & Ireland", "Spain", "France", "Italy", "Germany", "Nordic Noir",
                             "Central & Eastern Europe", "South Korea", "Japan", "Greater China", "India",
                             "Southeast Asia", "Latin America", "Middle East"],
    "Reality TV": ["Trending & New Reality", "Strategy, Mind Games & Survival", "British Panel, Quiz & Comedy Shows",
                   "Culinary & Cooking Battles", "Dating, Social Experiment & Drama", "Makeover, Motors & Craft Battles"],
    "Documentaries": ["Trending & Award-Winning Docs", "True Crime & Serial Killers", "Investigative & Scandals",
                      "Nature, Wildlife & Earth", "Science, Tech & Cosmos", "History, War & Civilizations",
                      "Sports & Athletic Stories", "Music & Concert Documentaries"],
    # independents, then the animation studios, then Searchlight (Disney's specialty label) and the majors
    "Studios": ["A24", "Blumhouse Productions", "NEON", "Studio Ghibli", "Disney & Pixar Animation", "Searchlight Pictures",
                "Warner Bros. Pictures", "Universal Pictures", "Paramount Pictures", "20th Century Studios"],
}
DROP = {"Genres": ["Anime"]}  # the Anime row sits right under Genres

data = load(sys.argv[1])
missing = [c["title"] for c in data if c["title"] not in ROWS]
assert not missing, f"rows without a place: {missing}"
data.sort(key=lambda c: ROWS.index(c["title"]))
for c in data:
    c["folders"] = [f for f in c["folders"] if f["title"] not in DROP.get(c["title"], [])]
    want = FOLDERS.get(c["title"])
    if want:
        lost = [f["title"] for f in c["folders"] if f["title"] not in want]
        if lost:
            print(f"warning: {c['title']}: not in the agreed order, kept at the end: {lost}")
        c["folders"].sort(key=lambda f: want.index(f["title"]) if f["title"] in want else len(want))
# Nuvio mobile keeps each collection's home position per collection id (synced to the account) and never lets the
# user drag a pinned collection, so an import with old ids keeps the old order. The ids below were issued with the
# agreed row order (2026-10-21) and are now FIXED: Ozzy's hidden rows, custom row names and GIF switches hang on them.
# Change ID_TAG only on purpose, when the row order itself changes again (and tell him: those settings reset).
ID_TAG = "6d6158"
for c in data:
    c["id"] = f"row-{re.sub(r'[^a-z0-9]+', '-', c['title'].lower()).strip('-')}-{ID_TAG}"
save(data, sys.argv[2])
print("order:", " > ".join(c["title"] for c in data))

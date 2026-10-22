"""Universes & Franchises: the pictures that play behind each universe's mark are the franchise films' own
landscape key art (fanart.tv's most liked textless background, TMDB's best textless backdrop as fallback) instead of
random stills - one picture per film, the films that define the universe."""
KEYART = {
    "mcu": [("Avengers: Infinity War", 2018), ("Guardians of the Galaxy", 2014), ("Thor: Ragnarok", 2017),
            ("Captain America: The Winter Soldier", 2014), ("Doctor Strange", 2016)],
    "dc": [("Man of Steel", 2013), ("Aquaman", 2018), ("The Suicide Squad", 2021), ("Superman", 2025),
           ("Zack Snyder's Justice League", 2021)],
    "batman": [("Batman", 1989), ("Batman Begins", 2005), ("The Dark Knight Rises", 2012), ("The Batman", 2022),
               ("Batman Returns", 1992)],
    "spiderman": [("Spider-Man 2", 2004), ("Spider-Man: No Way Home", 2021), ("Spider-Man: Across the Spider-Verse", 2023),
                  ("The Amazing Spider-Man", 2012), ("Spider-Man: Homecoming", 2017)],
    "xmen": [("X-Men: Days of Future Past", 2014), ("X2", 2003), ("Deadpool & Wolverine", 2024), ("Deadpool", 2016),
             ("X-Men", 2000)],
    "middleearth": [("The Lord of the Rings: The Two Towers", 2002), ("The Lord of the Rings: The Fellowship of the Ring", 2001),
                    ("The Lord of the Rings: The Return of the King", 2003), ("The Hobbit: An Unexpected Journey", 2012),
                    ("The Hobbit: The Desolation of Smaug", 2013)],
    "starwars": [("The Empire Strikes Back", 1980), ("Rogue One: A Star Wars Story", 2016), ("Return of the Jedi", 1983),
                 ("Star Wars: The Force Awakens", 2015), ("Star Wars: Episode III - Revenge of the Sith", 2005)],
    "wizarding": [("Harry Potter and the Philosopher's Stone", 2001), ("Harry Potter and the Prisoner of Azkaban", 2004),
                  ("Harry Potter and the Deathly Hallows: Part 2", 2011), ("Harry Potter and the Goblet of Fire", 2005),
                  ("Fantastic Beasts and Where to Find Them", 2016)],
    "dune": [("Dune", 2021), ("Dune: Part Two", 2024), ("Dune", 1984)],
    "startrek": [("Star Trek", 2009), ("Star Trek Into Darkness", 2013), ("Star Trek II: The Wrath of Khan", 1982),
                 ("Star Trek Beyond", 2016), ("Star Trek: First Contact", 1996)],
    "mi": [("Mission: Impossible - Fallout", 2018), ("Mission: Impossible - Ghost Protocol", 2011),
           ("Mission: Impossible - Rogue Nation", 2015), ("Mission: Impossible", 1996),
           ("Mission: Impossible - Dead Reckoning Part One", 2023)],
    "johnwick": [("John Wick", 2014), ("John Wick: Chapter 2", 2017), ("John Wick: Chapter 3 - Parabellum", 2019),
                 ("John Wick: Chapter 4", 2023)],
    "fast": [("The Fast and the Furious", 2001), ("Fast Five", 2011), ("Furious 7", 2015), ("Fast & Furious 6", 2013),
             ("Fast X", 2023)],
    "madmax": [("Mad Max: Fury Road", 2015), ("Mad Max 2", 1981), ("Furiosa: A Mad Max Saga", 2024), ("Mad Max", 1979),
               ("Mad Max Beyond Thunderdome", 1985)],
    "indiana": [("Raiders of the Lost Ark", 1981), ("Indiana Jones and the Last Crusade", 1989),
                ("Indiana Jones and the Temple of Doom", 1984), ("Indiana Jones and the Dial of Destiny", 2023),
                ("Indiana Jones and the Kingdom of the Crystal Skull", 2008)],
    "matrix": [("The Matrix", 1999), ("The Matrix Reloaded", 2003), ("The Matrix Revolutions", 2003),
               ("The Matrix Resurrections", 2021)],
    "alienpredator": [("Aliens", 1986), ("Predator", 1987), ("Alien: Romulus", 2024), ("Prey", 2022), ("Prometheus", 2012)],
    "godzillakong": [("Godzilla vs. Kong", 2021), ("Godzilla", 2014), ("Kong: Skull Island", 2017),
                     ("Godzilla: King of the Monsters", 2019), ("Godzilla x Kong: The New Empire", 2024)],
    "jurassic": [("Jurassic Park", 1993), ("Jurassic World", 2015), ("The Lost World: Jurassic Park", 1997),
                 ("Jurassic World: Fallen Kingdom", 2018), ("Jurassic World Rebirth", 2025)],
    "apes": [("Planet of the Apes", 1968), ("War for the Planet of the Apes", 2017), ("Dawn of the Planet of the Apes", 2014),
             ("Rise of the Planet of the Apes", 2011), ("Kingdom of the Planet of the Apes", 2024)],
    "terminator": [("The Terminator", 1984), ("Terminator 2: Judgment Day", 1991), ("Terminator Salvation", 2009),
                   ("Terminator 3: Rise of the Machines", 2003), ("Terminator: Dark Fate", 2019)],
    "transformers": [("Transformers", 2007), ("Transformers: Dark of the Moon", 2011), ("Bumblebee", 2018),
                     ("Transformers: Rise of the Beasts", 2023), ("Transformers: Revenge of the Fallen", 2009)],
    "conjuring": [("The Conjuring", 2013), ("The Conjuring 2", 2016), ("Annabelle", 2014), ("The Nun", 2018),
                  ("Insidious", 2010)],
}
# (uid, film title) -> which fanart background when the most liked one isn't the best picture
PICK = {}


def paths(uid):
    import genre_art as g
    out = []
    for name, year in KEYART[uid]:
        tid, _ = g.find_movie(name, year)
        if not tid:
            continue
        fa = g.fanart_backgrounds(tid)
        p = fa[min(PICK.get((uid, name), 0), len(fa) - 1)] if fa else g.textless_backdrop("movie", tid)
        if p:
            out.append(p)
    return out

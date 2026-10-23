"""Universes & Franchises: the pictures that play behind each universe's mark are the franchise films' own
landscape key art (fanart.tv's most liked textless background, TMDB's best textless backdrop as fallback) instead of
random stills - four pictures per universe, one per film, the films that define it."""
KEYART = {
    'mcu': [('Avengers: Infinity War', 2018), ('Guardians of the Galaxy', 2014), ('Thor: Ragnarok', 2017), ('Captain America: The Winter Soldier', 2014)],
    'dc': [('Man of Steel', 2013), ('Aquaman', 2018), ('The Suicide Squad', 2021), ('Superman', 2025)],
    'batman': [('Batman', 1989), ('Batman Begins', 2005), ('The Dark Knight Rises', 2012), ('The Batman', 2022)],
    'spiderman': [('Spider-Man 2', 2004), ('Spider-Man: No Way Home', 2021), ('Spider-Man: Across the Spider-Verse', 2023), ('The Amazing Spider-Man', 2012)],
    'xmen': [('X-Men: Days of Future Past', 2014), ('X2', 2003), ('Deadpool & Wolverine', 2024), ('Deadpool', 2016)],
    'middleearth': [('The Lord of the Rings: The Two Towers', 2002), ('The Lord of the Rings: The Fellowship of the Ring', 2001), ('The Lord of the Rings: The Return of the King', 2003), ('The Hobbit: An Unexpected Journey', 2012)],
    'starwars': [('The Empire Strikes Back', 1980), ('Rogue One: A Star Wars Story', 2016), ('Return of the Jedi', 1983), ('Star Wars: The Force Awakens', 2015)],
    'wizarding': [("Harry Potter and the Philosopher's Stone", 2001), ('Harry Potter and the Prisoner of Azkaban', 2004), ('Harry Potter and the Deathly Hallows: Part 2', 2011), ('Harry Potter and the Goblet of Fire', 2005)],
    'dune': [('Dune', 2021), ('Dune: Part Two', 2024), ('Dune', 1984), ('Dune: Part Two', 2024, 2)],
    'startrek': [('Star Trek', 2009), ('Star Trek Into Darkness', 2013), ('Star Trek II: The Wrath of Khan', 1982), ('Star Trek Beyond', 2016)],
    'mi': [('Mission: Impossible - Fallout', 2018), ('Mission: Impossible - Ghost Protocol', 2011), ('Mission: Impossible - Rogue Nation', 2015), ('Mission: Impossible', 1996)],
    'johnwick': [('John Wick', 2014), ('John Wick: Chapter 2', 2017), ('John Wick: Chapter 3 - Parabellum', 2019), ('John Wick: Chapter 4', 2023)],
    'fast': [('The Fast and the Furious', 2001), ('Fast Five', 2011), ('Furious 7', 2015), ('Fast & Furious 6', 2013)],
    'madmax': [('Mad Max: Fury Road', 2015), ('Mad Max 2', 1981), ('Furiosa: A Mad Max Saga', 2024), ('Mad Max', 1979)],
    'indiana': [('Raiders of the Lost Ark', 1981), ('Indiana Jones and the Last Crusade', 1989), ('Indiana Jones and the Temple of Doom', 1984), ('Indiana Jones and the Dial of Destiny', 2023)],
    'matrix': [('The Matrix', 1999), ('The Matrix Reloaded', 2003), ('The Matrix Revolutions', 2003), ('The Matrix Resurrections', 2021)],
    'alienpredator': [('Aliens', 1986), ('Predator', 1987), ('Alien: Romulus', 2024), ('Prey', 2022)],
    'godzillakong': [('Godzilla vs. Kong', 2021), ('Godzilla', 2014), ('Kong: Skull Island', 2017), ('Godzilla: King of the Monsters', 2019)],
    'jurassic': [('Jurassic Park', 1993), ('Jurassic World', 2015), ('The Lost World: Jurassic Park', 1997), ('Jurassic World: Fallen Kingdom', 2018)],
    'apes': [('Planet of the Apes', 1968), ('War for the Planet of the Apes', 2017), ('Dawn of the Planet of the Apes', 2014), ('Rise of the Planet of the Apes', 2011)],
    'terminator': [('The Terminator', 1984), ('Terminator 2: Judgment Day', 1991), ('Terminator Salvation', 2009), ('Terminator 3: Rise of the Machines', 2003)],
    'transformers': [('Transformers', 2007), ('Transformers: Dark of the Moon', 2011), ('Bumblebee', 2018), ('Transformers: Rise of the Beasts', 2023)],
    'bond': [('Goldfinger', 1964), ('GoldenEye', 1995), ('Casino Royale', 2006), ('Skyfall', 2012)],
    'conjuring': [('The Conjuring', 2013), ('The Conjuring 2', 2016), ('Annabelle', 2014), ('The Nun', 2018)],
}
# (uid, film title) -> which fanart background when the most liked one isn't the best picture
PICK = {
    ('alienpredator', 'Aliens'): 1,
    ('alienpredator', 'Alien: Romulus'): 3,
    ('alienpredator', 'Prey'): 3,
    ('alienpredator', 'Prometheus'): 2,
    ('apes', 'War for the Planet of the Apes'): 2,
    ('apes', 'Kingdom of the Planet of the Apes'): 2,
    ('batman', 'Batman'): 3,
    ('batman', 'Batman Begins'): 2,
    ('batman', 'The Dark Knight Rises'): 1,
    ('batman', 'The Batman'): 1,
    ('batman', 'Batman Returns'): 4,
    ('conjuring', 'Annabelle'): 1,
    ('conjuring', 'The Nun'): 2,
    ('dc', 'Aquaman'): 1,
    ('dc', 'The Suicide Squad'): 1,
    ('dc', 'Superman'): 1,
    ('dc', "Zack Snyder's Justice League"): 2,
    ('dune', 'Dune'): 2,
    ('dune', 'Dune'): 1,
    ('fast', 'The Fast and the Furious'): 1,
    ('fast', 'Fast Five'): 4,
    ('godzillakong', 'Godzilla vs. Kong'): 2,
    ('godzillakong', 'Godzilla'): 2,
    ('godzillakong', 'Godzilla x Kong: The New Empire'): 1,
    ('indiana', 'Indiana Jones and the Last Crusade'): 1,
    ('indiana', 'Indiana Jones and the Temple of Doom'): 1,
    ('indiana', 'Indiana Jones and the Dial of Destiny'): 2,
    ('indiana', 'Indiana Jones and the Kingdom of the Crystal Skull'): 1,
    ('jurassic', 'The Lost World: Jurassic Park'): 2,
    ('jurassic', 'Jurassic World Rebirth'): 3,
    ('matrix', 'The Matrix'): 2,
    ('matrix', 'The Matrix Reloaded'): 4,
    ('matrix', 'The Matrix Revolutions'): 2,
    ('matrix', 'The Matrix Resurrections'): 2,
    ('mcu', 'Captain America: The Winter Soldier'): 2,
    ('mcu', 'Doctor Strange'): 2,
    ('mi', 'Mission: Impossible - Fallout'): 4,
    ('mi', 'Mission: Impossible - Ghost Protocol'): 2,
    ('mi', 'Mission: Impossible - Rogue Nation'): 2,
    ('mi', 'Mission: Impossible'): 3,
    ('middleearth', 'The Lord of the Rings: The Two Towers'): 1,
    ('middleearth', 'The Lord of the Rings: The Fellowship of the Ring'): 1,
    ('middleearth', 'The Lord of the Rings: The Return of the King'): 3,
    ('middleearth', 'The Hobbit: The Desolation of Smaug'): 1,
    ('spiderman', 'Spider-Man 2'): 4,
    ('spiderman', 'Spider-Man: Across the Spider-Verse'): 4,
    ('spiderman', 'Spider-Man: Homecoming'): 2,
    ('startrek', 'Star Trek'): 2,
    ('startrek', 'Star Trek II: The Wrath of Khan'): 2,
    ('startrek', 'Star Trek: First Contact'): 4,
    ('starwars', 'The Empire Strikes Back'): 1,
    ('starwars', 'Rogue One: A Star Wars Story'): 3,
    ('terminator', 'Terminator 3: Rise of the Machines'): 1,
    ('terminator', 'Terminator: Dark Fate'): 4,
    ('transformers', 'Bumblebee'): 1,
    ('transformers', 'Transformers: Revenge of the Fallen'): 2,
    ('wizarding', "Harry Potter and the Philosopher's Stone"): 1,
    ('wizarding', 'Harry Potter and the Deathly Hallows: Part 2'): 4,
    ('xmen', 'Deadpool'): 1,
    ('xmen', 'X-Men'): 1,
}


def paths(uid):
    return [p for p, _, _ in entries(uid)]


def entries(uid):
    """(picture, film title, year) for each key-art film found."""
    import genre_art as g
    out = []
    for entry in KEYART[uid]:   # (title, year) or (title, year, which fanart background)
        name, year = entry[0], entry[1]
        tid, _ = g.find_movie(name, year)
        if not tid:
            continue
        fa = g.fanart_backgrounds(tid)
        i = entry[2] if len(entry) > 2 else PICK.get((uid, name), 0)
        p = fa[min(i, len(fa) - 1)] if fa else g.textless_backdrop("movie", tid)
        if p:
            out.append((p, name, year))
    return out

"""The car inventory: a synthetic SQLite database and the queries on it.

The original project shipped a database with dates up to 31 December 2025, so
it stopped working after that. The demo now generates its own fictional fleet
when the server starts, with availability dates from today onwards. The random
generator is seeded, so the same day always produces the same fleet.

Queries are built here with SQL parameters, never by the language model.
"""

import random
import sqlite3
from dataclasses import dataclass
from datetime import date, timedelta

LOCATIONS = ["Madrid", "Barcelona", "Sevilla", "Valencia", "Malaga", "Tarifa", "Bilbao"]
COLORS = ["Black", "White", "Red", "Blue", "Silver", "Gray", "Green", "Purple"]

# Make → (models, price range per day in EUR, oldest year)
CATALOGUE: dict[str, tuple[list[str], tuple[int, int], int]] = {
    "Tesla": (["Model 3", "Model Y", "Model S"], (80, 150), 2018),
    "BMW": (["i3", "iX3", "Series 1", "Series 3", "X1"], (70, 150), 2014),
    "Audi": (["A3", "A4", "Q4 e-Tron", "Q5"], (70, 150), 2014),
    "Porsche": (["911 Carrera", "Taycan", "Macan"], (200, 500), 2016),
    "Ferrari": (["Roma", "Portofino"], (300, 500), 2018),
    "Toyota": (["Yaris", "Corolla", "RAV4", "C-HR"], (30, 80), 2008),
    "Ford": (["Fiesta", "Focus", "Puma", "Kuga"], (30, 70), 2008),
    "Fiat": (["500", "Panda", "Tipo"], (25, 60), 2008),
    "Renault": (["Clio", "Captur", "Megane"], (30, 70), 2010),
    "Seat": (["Ibiza", "Leon", "Arona", "Ateca"], (30, 70), 2010),
    "Skoda": (["Fabia", "Octavia", "Karoq"], (30, 70), 2010),
    "Peugeot": (["208", "2008", "308", "3008"], (30, 75), 2010),
}

SCHEMA = """
CREATE TABLE cars (
    id INTEGER PRIMARY KEY,
    make TEXT NOT NULL,
    model TEXT NOT NULL,
    year INTEGER NOT NULL,
    price_per_day REAL NOT NULL,
    date_available DATE NOT NULL,
    location TEXT NOT NULL,
    color TEXT NOT NULL
)
"""


@dataclass(frozen=True)
class Car:
    id: int
    make: str
    model: str
    year: int
    price_per_day: float
    date_available: date
    location: str
    color: str

    def describe(self) -> str:
        return (
            f"#{self.id} {self.make} {self.model} ({self.year}), {self.color}, "
            f"€{self.price_per_day:.2f}/day, available {self.date_available.isoformat()} in {self.location}"
        )


def create_inventory(today: date, days_ahead: int, cars_per_location_per_week: int = 40) -> sqlite3.Connection:
    """Builds an in-memory database of fictional cars available from `today`."""
    generator = random.Random(today.toordinal())  # same fleet for the whole day
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.execute(SCHEMA)
    rows = []
    for location in LOCATIONS:
        for _ in range(cars_per_location_per_week * max(1, days_ahead // 7)):
            make = generator.choice(list(CATALOGUE))
            models, (low, high), oldest = CATALOGUE[make]
            rows.append(
                (
                    make,
                    generator.choice(models),
                    generator.randint(oldest, today.year),
                    round(generator.uniform(low, high), 2),
                    (today + timedelta(days=generator.randint(0, days_ahead))).isoformat(),
                    location,
                    generator.choice(COLORS),
                )
            )
    connection.executemany(
        "INSERT INTO cars (make, model, year, price_per_day, date_available, location, color) VALUES (?, ?, ?, ?, ?, ?, ?)",
        rows,
    )
    connection.commit()
    return connection


def search_cars(
    connection: sqlite3.Connection,
    location: str,
    start: date,
    end: date,
    max_price: float | None = None,
    limit: int = 15,
) -> list[Car]:
    """Cars available in `location` on any day between `start` and `end`, cheapest first."""
    query = "SELECT * FROM cars WHERE location = ? AND date_available BETWEEN ? AND ?"
    params: list[object] = [location, start.isoformat(), end.isoformat()]
    if max_price is not None:
        query += " AND price_per_day <= ?"
        params.append(max_price)
    query += " ORDER BY price_per_day LIMIT ?"
    params.append(limit)
    rows = connection.execute(query, params).fetchall()
    return [Car(r[0], r[1], r[2], r[3], r[4], date.fromisoformat(r[5]), r[6], r[7]) for r in rows]


def match_location(text: str | None) -> str | None:
    """Case- and accent-insensitive match against the known locations."""
    if not text:
        return None
    normalized = text.strip().lower().replace("á", "a").replace("é", "e").replace("í", "i")
    aliases = {"seville": "sevilla", "malaga": "malaga", "málaga": "malaga"}
    normalized = aliases.get(normalized, normalized)
    for location in LOCATIONS:
        if location.lower() == normalized:
            return location
    return None

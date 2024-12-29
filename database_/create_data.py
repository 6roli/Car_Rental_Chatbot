import sqlite3
from datetime import date, timedelta
import random

# Connect to SQLite database
conn = sqlite3.connect('cars_schema.db')
cursor = conn.cursor()

# Create the 'cars' table
cursor.execute("""
CREATE TABLE IF NOT EXISTS cars (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    make TEXT NOT NULL,
    model TEXT NOT NULL,
    year INTEGER NOT NULL,
    price_per_day REAL NOT NULL,
    date_available DATE NOT NULL,
    location TEXT NOT NULL,
    color TEXT NOT NULL
)
""")

# Car makes and models, adding more economic cars
cars_data = {
    "Volkswagen": ["California", "Golf", "Passat", "Polo", "Tiguan"],
    "Lamborghini": ["Huracan", "Aventador", "Urus"],
    "Ferrari": ["488 GTB", "Roma", "Portofino", "F8 Tributo", "SF90 Stradale"],
    "Porsche": ["911 Convertible", "Cayman", "Taycan", "Panamera", "Macan"],
    "Tesla": ["Model S", "Model 3", "Model X", "Model Y", "Roadster"],
    "Nissan": ["Leaf", "Rogue", "Qashqai", "Altima", "GT-R"],
    "Hyundai": ["Kona Electric", "Ioniq", "Elantra", "Santa Fe", "i20", "Accent"],
    "Kia": ["EV6", "Soul EV", "Sportage", "Sorento", "Rio", "Picanto"],
    "BMW": ["i3", "i8", "X5", "3 Series", "Z4"],
    "Audi": ["e-Tron", "Q4 e-Tron", "A4", "Q5", "TT"],
    # Additional economic and budget-friendly cars
    "Toyota": ["Corolla", "Yaris", "Camry", "Highlander", "RAV4"],
    "Ford": ["Fiesta", "Focus", "Mustang", "Explorer", "F-150"],
    "Honda": ["Civic", "Accord", "Fit", "Pilot", "CR-V"],
    "Chevrolet": ["Spark", "Malibu", "Cruze", "Impala", "Equinox"],
    "Fiat": ["500", "Panda", "Tipo", "Punto", "Doblo"],
    "Renault": ["Clio", "Twingo", "Captur", "Megane", "Kadjar"],
    "Skoda": ["Fabia", "Octavia", "Superb", "Karoq", "Kodiaq"],
    "Peugeot": ["208", "308", "2008", "3008", "508"]
}

# Updated Locations in Spain, including Tarifa and Bilbao
locations = ["Madrid", "Barcelona", "Sevilla", "Valencia", "Malaga", "Tarifa", "Bilbao"]

# Colors (including the new color 'Purple' instead of Pink)
colors = ["Black", "White", "Red", "Blue", "Silver", "Gray", "Green", "Purple"]

# Helper function to get all months between two dates
def get_months(start_date, end_date):
    months = []
    current = start_date.replace(day=1)
    while current <= end_date:
        months.append(current)
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)
    return months

# Generate rows for each month with a max of 30 rows per location per month
start_date = date(2024, 12, 1)
end_date = date(2025, 12, 31)
months = get_months(start_date, end_date)

# Track the count of rows for each location per month
location_month_count = {location: {month: 0 for month in months} for location in locations}

# Electric cars for realistic years
electric_cars = {"Tesla", "BMW", "Audi", "Hyundai", "Kia", "Nissan", "Porsche"}

# Price ranges for different types of cars
price_ranges = {
    "electric": (80, 150),  # Electric cars (higher end)
    "luxury": (200, 500),   # Luxury cars (e.g., Ferrari, Lamborghini)
    "regular": (30, 80),    # Regular cars (e.g., Toyota, Ford, Fiat)
}

for month_start in months:
    # Calculate the last day of the month
    if month_start.month == 12:
        next_month_start = month_start.replace(year=month_start.year + 1, month=1)
    else:
        next_month_start = month_start.replace(month=month_start.month + 1)
    month_end = next_month_start - timedelta(days=1)

    # Generate up to 30 random rows for this month for each location
    for location in locations:
        # Only insert up to 30 rows for this location in the month
        while location_month_count[location][month_start] < 30:
            make = random.choice(list(cars_data.keys()))
            model = random.choice(cars_data[make])
            
            # Set year based on the type of car
            if make in electric_cars:
                year = random.randint(2010, 2024)  # Electric cars: newer years
                price_per_day = round(random.uniform(price_ranges["electric"][0], price_ranges["electric"][1]), 2)
            elif make in ["Lamborghini", "Ferrari", "Porsche"]:
                year = random.randint(2015, 2024)  # Luxury cars: recent years
                price_per_day = round(random.uniform(price_ranges["luxury"][0], price_ranges["luxury"][1]), 2)
            else:
                year = random.randint(1995, 2024)  # Regular cars: wider range of years
                price_per_day = round(random.uniform(price_ranges["regular"][0], price_ranges["regular"][1]), 2)

            color = random.choice(colors)

            # Random date within the month
            date_available = month_start + timedelta(days=random.randint(0, (month_end - month_start).days))

            cursor.execute("""
                INSERT INTO cars (make, model, year, price_per_day, date_available, location, color)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (make, model, year, price_per_day, date_available.strftime('%Y-%m-%d'), location, color))

            location_month_count[location][month_start] += 1  # Increment the count for this location

# Commit changes and close the connection
conn.commit()
conn.close()

print("Database created with price adjustments and added economic cars.")

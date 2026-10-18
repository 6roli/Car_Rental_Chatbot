from datetime import date, timedelta

from car_rental.agents import SearchCriteria, validate_criteria
from car_rental.inventory import LOCATIONS, create_inventory, match_location, search_cars

TODAY = date(2026, 10, 18)
LAST_DAY = TODAY + timedelta(days=180)


def test_inventory_covers_every_city_from_today():
    connection = create_inventory(TODAY, days_ahead=180)
    first, last = connection.execute("SELECT min(date_available), max(date_available) FROM cars").fetchone()
    assert date.fromisoformat(first) >= TODAY
    assert date.fromisoformat(last) <= LAST_DAY
    cities = {row[0] for row in connection.execute("SELECT DISTINCT location FROM cars")}
    assert cities == set(LOCATIONS)


def test_inventory_is_the_same_all_day():
    a = create_inventory(TODAY, 60).execute("SELECT * FROM cars").fetchall()
    b = create_inventory(TODAY, 60).execute("SELECT * FROM cars").fetchall()
    assert a == b


def test_search_filters_city_dates_and_price_cheapest_first():
    connection = create_inventory(TODAY, 180)
    cars = search_cars(connection, "Madrid", TODAY, TODAY + timedelta(days=30), max_price=60)
    assert cars, "expected some cars in a month"
    assert all(car.location == "Madrid" and car.price_per_day <= 60 for car in cars)
    assert all(TODAY <= car.date_available <= TODAY + timedelta(days=30) for car in cars)
    prices = [car.price_per_day for car in cars]
    assert prices == sorted(prices)


def test_search_is_safe_against_sql_in_the_city_name():
    connection = create_inventory(TODAY, 30)
    assert search_cars(connection, "Madrid' OR '1'='1", TODAY, LAST_DAY) == []


def test_match_location_is_forgiving():
    assert match_location("sevilla") == "Sevilla"
    assert match_location("Seville") == "Sevilla"
    assert match_location("Málaga") == "Malaga"
    assert match_location("Paris") is None
    assert match_location(None) is None


def test_validation_explains_every_problem():
    ok = SearchCriteria(location="Bilbao", start_date=TODAY, end_date=TODAY + timedelta(days=2))
    assert validate_criteria(ok, TODAY, LAST_DAY) == []

    missing = validate_criteria(SearchCriteria(), TODAY, LAST_DAY)
    assert len(missing) == 2  # city and dates

    unknown = validate_criteria(SearchCriteria(location="Paris", start_date=TODAY), TODAY, LAST_DAY)
    assert any("Paris" in problem for problem in unknown)

    past = validate_criteria(SearchCriteria(location="Madrid", start_date=TODAY - timedelta(days=1)), TODAY, LAST_DAY)
    assert any("past" in problem for problem in past)

    too_far = validate_criteria(SearchCriteria(location="Madrid", start_date=LAST_DAY + timedelta(days=1)), TODAY, LAST_DAY)
    assert any("up to" in problem for problem in too_far)

    inverted = SearchCriteria(location="Madrid", start_date=TODAY + timedelta(days=5), end_date=TODAY + timedelta(days=1))
    assert any("before" in problem for problem in validate_criteria(inverted, TODAY, LAST_DAY))


def test_a_weekend_in_any_city_has_enough_choice():
    connection = create_inventory(TODAY, 180)
    friday = TODAY + timedelta(days=(4 - TODAY.weekday()) % 7)
    for city in LOCATIONS:
        assert len(search_cars(connection, city, friday, friday + timedelta(days=2))) >= 5, city


def test_search_summary_repeats_what_was_understood():
    from car_rental.assistant import describe_search

    criteria = SearchCriteria(location="barcelona", start_date=date(2026, 10, 23), end_date=date(2026, 10, 25), max_price_per_day=60)
    assert describe_search(criteria) == "Searching Barcelona, Fri 23 Oct 2026 to Sun 25 Oct 2026, up to €60/day"

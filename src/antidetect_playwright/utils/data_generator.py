"""Data generators for registration tasks."""

import random
import string
import secrets
from dataclasses import dataclass
from typing import Iterator


# Common first/last names for generation
FIRST_NAMES = [
    "James",
    "John",
    "Robert",
    "Michael",
    "William",
    "David",
    "Richard",
    "Joseph",
    "Thomas",
    "Charles",
    "Mary",
    "Patricia",
    "Jennifer",
    "Linda",
    "Elizabeth",
    "Barbara",
    "Susan",
    "Jessica",
    "Sarah",
    "Karen",
    "Alex",
    "Jordan",
    "Taylor",
    "Morgan",
    "Casey",
    "Riley",
    "Avery",
    "Quinn",
    "Peyton",
    "Cameron",
]

LAST_NAMES = [
    "Smith",
    "Johnson",
    "Williams",
    "Brown",
    "Jones",
    "Garcia",
    "Miller",
    "Davis",
    "Rodriguez",
    "Martinez",
    "Anderson",
    "Taylor",
    "Thomas",
    "Moore",
    "Jackson",
    "Martin",
    "Lee",
    "Thompson",
    "White",
    "Harris",
    "Clark",
    "Lewis",
    "Walker",
]

EMAIL_DOMAINS = [
    "gmail.com",
    "yahoo.com",
    "outlook.com",
    "hotmail.com",
    "protonmail.com",
    "icloud.com",
    "mail.com",
    "aol.com",
]


@dataclass
class GeneratedUser:
    """Generated user data for registration."""

    first_name: str
    last_name: str
    email: str
    username: str
    password: str
    birth_year: int
    birth_month: int
    birth_day: int
    phone: str | None = None

    def to_dict(self) -> dict:
        return {
            "first_name": self.first_name,
            "last_name": self.last_name,
            "email": self.email,
            "username": self.username,
            "password": self.password,
            "birth_year": self.birth_year,
            "birth_month": self.birth_month,
            "birth_day": self.birth_day,
            "phone": self.phone,
        }


def generate_password(
    length: int = 16,
    include_special: bool = True,
) -> str:
    """Generate secure random password."""
    chars = string.ascii_letters + string.digits
    if include_special:
        chars += "!@#$%^&*"

    # Ensure at least one of each type
    password = [
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.digits),
    ]
    if include_special:
        password.append(secrets.choice("!@#$%^&*"))

    remaining = length - len(password)
    password.extend(secrets.choice(chars) for _ in range(remaining))

    random.shuffle(password)
    return "".join(password)


def generate_username(first_name: str, last_name: str) -> str:
    """Generate username from name."""
    patterns = [
        lambda f, l: f"{f.lower()}{l.lower()}{random.randint(1, 999)}",
        lambda f, l: f"{f.lower()}.{l.lower()}{random.randint(1, 99)}",
        lambda f, l: f"{f.lower()}_{l.lower()}",
        lambda f, l: f"{f[0].lower()}{l.lower()}{random.randint(10, 9999)}",
        lambda f, l: f"{l.lower()}{f.lower()[:2]}{random.randint(1, 999)}",
    ]
    return random.choice(patterns)(first_name, last_name)


def generate_email(
    username: str,
    domain: str | None = None,
    plus_suffix: bool = False,
) -> str:
    """Generate email address."""
    domain = domain or random.choice(EMAIL_DOMAINS)

    if plus_suffix:
        suffix = secrets.token_hex(4)
        return f"{username}+{suffix}@{domain}"

    return f"{username}@{domain}"


def generate_phone(country_code: str = "+1") -> str:
    """Generate random phone number."""
    # US format
    area_code = random.randint(200, 999)
    exchange = random.randint(200, 999)
    subscriber = random.randint(1000, 9999)
    return f"{country_code}{area_code}{exchange}{subscriber}"


def generate_birth_date(
    min_age: int = 18,
    max_age: int = 50,
) -> tuple[int, int, int]:
    """Generate birth date (year, month, day)."""
    import datetime

    today = datetime.date.today()
    age = random.randint(min_age, max_age)
    birth_year = today.year - age
    birth_month = random.randint(1, 12)

    # Days per month
    days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    max_day = days_in_month[birth_month - 1]
    birth_day = random.randint(1, max_day)

    return birth_year, birth_month, birth_day


def generate_user(
    email_domain: str | None = None,
    include_phone: bool = False,
) -> GeneratedUser:
    """Generate complete user data."""
    first_name = random.choice(FIRST_NAMES)
    last_name = random.choice(LAST_NAMES)
    username = generate_username(first_name, last_name)
    email = generate_email(username, email_domain)
    password = generate_password()
    birth_year, birth_month, birth_day = generate_birth_date()

    phone = generate_phone() if include_phone else None

    return GeneratedUser(
        first_name=first_name,
        last_name=last_name,
        email=email,
        username=username,
        password=password,
        birth_year=birth_year,
        birth_month=birth_month,
        birth_day=birth_day,
        phone=phone,
    )


def generate_users(
    count: int,
    email_domain: str | None = None,
    include_phone: bool = False,
) -> list[GeneratedUser]:
    """Generate multiple users."""
    return [generate_user(email_domain, include_phone) for _ in range(count)]


def generate_users_iterator(
    count: int,
    email_domain: str | None = None,
    include_phone: bool = False,
) -> Iterator[GeneratedUser]:
    """Generate users lazily."""
    for _ in range(count):
        yield generate_user(email_domain, include_phone)

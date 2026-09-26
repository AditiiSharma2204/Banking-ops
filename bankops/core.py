"""Money, validation, security and loan maths - no database or UI code.

All money is integer paise (1 rupee = 100 paise), as in banking_ops.c.
"""

import hashlib
import hmac
import math
import re
import secrets

MIN_BALANCE = 1_000_00            # Rs 1,000 must stay in the account
MAX_AMOUNT = 10_00_00_000_00      # Rs 10 crore per operation
RTGS_MIN = 2_00_000_00            # Rs 2 lakh
IMPS_MAX = 5_00_000_00            # Rs 5 lakh
MAX_ATTEMPTS = 3                  # wrong passwords / PINs before a lockout
LOCK_MINUTES = 5

TRANSFER_MODES = {
    "IMPS": "Instant, up to ₹5,00,000",
    "NEFT": "Within 30 minutes, any amount",
    "RTGS": "Real time, minimum ₹2,00,000",
}

# name -> tiers of (upper limit in paise or None, years, annual rate %)
LOANS = {
    "Home Loan": [(20_00_000_00, 4, 8.6), (60_00_000_00, 6, 9.1), (None, 8, 9.5)],
    "Car Loan": [(5_00_000_00, 3, 9.0), (15_00_000_00, 5, 9.5), (None, 7, 10.0)],
    "Personal Loan": [(2_00_000_00, 2, 11.0), (10_00_000_00, 3, 12.0), (None, 5, 13.0)],
}


class BankError(Exception):
    """A user-facing error, e.g. insufficient funds or a wrong PIN."""


# ----------------------------------------------------------------------
# Money
# ----------------------------------------------------------------------


def to_paise(rupees):
    """Rupees (int, float or str like '1500.50') to integer paise."""
    text = str(rupees).strip().replace(",", "")
    if not re.fullmatch(r"\d+(\.\d{1,2})?", text):
        raise BankError("Enter an amount like 1500 or 1500.50.")
    whole, _, frac = text.partition(".")
    return int(whole) * 100 + int((frac + "00")[:2])


def money(paise, decimals=True):
    """Indian digit grouping: 123456789 paise -> '₹12,34,567.89'."""
    sign = "-" if paise < 0 else ""
    rupees, p = divmod(abs(int(paise)), 100)
    digits = str(rupees)
    head, tail = digits[:-3], digits[-3:]
    groups = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    if head:
        groups.insert(0, head)
    text = ",".join(groups + [tail])
    return f"{sign}₹{text}.{p:02d}" if decimals else f"{sign}₹{text}"


def check_amount(paise):
    if paise <= 0:
        raise BankError("Amount must be greater than zero.")
    if paise > MAX_AMOUNT:
        raise BankError(f"The maximum per transaction is {money(MAX_AMOUNT, False)}.")


# ----------------------------------------------------------------------
# Validation
# ----------------------------------------------------------------------

NAME_RE = re.compile(r"^[A-Za-z]+([ .'-]+[A-Za-z]+)*\.?$")
USERNAME_RE = re.compile(r"^[a-z0-9_.]{3,20}$")
IFSC_RE = re.compile(r"^[A-Z]{4}0[A-Z0-9]{6}$")


def clean_name(value):
    value = " ".join(value.split())
    if not value or len(value) > 60 or not NAME_RE.match(value):
        raise BankError("Enter your full name using letters only.")
    return " ".join(w[:1].upper() + w[1:] for w in value.split(" "))


def clean_username(value):
    value = value.strip().lower()
    if not USERNAME_RE.match(value):
        raise BankError("Username must be 3–20 characters: letters, digits, '.' or '_'.")
    return value


def check_password(value):
    if len(value) < 6:
        raise BankError("Password must be at least 6 characters.")


def check_pin(value):
    if not re.fullmatch(r"\d{4}", value or ""):
        raise BankError("PIN must be exactly 4 digits.")


def clean_ifsc(value):
    value = value.strip().upper()
    if not IFSC_RE.match(value):
        raise BankError("IFSC must be 4 letters, '0', then 6 letters or digits (e.g. SBIN0001234).")
    return value


def check_transfer_mode(mode, paise):
    if mode not in TRANSFER_MODES:
        raise BankError("Choose NEFT, RTGS or IMPS.")
    if mode == "RTGS" and paise < RTGS_MIN:
        raise BankError(f"RTGS needs at least {money(RTGS_MIN, False)}.")
    if mode == "IMPS" and paise > IMPS_MAX:
        raise BankError(f"IMPS allows at most {money(IMPS_MAX, False)}.")


# ----------------------------------------------------------------------
# Secrets: passwords and PINs are stored only as salted PBKDF2 hashes
# ----------------------------------------------------------------------


def hash_secret(secret, iterations=120_000):
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", secret.encode(), salt.encode(), iterations).hex()
    return f"pbkdf2${iterations}${salt}${digest}"


def verify_secret(secret, stored):
    _, iterations, salt, digest = stored.split("$")
    candidate = hashlib.pbkdf2_hmac("sha256", secret.encode(), salt.encode(), int(iterations)).hex()
    return hmac.compare_digest(candidate, digest)


# ----------------------------------------------------------------------
# Loans
# ----------------------------------------------------------------------


def loan_terms(product, principal):
    """(years, annual rate %) for a loan amount, from the product's tiers."""
    for limit, years, rate in LOANS[product]:
        if limit is None or principal < limit:
            return years, rate
    raise AssertionError("unreachable")


def emi(principal, annual_rate, years):
    """Equated monthly instalment in paise."""
    r = annual_rate / 12 / 100
    n = years * 12
    if r == 0:
        return math.ceil(principal / n)
    f = (1 + r) ** n
    return int(round(principal * r * f / (f - 1)))


def amortization(principal, annual_rate, years):
    """Yearly rows: principal paid, interest paid and balance left (paise)."""
    r = annual_rate / 12 / 100
    payment = emi(principal, annual_rate, years)
    balance = principal
    rows = []
    for year in range(1, years + 1):
        paid_p = paid_i = 0
        for month in range(12):
            interest = int(round(balance * r))
            principal_part = payment - interest
            if year == years and month == 11:  # last instalment clears rounding
                principal_part = balance
            balance -= principal_part
            paid_p += principal_part
            paid_i += interest
        rows.append({"year": year, "principal": paid_p, "interest": paid_i, "balance": max(balance, 0)})
    return rows

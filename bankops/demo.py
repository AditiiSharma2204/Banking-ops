"""A ready-made demo account with two months of realistic activity."""

import datetime as dt

from .bank import now

DEMO_USER, DEMO_PASSWORD, DEMO_PIN = "demo", "demo123", "1234"
FRIEND_USER, FRIEND_PIN = "priya.demo", "4321"


def reset_demo(bank):
    """(Re)create the demo accounts; returns the demo account number."""
    for user in (DEMO_USER, FRIEND_USER):
        bank.delete_account(user)

    start = (now() - dt.timedelta(days=62)).replace(hour=0, minute=0, second=0)

    def at(day, hour, minute=0):
        return start + dt.timedelta(days=day, hours=hour, minutes=minute)

    friend = bank.open_account("Priya Nair", FRIEND_USER, "priya-demo-pass", FRIEND_PIN, 25_000_00, when=at(0, 9))
    acc = bank.open_account("Aditi Sharma", DEMO_USER, DEMO_PASSWORD, DEMO_PIN, 50_000_00, when=at(0, 11))

    events = []  # (time, action) - posted in date order so running balances are right
    for month in (0, 30, 60):
        events.append((at(month + 1, 9, 5), lambda w: bank.deposit(
            acc, 85_000_00, DEMO_PIN, when=w, description="Salary credit - Acme Analytics")))
        events.append((at(month + 2, 18), lambda w: bank.transfer(
            acc, 918273, 22_000_00, "NEFT", DEMO_PIN, ifsc="ABCD0001234", note="Rent", when=w)))
    for day, amount, text in [(4, 3_500_00, "ATM withdrawal"), (9, 6_200_00, "Groceries"),
                              (15, 2_000_00, "ATM withdrawal"), (20, 4_800_00, "Electricity & internet"),
                              (34, 5_600_00, "Groceries"), (41, 12_000_00, "Laptop EMI"),
                              (48, 3_000_00, "ATM withdrawal"), (55, 7_450_00, "Groceries")]:
        events.append((at(day, 13), lambda w, a=amount, t=text: bank.withdraw(
            acc, a, DEMO_PIN, when=w, description=t)))
    events += [
        (at(12, 21, 30), lambda w: bank.transfer(acc, friend, 2_500_00, "IMPS", DEMO_PIN, note="Dinner split", when=w)),
        (at(27, 20), lambda w: bank.transfer(friend, acc, 1_200_00, "IMPS", FRIEND_PIN, note="Movie tickets", when=w)),
        (at(38, 12), lambda w: bank.apply_loan(acc, "Car Loan", 4_50_000_00, 7_00_000_00, "New hatchback",
                                               DEMO_PIN, when=w)),
        (at(39, 11), lambda w: bank.transfer(acc, 564738, 3_80_000_00, "NEFT", DEMO_PIN, ifsc="AUTO0000123",
                                             note="Car dealer", when=w)),
    ]
    for when, action in sorted(events, key=lambda e: e[0]):
        action(when)
    return acc

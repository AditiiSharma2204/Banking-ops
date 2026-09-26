import datetime as dt

import pytest

from bankops.bank import Bank
from bankops.core import (
    BankError,
    amortization,
    clean_ifsc,
    emi,
    hash_secret,
    loan_terms,
    money,
    to_paise,
    verify_secret,
)
from bankops.demo import DEMO_PIN, reset_demo

T0 = dt.datetime(2026, 9, 1, 10, 0)


@pytest.fixture
def bank(tmp_path):
    return Bank(tmp_path / "bank.db")


@pytest.fixture
def alice(bank):
    return bank.open_account("alice  sharma", "Alice", "secret1", "1234", 5_000_00, acc_no=123456, when=T0)


def test_money_and_amount_parsing():
    assert money(0) == "₹0.00"
    assert money(123456789) == "₹12,34,567.89"
    assert money(-150050) == "-₹1,500.50"
    assert money(1_00_000_00, False) == "₹1,00,000"
    assert to_paise("1500") == 150000 and to_paise("1,500.5") == 150050 and to_paise(0.1) == 10
    with pytest.raises(BankError):
        to_paise("12.345")


def test_secrets_are_hashed_and_salted():
    a, b = hash_secret("1234"), hash_secret("1234")
    assert a != b and "1234" not in a
    assert verify_secret("1234", a) and not verify_secret("1235", a)


def test_open_account_validates_and_records_deposit(bank, alice):
    acc = bank.account(alice)
    assert acc["name"] == "Alice Sharma" and acc["username"] == "alice" and acc["balance"] == 5_000_00
    assert "secret1" not in acc["password_hash"]
    assert bank.transactions(alice)[0]["description"] == "Account opening deposit"
    with pytest.raises(BankError, match="taken"):
        bank.open_account("Other", "alice", "secret1", "1234", 5_000_00)
    with pytest.raises(BankError, match="at least"):
        bank.open_account("Bob", "bob", "secret1", "1234", 999_00)
    with pytest.raises(BankError, match="PIN"):
        bank.open_account("Bob", "bob", "secret1", "12a4", 5_000_00)
    with pytest.raises(BankError, match="Password"):
        bank.open_account("Bob", "bob", "short", "1234", 5_000_00)


def test_login_lockout_and_unlock(bank, alice):
    assert bank.login("ALICE", "secret1", when=T0) == alice
    with pytest.raises(BankError, match="2 attempts left"):
        bank.login("alice", "x", when=T0)
    with pytest.raises(BankError, match="1 attempt left"):
        bank.login("alice", "x", when=T0)
    with pytest.raises(BankError, match="locked for 5 minutes"):
        bank.login("alice", "x", when=T0)
    with pytest.raises(BankError, match="locked"):
        bank.login("alice", "secret1", when=T0 + dt.timedelta(minutes=2))
    assert bank.login("alice", "secret1", when=T0 + dt.timedelta(minutes=6)) == alice
    with pytest.raises(BankError, match="Invalid username"):
        bank.login("nobody", "secret1")


def test_wrong_pins_lock_the_account(bank, alice):
    for _ in range(2):
        with pytest.raises(BankError, match="Wrong PIN"):
            bank.deposit(alice, 100_00, "0000", when=T0)
    with pytest.raises(BankError, match="locked"):
        bank.deposit(alice, 100_00, "0000", when=T0)
    with pytest.raises(BankError, match="locked"):
        bank.deposit(alice, 100_00, "1234", when=T0)
    assert bank.account(alice)["balance"] == 5_000_00


def test_deposit_withdraw_and_minimum_balance(bank, alice):
    assert bank.deposit(alice, 2_500_50, "1234", when=T0) == 7_500_50
    with pytest.raises(BankError, match="up to ₹6,500.50"):
        bank.withdraw(alice, 7_000_00, "1234", when=T0)
    assert bank.withdraw(alice, 6_500_50, "1234", when=T0) == 1_000_00
    with pytest.raises(BankError, match="greater than zero"):
        bank.deposit(alice, 0, "1234")


def test_internal_and_external_transfers(bank, alice):
    bob = bank.open_account("Bob Roy", "bob", "secret2", "4321", 2_000_00, acc_no=654321, when=T0)
    bank.transfer(alice, bob, 1_500_00, "IMPS", "1234", note="Lunch", when=T0)
    assert bank.account(alice)["balance"] == 3_500_00
    assert bank.account(bob)["balance"] == 3_500_00
    assert bank.transactions(bob)[-1]["description"] == "IMPS from A/c 123456 (Alice Sharma) · Lunch"

    with pytest.raises(BankError, match="IFSC"):
        bank.transfer(alice, 111111, 100_00, "NEFT", "1234", ifsc="bad")
    bank.transfer(alice, 111111, 100_00, "NEFT", "1234", ifsc="abcd0001234", when=T0)
    assert bank.transactions(alice)[-1]["description"] == "NEFT to A/c 111111 (ABCD0001234)"

    with pytest.raises(BankError, match="RTGS needs"):
        bank.transfer(alice, bob, 100_00, "RTGS", "1234")
    with pytest.raises(BankError, match="IMPS allows"):
        bank.transfer(alice, bob, 6_00_000_00, "IMPS", "1234")
    with pytest.raises(BankError, match="own account"):
        bank.transfer(alice, alice, 100_00, "IMPS", "1234")
    with pytest.raises(BankError, match="Insufficient"):
        bank.transfer(alice, bob, 3_000_00, "NEFT", "1234")


def test_failed_transfer_changes_nothing(bank, alice):
    bob = bank.open_account("Bob Roy", "bob", "secret2", "4321", 2_000_00, when=T0)
    before = (bank.account(alice)["balance"], bank.account(bob)["balance"], len(bank.transactions(alice)))
    with pytest.raises(BankError):
        bank.transfer(alice, bob, 4_500_00, "NEFT", "1234")
    assert (bank.account(alice)["balance"], bank.account(bob)["balance"], len(bank.transactions(alice))) == before


def test_loan_terms_and_emi():
    assert loan_terms("Home Loan", 30_00_000_00) == (6, 9.1)
    assert loan_terms("Home Loan", 60_00_000_00) == (8, 9.5)
    assert loan_terms("Personal Loan", 1_99_999_00) == (2, 11.0)
    # Rs 30 lakh at 9.1% for 6 years -> EMI about Rs 54,226, matching the C version
    assert 54_220_00 < emi(30_00_000_00, 9.1, 6) < 54_230_00
    rows = amortization(30_00_000_00, 9.1, 6)
    assert len(rows) == 6 and rows[-1]["balance"] == 0
    assert sum(r["principal"] for r in rows) == 30_00_000_00
    assert rows[0]["interest"] > rows[-1]["interest"]


def test_apply_loan(bank, alice):
    with pytest.raises(BankError, match="collateral"):
        bank.apply_loan(alice, "Car Loan", 5_00_000_00, 4_00_000_00, "Car", "1234")
    bank.apply_loan(alice, "Car Loan", 4_00_000_00, 6_00_000_00, "Car", "1234", when=T0)
    [loan] = bank.loans(alice)
    assert (loan["years"], loan["rate"]) == (3, 9.0)
    assert loan["total"] == loan["emi"] * 36
    assert bank.account(alice)["balance"] == 4_05_000_00


def test_change_pin_and_password(bank, alice):
    bank.change_pin(alice, "1234", "9999")
    bank.deposit(alice, 100_00, "9999")
    with pytest.raises(BankError):
        bank.change_password(alice, "wrong", "newpass1")
    bank.change_password(alice, "secret1", "newpass1")
    assert bank.login("alice", "newpass1") == alice


def test_demo_account_is_rich_and_resettable(bank):
    acc = reset_demo(bank)
    txns = bank.transactions(acc)
    assert len(txns) == 19
    assert [l["product"] for l in bank.loans(acc)] == ["Car Loan"]
    assert all(t["balance_after"] >= 1_000_00 for t in txns)
    # recorded in date order, so each running balance follows from the one before
    assert [t["ts"] for t in txns] == sorted(t["ts"] for t in txns)
    for prev, cur in zip(txns, txns[1:]):
        assert cur["balance_after"] == prev["balance_after"] + cur["amount"]
    bank.deposit(acc, 1_00, DEMO_PIN)
    again = reset_demo(bank)
    assert len(bank.transactions(again)) == len(txns)


def test_clean_ifsc():
    assert clean_ifsc(" abcd0a1b2c3 ") == "ABCD0A1B2C3"
    for bad in ("ABCD1234567", "ABC0123456", "ABCD0123"):
        with pytest.raises(BankError):
            clean_ifsc(bad)

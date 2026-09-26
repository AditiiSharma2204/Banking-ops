import sqlite3
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from bankops.bank import Bank

APP = str(Path(__file__).resolve().parents[2] / "streamlit_app.py")


@pytest.fixture(autouse=True)
def db(monkeypatch, tmp_path):
    path = str(tmp_path / "bank.db")
    monkeypatch.setenv("BANK_DB", path)
    return path


def run(at):
    at.run()
    assert not at.exception, at.exception
    return at


def start():
    return run(AppTest.from_file(APP, default_timeout=60))


def submit(at, label):
    next(b for b in at.button if b.label == label).click()
    return run(at)


def test_open_account_deposit_and_withdraw(db):
    at = start()
    at.text_input(key="open_name").input("aditi sharma")
    at.text_input(key="open_user").input("aditi")
    at.text_input(key="open_pwd").input("secret1")
    at.text_input(key="open_pin").input("2468")
    at.text_input(key="open_pin2").input("2468")
    at.number_input(key="open_deposit").set_value(20000.0)
    submit(at, "Open account")
    acc = at.session_state.acc_no
    assert acc is not None
    assert any("Welcome" in s.value for s in at.success)

    at.number_input(key="dep_amount").set_value(5000.0)
    at.text_input(key="dep_pin").input("2468")
    submit(at, "Deposit")
    assert any("New balance ₹25,000.00" in s.value for s in at.success)

    at.number_input(key="wd_amount").set_value(24500.0)
    at.text_input(key="wd_pin").input("2468")
    submit(at, "Withdraw")
    assert any("Insufficient funds" in e.value for e in at.error)
    assert Bank(db).account(acc)["balance"] == 25_000_00


def test_demo_account_transfer_loan_and_statement(db):
    at = start()
    at.button(key="demo_btn").click()
    run(at)
    acc = at.session_state.acc_no
    assert len(at.tabs) == 6
    assert [m.label for m in at.metric][:4] == [
        "Balance", "Money in · 30 days", "Money out · 30 days", "Loan EMIs / month"]

    bank = Bank(db)
    before = bank.account(acc)["balance"]
    with sqlite3.connect(db) as conn:
        friend = conn.execute("SELECT acc_no FROM accounts WHERE username = 'priya.demo'").fetchone()[0]

    at.text_input(key="tr_to").input(str(friend))
    run(at)
    assert any("Priya Nair" in i.value for i in at.info)
    at.number_input(key="tr_amount").set_value(1000.0)
    at.text_input(key="tr_pin").input("1234")
    submit(at, "Send money")
    assert bank.account(acc)["balance"] == before - 1_000_00

    at.number_input(key="loan_amount").set_value(100000.0)
    run(at)
    at.text_input(key="loan_purpose").input("Laptop")
    at.text_input(key="loan_pin").input("1234")
    next(b for b in at.button if b.label.startswith("Apply for")).click()
    run(at)
    assert len(bank.loans(acc)) == 2

    at.text_input(key="st_text").input("salary")
    run(at)
    assert next(m.value for m in at.metric if m.label == "Transactions") == "3"


def test_login_errors_and_lockout(db):
    Bank(db).open_account("Test User", "tester", "secret1", "1111", 5_000_00)
    at = start()
    for expected in ("2 attempts left", "1 attempt left", "locked"):
        at.text_input(key="login_user").input("tester")
        at.text_input(key="login_pwd").input("wrong")
        submit(at, "Log in")
        assert expected in at.error[0].value
    assert at.session_state.acc_no is None

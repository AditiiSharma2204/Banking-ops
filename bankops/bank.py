"""SQLite-backed bank: accounts, transactions, transfers and loans."""

import datetime as dt
import os
import random
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from .core import (
    LOCK_MINUTES,
    MAX_ATTEMPTS,
    MIN_BALANCE,
    BankError,
    check_amount,
    check_password,
    check_pin,
    check_transfer_mode,
    clean_ifsc,
    clean_name,
    clean_username,
    emi,
    hash_secret,
    loan_terms,
    money,
    verify_secret,
)

DEFAULT_DB = Path(__file__).resolve().parent.parent / "bank.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts (
    acc_no INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    pin_hash TEXT NOT NULL,
    balance INTEGER NOT NULL,
    failed_attempts INTEGER NOT NULL DEFAULT 0,
    locked_until TEXT,
    created TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    acc_no INTEGER NOT NULL REFERENCES accounts(acc_no) ON DELETE CASCADE,
    ts TEXT NOT NULL,
    kind TEXT NOT NULL,
    description TEXT NOT NULL,
    amount INTEGER NOT NULL,
    balance_after INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS loans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    acc_no INTEGER NOT NULL REFERENCES accounts(acc_no) ON DELETE CASCADE,
    product TEXT NOT NULL,
    principal INTEGER NOT NULL,
    rate REAL NOT NULL,
    years INTEGER NOT NULL,
    emi INTEGER NOT NULL,
    total INTEGER NOT NULL,
    purpose TEXT NOT NULL,
    ts TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_txn_acc ON transactions(acc_no, id);
"""


def now():
    return dt.datetime.now().replace(microsecond=0)


class Bank:
    def __init__(self, path=None):
        self.path = str(path or os.environ.get("BANK_DB", DEFAULT_DB))
        with self._db() as db:
            db.executescript(SCHEMA)

    @contextmanager
    def _db(self):
        """One connection per operation; commits on success, rolls back on error."""
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Accounts
    # ------------------------------------------------------------------

    def open_account(self, name, username, password, pin, deposit, acc_no=None, when=None):
        name, username = clean_name(name), clean_username(username)
        check_password(password)
        check_pin(pin)
        check_amount(deposit)
        if deposit < MIN_BALANCE:
            raise BankError(f"The opening deposit must be at least {money(MIN_BALANCE, False)}.")
        when = when or now()
        with self._db() as db:
            if db.execute("SELECT 1 FROM accounts WHERE username = ?", (username,)).fetchone():
                raise BankError("That username is taken. Try another.")
            taken = {r[0] for r in db.execute("SELECT acc_no FROM accounts")}
            while acc_no is None or acc_no in taken:
                acc_no = random.randint(100000, 999999)
            db.execute(
                "INSERT INTO accounts (acc_no, name, username, password_hash, pin_hash, balance, created)"
                " VALUES (?, ?, ?, ?, ?, 0, ?)",
                (acc_no, name, username, hash_secret(password), hash_secret(pin), when.isoformat()),
            )
            self._post(db, acc_no, "Deposit", "Account opening deposit", deposit, when)
        return acc_no

    def account(self, acc_no):
        with self._db() as db:
            row = db.execute("SELECT * FROM accounts WHERE acc_no = ?", (acc_no,)).fetchone()
        if not row:
            raise BankError("Account not found.")
        return dict(row)

    def find_account(self, acc_no):
        """Name for a same-bank account number, or None."""
        with self._db() as db:
            row = db.execute("SELECT name FROM accounts WHERE acc_no = ?", (acc_no,)).fetchone()
        return row["name"] if row else None

    def delete_account(self, username):
        with self._db() as db:
            db.execute("DELETE FROM accounts WHERE username = ?", (username,))

    # ------------------------------------------------------------------
    # Authentication with lockout
    # ------------------------------------------------------------------

    def _check_unlocked(self, row, when):
        if row["locked_until"] and dt.datetime.fromisoformat(row["locked_until"]) > when:
            wait = dt.datetime.fromisoformat(row["locked_until"]) - when
            minutes = max(1, round(wait.total_seconds() / 60))
            raise BankError(f"Too many wrong attempts. The account is locked for {minutes} more minute(s).")

    def _record_failure(self, db, row, what, when):
        attempts = row["failed_attempts"] + 1
        if attempts >= MAX_ATTEMPTS:
            until = (when + dt.timedelta(minutes=LOCK_MINUTES)).isoformat()
            db.execute("UPDATE accounts SET failed_attempts = 0, locked_until = ? WHERE acc_no = ?",
                       (until, row["acc_no"]))
            return f"Wrong {what}. Too many attempts - the account is locked for {LOCK_MINUTES} minutes."
        db.execute("UPDATE accounts SET failed_attempts = ? WHERE acc_no = ?", (attempts, row["acc_no"]))
        return f"Wrong {what} ({MAX_ATTEMPTS - attempts} attempt{'s' if MAX_ATTEMPTS - attempts != 1 else ''} left)."

    def login(self, username, password, when=None):
        when = when or now()
        with self._db() as db:
            row = db.execute("SELECT * FROM accounts WHERE username = ?", (username.strip().lower(),)).fetchone()
            if not row:
                raise BankError("Invalid username or password.")
            self._check_unlocked(row, when)
            if not verify_secret(password, row["password_hash"]):
                message = self._record_failure(db, row, "password", when)
            else:
                db.execute("UPDATE accounts SET failed_attempts = 0, locked_until = NULL WHERE acc_no = ?",
                           (row["acc_no"],))
                return row["acc_no"]
        raise BankError(message)

    def _authorise(self, db, acc_no, pin, when):
        row = db.execute("SELECT * FROM accounts WHERE acc_no = ?", (acc_no,)).fetchone()
        self._check_unlocked(row, when)
        if not verify_secret(pin or "", row["pin_hash"]):
            return row, self._record_failure(db, row, "PIN", when)
        db.execute("UPDATE accounts SET failed_attempts = 0 WHERE acc_no = ?", (acc_no,))
        return row, None

    @contextmanager
    def _pin_protected(self, acc_no, pin, when):
        """Yields (db, account row) after checking the PIN; a wrong PIN is
        recorded (committed) and then raised, so lockouts can't be dodged."""
        with self._db() as db:
            row, error = self._authorise(db, acc_no, pin, when)
        if error:
            raise BankError(error)
        with self._db() as db:
            yield db, dict(db.execute("SELECT * FROM accounts WHERE acc_no = ?", (acc_no,)).fetchone())

    # ------------------------------------------------------------------
    # Money movements
    # ------------------------------------------------------------------

    def _post(self, db, acc_no, kind, description, amount, when):
        balance = db.execute("SELECT balance FROM accounts WHERE acc_no = ?", (acc_no,)).fetchone()[0] + amount
        db.execute("UPDATE accounts SET balance = ? WHERE acc_no = ?", (balance, acc_no))
        db.execute(
            "INSERT INTO transactions (acc_no, ts, kind, description, amount, balance_after) VALUES (?, ?, ?, ?, ?, ?)",
            (acc_no, when.isoformat(), kind, description, amount, balance),
        )
        return balance

    def deposit(self, acc_no, amount, pin, when=None, description="Cash deposit"):
        check_amount(amount)
        when = when or now()
        with self._pin_protected(acc_no, pin, when) as (db, acc):
            return self._post(db, acc_no, "Deposit", description, amount, when)

    def withdraw(self, acc_no, amount, pin, when=None, description="Cash withdrawal"):
        check_amount(amount)
        when = when or now()
        with self._pin_protected(acc_no, pin, when) as (db, acc):
            if acc["balance"] - amount < MIN_BALANCE:
                raise BankError(
                    f"Insufficient funds. You can withdraw up to {money(max(acc['balance'] - MIN_BALANCE, 0))} "
                    f"(a minimum balance of {money(MIN_BALANCE, False)} must remain)."
                )
            return self._post(db, acc_no, "Withdrawal", description, -amount, when)

    def transfer(self, acc_no, to_acc, amount, mode, pin, ifsc=None, note="", when=None):
        check_amount(amount)
        check_transfer_mode(mode, amount)
        when = when or now()
        if int(to_acc) == int(acc_no):
            raise BankError("You can't transfer money to your own account.")
        internal = self.find_account(int(to_acc)) is not None
        if not internal:
            ifsc = clean_ifsc(ifsc or "")
        note = f" · {note.strip()[:40]}" if note and note.strip() else ""
        with self._pin_protected(acc_no, pin, when) as (db, acc):
            if acc["balance"] - amount < MIN_BALANCE:
                raise BankError(
                    f"Insufficient funds. You can send up to {money(max(acc['balance'] - MIN_BALANCE, 0))}."
                )
            where = f"A/c {to_acc}" + ("" if internal else f" ({ifsc})")
            balance = self._post(db, acc_no, "Transfer out", f"{mode} to {where}{note}", -amount, when)
            if internal:
                self._post(db, int(to_acc), "Transfer in", f"{mode} from A/c {acc_no} ({acc['name']}){note}",
                           amount, when)
            return balance

    # ------------------------------------------------------------------
    # Loans
    # ------------------------------------------------------------------

    def apply_loan(self, acc_no, product, principal, collateral, purpose, pin, when=None):
        check_amount(principal)
        if not purpose or not purpose.strip():
            raise BankError("Tell us the purpose of the loan.")
        if principal >= collateral:
            raise BankError("Not eligible: the loan must be less than the value of your collateral.")
        years, rate = loan_terms(product, principal)
        monthly = emi(principal, rate, years)
        when = when or now()
        with self._pin_protected(acc_no, pin, when) as (db, acc):
            db.execute(
                "INSERT INTO loans (acc_no, product, principal, rate, years, emi, total, purpose, ts)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (acc_no, product, principal, rate, years, monthly, monthly * years * 12, purpose.strip()[:80],
                 when.isoformat()),
            )
            return self._post(db, acc_no, "Loan", f"{product} disbursed", principal, when)

    def loans(self, acc_no):
        with self._db() as db:
            return [dict(r) for r in db.execute("SELECT * FROM loans WHERE acc_no = ? ORDER BY id", (acc_no,))]

    # ------------------------------------------------------------------
    # History and security
    # ------------------------------------------------------------------

    def transactions(self, acc_no):
        with self._db() as db:
            return [dict(r) for r in db.execute(
                "SELECT ts, kind, description, amount, balance_after FROM transactions WHERE acc_no = ? ORDER BY id",
                (acc_no,),
            )]

    def change_pin(self, acc_no, old_pin, new_pin, when=None):
        check_pin(new_pin)
        with self._pin_protected(acc_no, old_pin, when or now()) as (db, acc):
            db.execute("UPDATE accounts SET pin_hash = ? WHERE acc_no = ?", (hash_secret(new_pin), acc_no))

    def change_password(self, acc_no, old_password, new_password):
        check_password(new_password)
        with self._db() as db:
            row = db.execute("SELECT password_hash FROM accounts WHERE acc_no = ?", (acc_no,)).fetchone()
            if not verify_secret(old_password, row["password_hash"]):
                raise BankError("Your current password is incorrect.")
            db.execute("UPDATE accounts SET password_hash = ? WHERE acc_no = ?",
                       (hash_secret(new_password), acc_no))

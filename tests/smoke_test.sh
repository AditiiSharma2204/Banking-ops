#!/bin/sh
# Runs a scripted banking session and checks key outputs.
# Usage: tests/smoke_test.sh ./banking_ops
set -u
BIN=${1:-./banking_ops}
DIR=$(dirname "$0")
OUT=$("$BIN" < "$DIR/session.txt" 2>&1)
fail=0

expect() {
    if printf '%s' "$OUT" | grep -qF -- "$1"; then
        echo "PASS: $1"
    else
        echo "FAIL: expected output containing: $1"
        fail=1
    fi
}

expect "Registration successful! Welcome, Alice Sharma."
expect "Registration successful! Welcome, Bob Kumar."
expect "Insufficient funds"
expect "Rs. 1,500.50 withdrawn. New balance: Rs. 3,499.50"
expect "Beneficiary: Bob Kumar (same bank)"
expect "Rs. 500.00 sent to account 654321 via NEFT."
expect "Enter a positive amount"
expect "Incorrect PIN (1 of 3 attempts)."
expect "Rs. 250.50 deposited. New balance: Rs. 3,250.00"
expect "Tenure           : 6 years (72 months)"
expect "Interest rate    : 9.10% per annum"
expect "LOAN APPROVED! Rs. 30,00,000.00 has been credited"
expect "NEFT transfer from A/c 123456"
expect "The account has been locked."
expect "This account is locked"
expect "Goodbye!"

[ "$fail" -eq 0 ] && echo "All checks passed." || echo "Some checks failed."
exit "$fail"

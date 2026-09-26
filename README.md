# Banking Operations

A console-based banking simulator written in portable C99. You can open accounts, log in, move money, apply for loans and view statements, all from the terminal.

## Features

- **Multiple accounts:** register as many customers as you like (up to 50 per session), each with a unique username and 6-digit account number.
- **Secure login:** password confirmation at sign-up, and the account locks after 3 failed login attempts.
- **PIN-protected transactions:** every deposit, withdrawal, transfer and loan needs the 4-digit PIN, with 3 attempts allowed.
- **Deposit and withdraw:** a minimum balance of ₹1,000 is enforced, so the balance can never go negative.
- **Transfers:**
  - Transfers to another account in the same bank are credited to the recipient instantly.
  - Transfers to other banks need a validated IFSC code.
  - You can pick NEFT, RTGS (minimum ₹2 lakh) or IMPS (maximum ₹5 lakh).
- **Loans:**
  - Home, car and personal loans, each with its own tiered interest rates and tenure.
  - Each offer shows the monthly EMI, total interest and total repayable before you accept.
- **Mini statement:** your last 20 transactions with a running balance.
- **Change PIN.**
- **Accurate money handling:** amounts are stored as integer paise, so there are no floating-point rounding errors. They are displayed with Indian digit grouping (e.g. `Rs. 30,00,000.00`).

## Build and run

You need any C99 compiler (GCC, Clang, MinGW or MSVC).

```sh
make          # builds ./banking_ops
make run      # builds and starts the program
make test     # runs the scripted smoke test
```

Without `make`:

```sh
gcc -std=c99 -Wall -Wextra -O2 banking_ops.c -o banking_ops -lm
./banking_ops
```

It works on Windows, Linux and macOS.

## Loan rates

| Loan     | Tier 1                     | Tier 2                     | Tier 3                    |
|----------|----------------------------|----------------------------|---------------------------|
| Home     | < ₹20 L: 8.6%, 4 yrs       | < ₹60 L: 9.1%, 6 yrs       | ≥ ₹60 L: 9.5%, 8 yrs      |
| Car      | < ₹5 L: 9.0%, 3 yrs        | < ₹15 L: 9.5%, 5 yrs       | ≥ ₹15 L: 10.0%, 7 yrs     |
| Personal | < ₹2 L: 11.0%, 2 yrs       | < ₹10 L: 12.0%, 3 yrs      | ≥ ₹10 L: 13.0%, 5 yrs     |

A loan is approved only if the collateral value is greater than the loan amount.

## Project layout

```
banking_ops.c          # the whole program
Makefile               # build / run / test targets
tests/session.txt      # scripted input for the smoke test
tests/smoke_test.sh    # runs the session and checks the output
.github/workflows/     # CI: builds and tests on Linux and Windows
```

## Limitations

This is a learning project. Data is kept in memory only and is lost when the program exits. Passwords are stored in plain text in memory.

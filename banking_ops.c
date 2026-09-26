/*
 * Banking Operations - a console banking simulator in portable C99.
 *
 * Features: multiple accounts, login with lockout, PIN-protected
 * deposit / withdrawal / transfer, loans with EMI calculation,
 * mini statement and PIN change.
 *
 * All money is stored as integer paise (1 rupee = 100 paise) to avoid
 * floating-point rounding errors.
 */
#include <ctype.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_ACCOUNTS      50
#define MAX_TXNS          20
#define NAME_LEN          64
#define USER_LEN          32
#define PASS_LEN          64
#define DESC_LEN          64
#define MAX_LOGIN_TRIES   3
#define MAX_PIN_TRIES     3

#define PAISE(rupees)     ((long long)(rupees) * 100LL)
#define MIN_BALANCE       PAISE(1000)          /* Rs. 1,000 */
#define MAX_AMOUNT        PAISE(100000000)     /* Rs. 10 crore per operation */
#define RTGS_MIN          PAISE(200000)        /* Rs. 2 lakh */
#define IMPS_MAX          PAISE(500000)        /* Rs. 5 lakh */

typedef struct {
    char desc[DESC_LEN];
    long long amount;       /* positive = credit, negative = debit */
    long long balance_after;
} Transaction;

typedef struct {
    int acc_no;
    char name[NAME_LEN];
    char username[USER_LEN];
    char password[PASS_LEN];
    int pin;
    long long balance;
    long long loan_outstanding;
    int locked;
    Transaction txns[MAX_TXNS];
    int txn_count;          /* total ever recorded; last MAX_TXNS are kept */
} Account;

typedef struct {
    long long upto;         /* tier applies to amounts below this (paise) */
    int years;
    double rate;            /* annual interest rate, percent */
} LoanTier;

typedef struct {
    const char *name;
    LoanTier tiers[3];
} LoanProduct;

static const LoanProduct LOANS[] = {
    {"Home Loan",     {{PAISE(2000000), 4, 8.6},  {PAISE(6000000), 6, 9.1},  {0, 8, 9.5}}},
    {"Car Loan",      {{PAISE(500000),  3, 9.0},  {PAISE(1500000), 5, 9.5},  {0, 7, 10.0}}},
    {"Personal Loan", {{PAISE(200000),  2, 11.0}, {PAISE(1000000), 3, 12.0}, {0, 5, 13.0}}},
};
#define NUM_LOANS ((int)(sizeof LOANS / sizeof LOANS[0]))

static Account accounts[MAX_ACCOUNTS];
static int num_accounts = 0;

/* ------------------------------------------------------------------ */
/* Input / output helpers                                              */
/* ------------------------------------------------------------------ */

static void clear_screen(void)
{
#ifdef _WIN32
    system("cls");
#else
    fputs("\033[2J\033[H", stdout);
#endif
}

/* Reads one line into buf (newline stripped). Exits cleanly on EOF. */
static void read_line(const char *prompt, char *buf, size_t size)
{
    if (prompt)
        fputs(prompt, stdout);
    fflush(stdout);
    if (!fgets(buf, (int)size, stdin)) {
        puts("\nInput closed. Goodbye!");
        exit(0);
    }
    size_t len = strcspn(buf, "\n");
    if (buf[len] == '\n') {
        buf[len] = '\0';
    } else {
        int c;                          /* discard the rest of a long line */
        while ((c = getchar()) != '\n' && c != EOF)
            ;
    }
    /* trim trailing whitespace (e.g. '\r' from Windows input) */
    while (len > 0 && isspace((unsigned char)buf[len - 1]))
        buf[--len] = '\0';
}

static void pause_screen(void)
{
    char tmp[8];
    read_line("\nPress ENTER to continue...", tmp, sizeof tmp);
}

/* Reads an integer in [min, max], re-prompting until valid. */
static long read_long(const char *prompt, long min, long max)
{
    char buf[64];
    for (;;) {
        read_line(prompt, buf, sizeof buf);
        char *end;
        long v = strtol(buf, &end, 10);
        if (end != buf && *end == '\0' && v >= min && v <= max)
            return v;
        printf("  Please enter a number between %ld and %ld.\n", min, max);
    }
}

static int read_choice(int max)
{
    return (int)read_long("Enter your choice: ", 1, max);
}

/* Parses "1500" or "1500.5" or "1500.50" into paise. Returns -1 if invalid. */
static long long parse_amount(const char *s)
{
    long long rupees = 0, paise = 0;
    int digits = 0, frac = 0;

    for (; isdigit((unsigned char)*s); s++, digits++) {
        rupees = rupees * 10 + (*s - '0');
        if (rupees > MAX_AMOUNT / 100)
            return -1;
    }
    if (*s == '.') {
        for (s++; isdigit((unsigned char)*s) && frac < 2; s++, frac++)
            paise = paise * 10 + (*s - '0');
        if (frac == 1)
            paise *= 10;
    }
    if (*s != '\0' || (digits == 0 && frac == 0))
        return -1;
    return rupees * 100 + paise;
}

static long long read_amount(const char *prompt)
{
    char buf[64];
    for (;;) {
        read_line(prompt, buf, sizeof buf);
        long long amt = parse_amount(buf);
        if (amt > 0 && amt <= MAX_AMOUNT)
            return amt;
        puts("  Enter a positive amount (up to 2 decimal places, max Rs. 10 crore).");
    }
}

/* Formats paise as "Rs. 12,34,567.89" (Indian digit grouping). */
static const char *fmt_money(long long paise, char *out, size_t size)
{
    char digits[32], grouped[48];
    int neg = paise < 0;
    unsigned long long p = neg ? (unsigned long long)(-paise) : (unsigned long long)paise;
    int n = snprintf(digits, sizeof digits, "%llu", p / 100);
    int j = 0;

    for (int i = 0; i < n; i++) {
        int left = n - i;
        if (i > 0 && (left == 3 || (left > 3 && (left - 3) % 2 == 0)))
            grouped[j++] = ',';
        grouped[j++] = digits[i];
    }
    grouped[j] = '\0';
    snprintf(out, size, "%sRs. %s.%02llu", neg ? "-" : "", grouped, p % 100);
    return out;
}

/* Convenience wrapper: up to 4 formatted amounts may be live at once. */
static const char *money(long long paise)
{
    static char bufs[4][48];
    static int next = 0;
    next = (next + 1) % 4;
    return fmt_money(paise, bufs[next], sizeof bufs[next]);
}

/* ------------------------------------------------------------------ */
/* Account helpers                                                     */
/* ------------------------------------------------------------------ */

static Account *find_by_username(const char *username)
{
    for (int i = 0; i < num_accounts; i++)
        if (strcmp(accounts[i].username, username) == 0)
            return &accounts[i];
    return NULL;
}

static Account *find_by_acc_no(int acc_no)
{
    for (int i = 0; i < num_accounts; i++)
        if (accounts[i].acc_no == acc_no)
            return &accounts[i];
    return NULL;
}

static void record_txn(Account *a, const char *desc, long long amount)
{
    Transaction *t = &a->txns[a->txn_count % MAX_TXNS];
    snprintf(t->desc, sizeof t->desc, "%s", desc);
    t->amount = amount;
    t->balance_after = a->balance;
    a->txn_count++;
}

/* Asks for the PIN up to MAX_PIN_TRIES times. Returns 1 if verified. */
static int verify_pin(const Account *a)
{
    for (int i = 1; i <= MAX_PIN_TRIES; i++) {
        if ((int)read_long("Enter your 4-digit PIN: ", 0, 9999) == a->pin)
            return 1;
        printf("  Incorrect PIN (%d of %d attempts).\n", i, MAX_PIN_TRIES);
    }
    puts("Too many incorrect PIN attempts. Transaction cancelled.");
    return 0;
}

static int has_space(const char *s)
{
    for (; *s; s++)
        if (isspace((unsigned char)*s))
            return 1;
    return 0;
}

/* IFSC: 4 letters, a literal '0', then 6 alphanumeric characters. */
static int valid_ifsc(const char *s)
{
    if (strlen(s) != 11)
        return 0;
    for (int i = 0; i < 4; i++)
        if (!isalpha((unsigned char)s[i]))
            return 0;
    if (s[4] != '0')
        return 0;
    for (int i = 5; i < 11; i++)
        if (!isalnum((unsigned char)s[i]))
            return 0;
    return 1;
}

/* ------------------------------------------------------------------ */
/* Screens                                                             */
/* ------------------------------------------------------------------ */

static void register_account(void)
{
    Account a;
    char buf[PASS_LEN];

    clear_screen();
    puts("===== New Account Registration =====\n");
    if (num_accounts >= MAX_ACCOUNTS) {
        puts("Sorry, the bank cannot open more accounts right now.");
        pause_screen();
        return;
    }
    memset(&a, 0, sizeof a);

    do {
        read_line("Full name: ", a.name, sizeof a.name);
    } while (a.name[0] == '\0');

    for (;;) {
        read_line("Choose a username (no spaces): ", a.username, sizeof a.username);
        if (a.username[0] == '\0' || has_space(a.username))
            puts("  Username must be non-empty and contain no spaces.");
        else if (find_by_username(a.username))
            puts("  That username is taken. Try another.");
        else
            break;
    }

    for (;;) {
        read_line("Choose a password (min 6 characters): ", a.password, sizeof a.password);
        if (strlen(a.password) < 6) {
            puts("  Password is too short.");
            continue;
        }
        read_line("Confirm password: ", buf, sizeof buf);
        if (strcmp(a.password, buf) == 0)
            break;
        puts("  Passwords do not match.");
    }

    for (;;) {
        a.acc_no = (int)read_long("Choose a 6-digit account number: ", 100000, 999999);
        if (!find_by_acc_no(a.acc_no))
            break;
        puts("  That account number is already in use.");
    }

    for (;;) {
        int pin = (int)read_long("Set a 4-digit PIN: ", 0, 9999);
        if ((int)read_long("Confirm PIN: ", 0, 9999) == pin) {
            a.pin = pin;
            break;
        }
        puts("  PINs do not match.");
    }

    for (;;) {
        printf("Opening deposit (minimum %s): ", money(MIN_BALANCE));
        a.balance = read_amount("");
        if (a.balance >= MIN_BALANCE)
            break;
        puts("  Opening deposit is below the minimum balance.");
    }
    record_txn(&a, "Account opening deposit", a.balance);

    accounts[num_accounts++] = a;
    printf("\nRegistration successful! Welcome, %s.\n", a.name);
    printf("Account number: %d   Balance: %s\n", a.acc_no, money(a.balance));
    pause_screen();
}

static Account *login(void)
{
    char user[USER_LEN], pass[PASS_LEN];

    clear_screen();
    puts("===== Login =====\n");
    read_line("Username: ", user, sizeof user);
    Account *a = find_by_username(user);

    if (a && a->locked) {
        puts("This account is locked after too many failed attempts.");
        pause_screen();
        return NULL;
    }
    for (int i = 1; i <= MAX_LOGIN_TRIES; i++) {
        read_line("Password: ", pass, sizeof pass);
        /* same message either way so usernames can't be probed */
        if (a && strcmp(a->password, pass) == 0) {
            printf("\nLogin successful. Welcome back, %s!\n", a->name);
            pause_screen();
            return a;
        }
        printf("  Invalid username or password (%d of %d attempts).\n", i, MAX_LOGIN_TRIES);
    }
    if (a) {
        a->locked = 1;
        puts("Too many failed attempts. The account has been locked.");
    }
    pause_screen();
    return NULL;
}

static void deposit(Account *a)
{
    clear_screen();
    puts("===== Deposit =====\n");
    long long amt = read_amount("Amount to deposit: ");
    if (a->balance + amt > MAX_AMOUNT * 10) {
        puts("Deposit would exceed the maximum account balance.");
    } else if (verify_pin(a)) {
        a->balance += amt;
        record_txn(a, "Cash deposit", amt);
        printf("%s deposited. New balance: %s\n", money(amt), money(a->balance));
    }
    pause_screen();
}

static void withdraw(Account *a)
{
    clear_screen();
    puts("===== Withdraw =====\n");
    printf("Available to withdraw: %s\n\n", money(a->balance - MIN_BALANCE));
    long long amt = read_amount("Amount to withdraw: ");
    if (a->balance - amt < MIN_BALANCE) {
        printf("Insufficient funds: a minimum balance of %s must be maintained.\n",
               money(MIN_BALANCE));
    } else if (verify_pin(a)) {
        a->balance -= amt;
        record_txn(a, "Cash withdrawal", -amt);
        printf("%s withdrawn. New balance: %s\n", money(amt), money(a->balance));
    }
    pause_screen();
}

static void transfer(Account *a)
{
    static const char *modes[] = {"NEFT", "RTGS", "IMPS"};
    char buf[64], desc[DESC_LEN];

    clear_screen();
    puts("===== Transfer Money =====\n");
    int to_no = (int)read_long("Beneficiary account number (6 digits): ", 100000, 999999);
    if (to_no == a->acc_no) {
        puts("You cannot transfer money to your own account.");
        pause_screen();
        return;
    }
    Account *to = find_by_acc_no(to_no);
    if (to)
        printf("Beneficiary: %s (same bank)\n", to->name);

    long long amt = read_amount("Amount to transfer: ");

    puts("\nMode of transfer:\n1. NEFT\n2. RTGS (min Rs. 2,00,000)\n3. IMPS (max Rs. 5,00,000)");
    int mode = read_choice(3);
    if (mode == 2 && amt < RTGS_MIN) {
        printf("RTGS requires a minimum of %s.\n", money(RTGS_MIN));
        pause_screen();
        return;
    }
    if (mode == 3 && amt > IMPS_MAX) {
        printf("IMPS allows a maximum of %s.\n", money(IMPS_MAX));
        pause_screen();
        return;
    }
    if (!to) {
        for (;;) {
            read_line("Beneficiary bank IFSC code (e.g. SBIN0001234): ", buf, sizeof buf);
            for (char *c = buf; *c; c++)
                *c = (char)toupper((unsigned char)*c);
            if (valid_ifsc(buf))
                break;
            puts("  Invalid IFSC: expected 4 letters, '0', then 6 letters/digits.");
        }
    }
    if (a->balance - amt < MIN_BALANCE) {
        printf("Insufficient funds: a minimum balance of %s must be maintained.\n",
               money(MIN_BALANCE));
        pause_screen();
        return;
    }
    if (!verify_pin(a)) {
        pause_screen();
        return;
    }

    a->balance -= amt;
    snprintf(desc, sizeof desc, "%s transfer to A/c %d", modes[mode - 1], to_no);
    record_txn(a, desc, -amt);
    if (to) {
        to->balance += amt;
        snprintf(desc, sizeof desc, "%s transfer from A/c %d", modes[mode - 1], a->acc_no);
        record_txn(to, desc, amt);
    }
    printf("\n%s sent to account %d via %s.\nNew balance: %s\n",
           money(amt), to_no, modes[mode - 1], money(a->balance));
    pause_screen();
}

/* Equated monthly instalment for principal p (paise), annual rate %, n years. */
static long long emi(long long p, double annual_rate, int years)
{
    double r = annual_rate / 12.0 / 100.0;
    int n = years * 12;
    double f = pow(1.0 + r, n);
    return (long long)((double)p * r * f / (f - 1.0) + 0.5);
}

static void apply_loan(Account *a, const LoanProduct *product)
{
    char purpose[128];

    clear_screen();
    printf("===== %s =====\n\n", product->name);
    long long amt = read_amount("Loan amount: ");
    long long collateral = read_amount("Value of assets offered as collateral: ");
    if (amt >= collateral) {
        printf("\nSorry, you do not qualify: the loan must be less than the collateral value.\n");
        pause_screen();
        return;
    }
    do {
        read_line("Purpose of the loan: ", purpose, sizeof purpose);
    } while (purpose[0] == '\0');

    const LoanTier *t = &product->tiers[2];
    for (int i = 0; i < 2; i++) {
        if (amt < product->tiers[i].upto) {
            t = &product->tiers[i];
            break;
        }
    }
    long long monthly = emi(amt, t->rate, t->years);
    long long total = monthly * t->years * 12;

    printf("\n----- Loan offer -----\n");
    printf("Principal        : %s\n", money(amt));
    printf("Tenure           : %d years (%d months)\n", t->years, t->years * 12);
    printf("Interest rate    : %.2f%% per annum\n", t->rate);
    printf("Monthly EMI      : %s\n", money(monthly));
    printf("Total interest   : %s\n", money(total - amt));
    printf("Total repayable  : %s\n", money(total));

    puts("\n1. Accept offer\n2. Decline");
    if (read_choice(2) == 2) {
        puts("Offer declined.");
    } else if (verify_pin(a)) {
        char desc[DESC_LEN];
        a->balance += amt;
        a->loan_outstanding += total;
        snprintf(desc, sizeof desc, "%s disbursed", product->name);
        record_txn(a, desc, amt);
        printf("\nLOAN APPROVED! %s has been credited to your account.\n", money(amt));
    }
    pause_screen();
}

static void loans_menu(Account *a)
{
    clear_screen();
    puts("===== Loans =====\n");
    for (int i = 0; i < NUM_LOANS; i++)
        printf("%d. %s\n", i + 1, LOANS[i].name);
    printf("%d. Back to menu\n", NUM_LOANS + 1);
    int c = read_choice(NUM_LOANS + 1);
    if (c <= NUM_LOANS)
        apply_loan(a, &LOANS[c - 1]);
}

static void mini_statement(const Account *a)
{
    clear_screen();
    printf("===== Mini Statement - A/c %d (%s) =====\n\n", a->acc_no, a->name);
    printf("%-34s %18s %18s\n", "Description", "Amount", "Balance");
    printf("%-34s %18s %18s\n", "-----------", "------", "-------");
    int start = a->txn_count > MAX_TXNS ? a->txn_count - MAX_TXNS : 0;
    for (int i = start; i < a->txn_count; i++) {
        const Transaction *t = &a->txns[i % MAX_TXNS];
        printf("%-34s %18s %18s\n", t->desc, money(t->amount), money(t->balance_after));
    }
    printf("\nCurrent balance : %s\n", money(a->balance));
    if (a->loan_outstanding > 0)
        printf("Loan repayable  : %s\n", money(a->loan_outstanding));
    pause_screen();
}

static void change_pin(Account *a)
{
    clear_screen();
    puts("===== Change PIN =====\n");
    if (verify_pin(a)) {
        int pin = (int)read_long("New 4-digit PIN: ", 0, 9999);
        if ((int)read_long("Confirm new PIN: ", 0, 9999) == pin) {
            a->pin = pin;
            puts("PIN changed successfully.");
        } else {
            puts("PINs do not match. PIN not changed.");
        }
    }
    pause_screen();
}

static void account_menu(Account *a)
{
    for (;;) {
        clear_screen();
        printf("Account: %d   Holder: %s   Balance: %s\n\n", a->acc_no, a->name, money(a->balance));
        puts("1. Deposit money");
        puts("2. Withdraw money");
        puts("3. Transfer money");
        puts("4. Loans");
        puts("5. Mini statement");
        puts("6. Change PIN");
        puts("7. Logout");
        switch (read_choice(7)) {
        case 1: deposit(a); break;
        case 2: withdraw(a); break;
        case 3: transfer(a); break;
        case 4: loans_menu(a); break;
        case 5: mini_statement(a); break;
        case 6: change_pin(a); break;
        case 7:
            puts("You have been logged out.");
            pause_screen();
            return;
        }
    }
}

int main(void)
{
    for (;;) {
        clear_screen();
        puts("===== Welcome to Banking Operations =====\n");
        puts("1. Register a new account");
        puts("2. Login");
        puts("3. Exit");
        switch (read_choice(3)) {
        case 1:
            register_account();
            break;
        case 2: {
            Account *a = login();
            if (a)
                account_menu(a);
            break;
        }
        case 3:
            puts("Thank you for banking with us. Goodbye!");
            return 0;
        }
    }
}

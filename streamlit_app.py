"""Banking Ops - online banking web app (Streamlit).

Run with:  streamlit run streamlit_app.py
"""

import datetime as dt
import os

import altair as alt
import pandas as pd
import streamlit as st

from bankops.bank import Bank
from bankops.core import (
    LOANS,
    MIN_BALANCE,
    TRANSFER_MODES,
    BankError,
    amortization,
    emi,
    loan_terms,
    money,
    to_paise,
)
from bankops.demo import DEMO_PASSWORD, DEMO_PIN, DEMO_USER, reset_demo

st.set_page_config(page_title="Banking Ops", page_icon="🏦", layout="wide")

NAVY, TEAL, GREEN, RED, GOLD = "#1E293B", "#0D9488", "#16A34A", "#DC2626", "#D97706"

st.markdown(
    """
    <style>
      .block-container { padding-top: 2rem; max-width: 1250px; }
      .hero { background: linear-gradient(120deg, #0f172a 0%, #134e4a 60%, #0d9488 100%); color: #fff;
              border-radius: 18px; padding: 1.5rem 2rem; margin-bottom: 1rem; }
      .hero h1 { color: #fff; margin: 0; font-size: 2rem; }
      .hero p { margin: .3rem 0 0; opacity: .9; }
      .card { background: linear-gradient(135deg, #0f172a, #115e59); color: #fff; border-radius: 16px;
              padding: 1.1rem 1.2rem; }
      .card .label { font-size: .72rem; letter-spacing: 1px; text-transform: uppercase; opacity: .75; }
      .card .bal { font-size: 1.7rem; font-weight: 800; margin: .1rem 0 .6rem; }
      .card .row { display: flex; justify-content: space-between; font-size: .85rem; opacity: .9; }
      [data-testid="stMetric"] { background: #F0FDFA; border: 1px solid #CCFBF1; border-radius: 12px;
                                 padding: .7rem 1rem; }
      .txn { display: flex; justify-content: space-between; align-items: center; padding: .55rem 0;
             border-bottom: 1px solid #e2e8f0; }
      .txn:last-child { border-bottom: 0; }
      .txn .d { font-weight: 600; }
      .txn small { color: #64748b; }
      .amt-in { color: #16a34a; font-weight: 700; white-space: nowrap; padding-left: .8rem; }
      .amt-out { color: #0f172a; font-weight: 700; white-space: nowrap; padding-left: .8rem; }
      .offer { background: #F0FDFA; border: 1px solid #99F6E4; border-radius: 14px; padding: 1rem 1.2rem; }
      .offer .emi { font-size: 1.9rem; font-weight: 800; color: #0f766e; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def get_bank(path):
    return Bank(path)


bank = get_bank(os.environ.get("BANK_DB"))
state = st.session_state
state.setdefault("acc_no", None)


def rupees_input(label, key, value=0.0):
    return st.number_input(label, min_value=0.0, value=value, step=500.0, format="%.2f", key=key)


def paise(value):
    return to_paise(f"{value:.2f}")


def attempt(action, success):
    """Run a bank operation. On success, rerun so every balance on the page
    refreshes and show the confirmation at the top; on failure show the error."""
    try:
        result = action()
    except BankError as e:
        st.error(str(e), icon="⚠️")
        return
    state.notice = success(result) if callable(success) else success
    st.rerun()


def txn_frame(acc_no):
    df = pd.DataFrame(bank.transactions(acc_no))
    if df.empty:
        return df
    df["ts"] = pd.to_datetime(df["ts"])
    return df


# ----------------------------------------------------------------------
# Signed out: log in, open an account, or try the demo
# ----------------------------------------------------------------------


def signed_out():
    st.markdown(
        """<div class="hero"><h1>🏦 Banking Ops</h1>
        <p>A secure online banking demo: accounts, PIN-protected payments, NEFT/RTGS/IMPS transfers,
        loans with EMI planning and statements.</p></div>""",
        unsafe_allow_html=True,
    )
    left, right = st.columns([1.3, 1], gap="large")
    with left:
        tab_login, tab_open = st.tabs(["🔐 Log in", "✨ Open an account"])
        with tab_login:
            with st.form("login_form"):
                user = st.text_input("Username", key="login_user")
                pwd = st.text_input("Password", type="password", key="login_pwd")
                if st.form_submit_button("Log in", type="primary", use_container_width=True):
                    try:
                        state.acc_no = bank.login(user, pwd)
                        st.rerun()
                    except BankError as e:
                        st.error(str(e))
        with tab_open:
            with st.form("open_form"):
                name = st.text_input("Full name", key="open_name")
                c1, c2 = st.columns(2)
                user = c1.text_input("Username", help="3–20 characters: letters, digits, '.' or '_'", key="open_user")
                pwd = c2.text_input("Password", type="password", help="At least 6 characters", key="open_pwd")
                c1, c2 = st.columns(2)
                pin = c1.text_input("4-digit PIN", type="password", max_chars=4, key="open_pin")
                pin2 = c2.text_input("Confirm PIN", type="password", max_chars=4, key="open_pin2")
                deposit = rupees_input(f"Opening deposit (minimum {money(MIN_BALANCE, False)})", "open_deposit",
                                       10000.0)
                if st.form_submit_button("Open account", type="primary", use_container_width=True):
                    if pin != pin2:
                        st.error("The PINs don't match.")
                    else:
                        try:
                            acc = bank.open_account(name, user, pwd, pin, paise(deposit))
                            state.acc_no = acc
                            state.welcome = f"Welcome! Your account number is {acc}."
                            st.rerun()
                        except BankError as e:
                            st.error(str(e))
    with right:
        with st.container(border=True):
            st.markdown("#### 👀 Just looking?")
            st.write("Explore a demo account with two months of salary, bills, transfers and a car loan.")
            if st.button("Explore the demo account", type="primary", use_container_width=True, key="demo_btn"):
                with st.spinner("Setting up the demo account..."):
                    state.acc_no = reset_demo(bank)
                state.welcome = f"You're in the demo account. Its PIN is **{DEMO_PIN}**."
                st.rerun()
            st.caption(f"Or log in as `{DEMO_USER}` / `{DEMO_PASSWORD}` (PIN {DEMO_PIN}).")
        st.markdown(
            """
            - 🔒 Passwords and PINs stored only as salted hashes
            - 🚫 Account locks for 5 minutes after 3 wrong attempts
            - 💸 NEFT, RTGS and IMPS with real limits and IFSC checks
            - 📈 Loan offers with EMI and repayment schedule
            - 🧾 Filterable statement with CSV export
            """
        )
    st.caption("Demo project - no real money is involved.")


# ----------------------------------------------------------------------
# Signed in
# ----------------------------------------------------------------------


def sidebar(acc):
    with st.sidebar:
        st.markdown(
            f"""<div class="card"><div class="label">Available balance</div>
            <div class="bal">{money(acc['balance'])}</div>
            <div class="row"><span>{acc['name']}</span><span>A/c {acc['acc_no']}</span></div></div>""",
            unsafe_allow_html=True,
        )
        st.write("")
        st.caption(f"Minimum balance {money(MIN_BALANCE, False)} · Member since "
                   f"{dt.datetime.fromisoformat(acc['created']):%b %Y}")
        if st.button("Log out", use_container_width=True, key="logout"):
            state.acc_no = None
            st.rerun()


def overview(acc, df):
    loans = bank.loans(acc["acc_no"])
    since = pd.Timestamp.now() - pd.Timedelta(days=30)
    recent = df[df["ts"] >= since]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Balance", money(acc["balance"], False))
    c2.metric("Money in · 30 days", money(recent.loc[recent.amount > 0, "amount"].sum(), False))
    c3.metric("Money out · 30 days", money(-recent.loc[recent.amount < 0, "amount"].sum(), False))
    c4.metric("Loan EMIs / month", money(sum(l["emi"] for l in loans), False))

    left, right = st.columns([1.6, 1], gap="large")
    with left:
        st.markdown("#### Balance over time")
        daily = df.set_index("ts")["balance_after"].resample("D").last().ffill().reset_index()
        daily["Balance"] = daily["balance_after"] / 100
        chart = alt.Chart(daily).mark_area(
            line={"color": TEAL, "strokeWidth": 2.5},
            color=alt.Gradient(gradient="linear", stops=[alt.GradientStop(color="#99F6E4", offset=0),
                                                         alt.GradientStop(color="#FFFFFF", offset=1)],
                               x1=1, x2=1, y1=0, y2=1),
            interpolate="step-after",
        ).encode(
            x=alt.X("ts:T", title=None, axis=alt.Axis(format="%d %b")),
            y=alt.Y("Balance:Q", title="Balance (₹)", axis=alt.Axis(format=",.0f")),
            tooltip=[alt.Tooltip("ts:T", title="Date", format="%d %b %Y"),
                     alt.Tooltip("Balance:Q", title="Balance (₹)", format=",.2f")],
        ).properties(height=280)
        st.altair_chart(chart, use_container_width=True)

        st.markdown("#### Money in vs. out by month")
        monthly = df[~df["description"].str.contains("opening", case=False)].copy()
        monthly["Month"] = monthly["ts"].dt.strftime("%Y-%m")
        monthly["Flow"] = monthly["amount"].map(lambda a: "In" if a > 0 else "Out")
        monthly["₹"] = monthly["amount"].abs() / 100
        grouped = monthly.groupby(["Month", "Flow"], as_index=False)["₹"].sum()
        bars = alt.Chart(grouped).mark_bar(cornerRadiusEnd=4).encode(
            x=alt.X("Month:N", title=None),
            xOffset="Flow:N",
            y=alt.Y("₹:Q", title="Amount (₹)", axis=alt.Axis(format=",.0f")),
            color=alt.Color("Flow:N", scale=alt.Scale(domain=["In", "Out"], range=[GREEN, "#94A3B8"]),
                            legend=alt.Legend(orient="top", title=None)),
            tooltip=["Month", "Flow", alt.Tooltip("₹:Q", format=",.2f")],
        ).properties(height=240)
        st.altair_chart(bars, use_container_width=True)
    with right:
        st.markdown("#### Recent activity")
        rows = []
        for _, t in df.sort_values("ts", ascending=False).head(8).iterrows():
            cls = "amt-in" if t.amount > 0 else "amt-out"
            sign = "+" if t.amount > 0 else "−"
            rows.append(
                f'<div class="txn"><div><div class="d">{t.description}</div>'
                f'<small>{t.ts:%d %b %Y, %H:%M} · {t.kind}</small></div>'
                f'<div class="{cls}">{sign}{money(abs(t.amount))}</div></div>'
            )
        with st.container(border=True):
            st.markdown("".join(rows), unsafe_allow_html=True)


def move_money(acc):
    left, right = st.columns(2, gap="large")
    with left:
        with st.container(border=True):
            st.markdown("#### ⬇️ Deposit")
            with st.form("deposit_form", clear_on_submit=True):
                amount = rupees_input("Amount (₹)", "dep_amount")
                pin = st.text_input("PIN", type="password", max_chars=4, key="dep_pin")
                submitted = st.form_submit_button("Deposit", type="primary", use_container_width=True)
            if submitted:
                attempt(lambda: bank.deposit(acc["acc_no"], paise(amount), pin),
                        lambda bal: f"Deposited {money(paise(amount))}. New balance {money(bal)}.")
    with right:
        with st.container(border=True):
            st.markdown("#### ⬆️ Withdraw")
            st.caption(f"Available to withdraw: **{money(max(acc['balance'] - MIN_BALANCE, 0))}**")
            with st.form("withdraw_form", clear_on_submit=True):
                amount = rupees_input("Amount (₹)", "wd_amount")
                pin = st.text_input("PIN", type="password", max_chars=4, key="wd_pin")
                submitted = st.form_submit_button("Withdraw", type="primary", use_container_width=True)
            if submitted:
                attempt(lambda: bank.withdraw(acc["acc_no"], paise(amount), pin),
                        lambda bal: f"Withdrew {money(paise(amount))}. New balance {money(bal)}.")


def transfer(acc):
    left, right = st.columns([1.4, 1], gap="large")
    with left:
        to = st.text_input("Beneficiary account number", max_chars=6, placeholder="6 digits", key="tr_to")
        payee = None
        if to:
            if not (to.isdigit() and len(to) == 6):
                st.warning("Account numbers have 6 digits.")
                to = None
            elif int(to) == acc["acc_no"]:
                st.warning("That's your own account.")
                to = None
            else:
                payee = bank.find_account(int(to))
                if payee:
                    st.info(f"Same-bank account · **{payee}** - money arrives instantly.", icon="🏦")
                else:
                    st.info("Account at another bank - enter the branch IFSC below.", icon="🌐")
        with st.form("transfer_form", clear_on_submit=True):
            amount = rupees_input("Amount (₹)", "tr_amount")
            mode = st.radio("Mode", list(TRANSFER_MODES), horizontal=True, key="tr_mode",
                            captions=list(TRANSFER_MODES.values()))
            ifsc = "" if payee else st.text_input("IFSC code", placeholder="ABCD0001234", key="tr_ifsc")
            note = st.text_input("Note (optional)", max_chars=40, key="tr_note")
            pin = st.text_input("PIN", type="password", max_chars=4, key="tr_pin")
            send = st.form_submit_button("Send money", type="primary", use_container_width=True)
        if send:
            if not to:
                st.error("Enter a valid beneficiary account number first.")
            else:
                attempt(lambda: bank.transfer(acc["acc_no"], int(to), paise(amount), mode, pin, ifsc, note),
                        lambda bal: f"Sent {money(paise(amount))} via {mode} to A/c {to}. New balance {money(bal)}.")
    with right:
        with st.container(border=True):
            st.markdown("#### Transfer limits")
            st.markdown(
                "| Mode | Limit | Speed |\n|---|---|---|\n"
                "| IMPS | up to ₹5,00,000 | Instant |\n"
                "| NEFT | no limit | Within 30 min |\n"
                "| RTGS | from ₹2,00,000 | Real time |"
            )
            st.caption(f"A minimum balance of {money(MIN_BALANCE, False)} must remain after every transfer.")


def loans_tab(acc):
    left, right = st.columns([1, 1.2], gap="large")
    with left:
        product = st.selectbox("Loan type", list(LOANS), key="loan_product")
        amount = st.number_input("Loan amount (₹)", min_value=10000.0, max_value=5_00_00_000.0,
                                 value=5_00_000.0, step=50_000.0, format="%.0f", key="loan_amount")
        principal = paise(amount)
        years, rate = loan_terms(product, principal)
        monthly = emi(principal, rate, years)
        total = monthly * years * 12
        tiers = " · ".join(
            f"{'above' if lim is None else 'under'} {money(LOANS[product][i - 1][0] if lim is None else lim, False)}: "
            f"{r}% for {y} yrs"
            for i, (lim, y, r) in enumerate(LOANS[product])
        )
        st.caption(tiers)
        st.markdown(
            f"""<div class="offer"><div>Monthly EMI</div><div class="emi">{money(monthly)}</div>
            <div>{rate}% per year · {years} years ({years * 12} months)</div>
            <div>Total interest <b>{money(total - principal)}</b> · Total repayable <b>{money(total)}</b></div></div>""",
            unsafe_allow_html=True,
        )
        st.write("")
        with st.form("loan_form", clear_on_submit=True):
            collateral = rupees_input("Value of collateral (₹)", "loan_collateral", amount * 1.5)
            purpose = st.text_input("Purpose", placeholder="e.g. New hatchback", key="loan_purpose")
            pin = st.text_input("PIN", type="password", max_chars=4, key="loan_pin")
            apply = st.form_submit_button(f"Apply for {money(principal, False)}", type="primary",
                                          use_container_width=True)
        if apply:
            attempt(lambda: bank.apply_loan(acc["acc_no"], product, principal, paise(collateral), purpose, pin),
                    lambda bal: f"Loan approved! {money(principal)} credited. New balance {money(bal)}.")
    with right:
        st.markdown("#### Repayment schedule")
        sched = pd.DataFrame(amortization(principal, rate, years))
        long = sched.melt(id_vars="year", value_vars=["principal", "interest"], var_name="Part", value_name="p")
        long["₹"] = long["p"] / 100
        long["Part"] = long["Part"].str.title()
        st.altair_chart(
            alt.Chart(long).mark_bar(cornerRadiusEnd=3).encode(
                x=alt.X("year:O", title="Year"),
                y=alt.Y("₹:Q", title="Paid in the year (₹)", axis=alt.Axis(format=",.0f")),
                color=alt.Color("Part:N", scale=alt.Scale(domain=["Principal", "Interest"], range=[TEAL, GOLD]),
                                legend=alt.Legend(orient="top", title=None)),
                tooltip=["year", "Part", alt.Tooltip("₹:Q", format=",.2f")],
            ).properties(height=260),
            use_container_width=True,
        )
        sched_view = pd.DataFrame({
            "Year": sched["year"],
            "Principal paid": sched["principal"].map(money),
            "Interest paid": sched["interest"].map(money),
            "Balance left": sched["balance"].map(money),
        })
        st.dataframe(sched_view, hide_index=True, use_container_width=True)

    loans = bank.loans(acc["acc_no"])
    if loans:
        st.markdown("#### Your loans")
        st.dataframe(
            pd.DataFrame({
                "Loan": [l["product"] for l in loans],
                "Purpose": [l["purpose"] for l in loans],
                "Amount": [money(l["principal"]) for l in loans],
                "Rate": [f"{l['rate']}%" for l in loans],
                "Tenure": [f"{l['years']} yrs" for l in loans],
                "EMI": [money(l["emi"]) for l in loans],
                "Total repayable": [money(l["total"]) for l in loans],
                "Taken on": [f"{dt.datetime.fromisoformat(l['ts']):%d %b %Y}" for l in loans],
            }),
            hide_index=True, use_container_width=True,
        )


def statement(acc, df):
    c1, c2, c3 = st.columns([1.2, 1.5, 1.3])
    first, last = df["ts"].min().date(), df["ts"].max().date()
    period = c1.date_input("Period", (first, last), min_value=first, max_value=max(last, dt.date.today()),
                           format="DD/MM/YYYY", key="st_period")
    kinds = c2.multiselect("Type", sorted(df["kind"].unique()), placeholder="All types", key="st_kinds")
    text = c3.text_input("Search", placeholder="e.g. rent, IMPS, salary", key="st_text")

    view = df.copy()
    if isinstance(period, tuple) and len(period) == 2:
        view = view[(view["ts"].dt.date >= period[0]) & (view["ts"].dt.date <= period[1])]
    if kinds:
        view = view[view["kind"].isin(kinds)]
    if text:
        view = view[view["description"].str.contains(text, case=False, regex=False)]
    view = view.sort_values("ts", ascending=False)

    c1, c2, c3 = st.columns(3)
    c1.metric("Transactions", len(view))
    c2.metric("Credits", money(view.loc[view.amount > 0, "amount"].sum(), False))
    c3.metric("Debits", money(-view.loc[view.amount < 0, "amount"].sum(), False))

    table = pd.DataFrame({
        "Date": view["ts"].dt.strftime("%d %b %Y %H:%M"),
        "Description": view["description"],
        "Type": view["kind"],
        "Debit": view["amount"].map(lambda a: money(-a) if a < 0 else ""),
        "Credit": view["amount"].map(lambda a: money(a) if a > 0 else ""),
        "Balance": view["balance_after"].map(money),
    })
    st.dataframe(table, hide_index=True, use_container_width=True, height=min(38 * (len(table) + 1) + 3, 520))
    csv = pd.DataFrame({
        "date": view["ts"].dt.strftime("%Y-%m-%d %H:%M"), "description": view["description"], "type": view["kind"],
        "amount_inr": view["amount"] / 100, "balance_inr": view["balance_after"] / 100,
    }).to_csv(index=False)
    st.download_button("⬇️ Download statement (CSV)", csv, f"statement-{acc['acc_no']}.csv", "text/csv")


def security(acc):
    left, right = st.columns(2, gap="large")
    with left, st.container(border=True):
        st.markdown("#### Change PIN")
        with st.form("pin_form", clear_on_submit=True):
            old = st.text_input("Current PIN", type="password", max_chars=4, key="sec_old_pin")
            new = st.text_input("New PIN", type="password", max_chars=4, key="sec_new_pin")
            new2 = st.text_input("Confirm new PIN", type="password", max_chars=4, key="sec_new_pin2")
            submitted = st.form_submit_button("Change PIN", type="primary", use_container_width=True)
        if submitted:
            if new != new2:
                st.error("The new PINs don't match.")
            else:
                attempt(lambda: bank.change_pin(acc["acc_no"], old, new), "Your PIN has been changed.")
    with right, st.container(border=True):
        st.markdown("#### Change password")
        with st.form("pwd_form", clear_on_submit=True):
            old = st.text_input("Current password", type="password", key="sec_old_pwd")
            new = st.text_input("New password", type="password", key="sec_new_pwd")
            new2 = st.text_input("Confirm new password", type="password", key="sec_new_pwd2")
            submitted = st.form_submit_button("Change password", type="primary", use_container_width=True)
        if submitted:
            if new != new2:
                st.error("The new passwords don't match.")
            else:
                attempt(lambda: bank.change_password(acc["acc_no"], old, new), "Your password has been changed.")
    st.info("Passwords and PINs are stored only as salted PBKDF2 hashes. Three wrong attempts lock the "
            "account for 5 minutes.", icon="🔒")


def signed_in():
    try:
        acc = bank.account(state.acc_no)
    except BankError:
        state.acc_no = None
        st.rerun()
    sidebar(acc)
    hour = dt.datetime.now().hour
    greeting = "Good morning" if hour < 12 else "Good afternoon" if hour < 17 else "Good evening"
    st.markdown(f"## {greeting}, {acc['name'].split()[0]} 👋")
    if state.get("welcome"):
        st.success(state.pop("welcome"), icon="🎉")
    if state.get("notice"):
        st.success(state.pop("notice"), icon="✅")
    df = txn_frame(acc["acc_no"])
    tabs = st.tabs(["🏠 Overview", "💵 Deposit & withdraw", "🔁 Transfer", "🏦 Loans", "🧾 Statement", "🔒 Security"],
                   key="main_tabs")  # keyed so the open tab survives reruns
    with tabs[0]:
        overview(acc, df)
    with tabs[1]:
        move_money(acc)
    with tabs[2]:
        transfer(acc)
    with tabs[3]:
        loans_tab(acc)
    with tabs[4]:
        statement(acc, df)
    with tabs[5]:
        security(acc)


if state.acc_no is None:
    signed_out()
else:
    signed_in()

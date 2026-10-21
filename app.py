import streamlit as st

st.set_page_config(page_title="Knight Rebet Trigger Check", page_icon="⚡", layout="centered")

# --- SESSION STATE & RESET LOGIC ---
if "reset_counter" not in st.session_state:
    st.session_state.reset_counter = 0

def reset_inputs():
    st.session_state.reset_counter += 1

default_unit_dollar = float(st.query_params.get("unit", 25.0))

# --- HEADER & QUICK RESET ---
col_title, col_reset = st.columns([3, 1])
with col_title:
    st.title("⚡ Rebet Trigger Check")
    st.caption("Instant second-opinion & unit calculator for Knight Rebet alerts.")
with col_reset:
    st.write("")
    st.button("🔄 Next Bet", on_click=reset_inputs, use_container_width=True)

k = st.session_state.reset_counter

# --- STEP 1: LINE & GRAPH MOMENTUM CHECK ---
st.subheader("1. Line & Graph Momentum Check")
c1, c2 = st.columns(2)

with c1:
    line_status = st.radio(
        "1A. Does Rebet have the EXACT spread/total number in the alert?",
        ["Yes (Exact Match)", "No (Line moved 0.5+ pts)"],
        key=f"line_{k}"
    )
    odds_trend = st.radio(
        "1B. Orange Line (Pinnacle Odds) Direction:",
        [
            "✅ Moving in our favor (e.g. -120 ➔ -140, usually drops DOWN)",
            "❌ Bouncing back / Reversing (e.g. -150 ➔ -135)"
        ],
        key=f"trend_{k}",
        help="On the bot's chart, getting more expensive/sharper (like -120 to -145) usually slopes DOWNWARD. Make sure the latest movement isn't reversing back toward -120."
    )

with c2:
    limit_status = st.radio(
        "1C. White Line (Pinnacle Limit) Trend & Size:",
        [
            "✅ Increasing (Stepping UP) or Steady at 2k+",
            "⚠️ Flat at 1k or Less (Low / Early Limit)",
            "❌ Decreasing / Dropping Down"
        ],
        key=f"limit_{k}",
        help="The white line shows Pinnacle's max bet limit. We want limits stepping UP or holding strong, never dropping."
    )
    game_window = st.radio(
        "1D. When is the game?",
        ["Within 48 Hours (Today / Tomorrow)", "3+ Days Out (Early Week)"],
        key=f"time_{k}"
    )

key_trap = st.checkbox(
    "🏈 Football Underdog Trap: Is this a football spread sitting at +2.5 or +6.5?",
    key=f"trap_{k}",
    help="Check this if betting a football underdog spread trapped right under the key numbers of 3 or 7."
)

# --- INSTANT GRAPH DISQUALIFIERS ---
if "No" in line_status:
    st.divider()
    st.error("🛑 **HARD PASS — REBET LINE MOVED**")
    st.markdown(
        "**Why:** Rebet already moved the spread or total number. Unless your new number has its own box with a valid `W%` on the Discord alert, the edge is gone."
    )
    st.stop()

if "Bouncing back" in odds_trend:
    st.divider()
    st.error("🛑 **HARD PASS — REVERSE STEAM (ODDS BOUNCING BACK)**")
    st.markdown(
        "**Why:** Pinnacle's odds are moving *against* this bet (e.g., `-150` weakening back to `-135`). Sharp buyback has entered the market on the opposite side. Never bet into reverse line movement."
    )
    st.stop()

if "Decreasing" in limit_status:
    st.divider()
    st.error("🛑 **HARD PASS — PINNACLE LIMITS ARE DROPPING**")
    st.markdown(
        "**Why:** The white limit line on the graph is decreasing. When Pinnacle slashes betting limits, it signals lineup uncertainty, injury news, or market recalibration. Stay away."
    )
    st.stop()

# --- STEP 2: NUMBERS FROM ALERT & REBET ---
st.subheader("2. Enter Alert `W%` & Live Rebet Odds")
col_a, col_b = st.columns(2)

with col_a:
    win_pct = st.number_input(
        "Alert `W%` (from Discord box)",
        min_value=10.0, max_value=90.0, value=56.0, step=0.1, format="%.2f",
        key=f"wp_{k}",
        help="Enter the exact W% shown inside the code block of the Knight Rebet alert."
    )

with col_b:
    rebet_odds = st.number_input(
        "Live Odds on YOUR Rebet App",
        min_value=-500, max_value=500, value=-119, step=1,
        key=f"odds_{k}",
        help="Enter the current odds on your Rebet screen right now (even if they shifted a few cents from the alert)."
    )

if -99 <= rebet_odds <= 99:
    st.warning("Please enter valid American odds (e.g., `-115` or `+105`).")
    st.stop()

# --- CALCULATION ENGINE ---
p = win_pct / 100.0
q = 1.0 - p

if rebet_odds > 0:
    dec_odds = 1.0 + (rebet_odds / 100.0)
    implied_be = 100.0 / (rebet_odds + 100.0)
else:
    dec_odds = 1.0 + (100.0 / abs(rebet_odds))
    implied_be = abs(rebet_odds) / (abs(rebet_odds) + 100.0)

fv_american = -round((p / q) * 100) if p >= 0.5 else round((q / p) * 100)

ev_pct = ((p * dec_odds) - 1.0) * 100.0
b = dec_odds - 1.0
full_kelly = ((b * p) - q) / b if b > 0 else 0.0
raw_qk_units = max(0.0, full_kelly * 0.25 * 100.0)

min_ev_hurdle = 4.5 if "3+ Days" in game_window else 2.5
min_dec_needed = (1.0 + (min_ev_hurdle / 100.0)) / p
max_prob_allowed = 1.0 / min_dec_needed
max_american_playable = (
    -round((max_prob_allowed / (1.0 - max_prob_allowed)) * 100)
    if max_prob_allowed >= 0.5
    else round(((1.0 - max_prob_allowed) / max_prob_allowed) * 100)
)

# Apply Risk Caps based on Limit & Time Window
is_low_or_early = ("Flat at 1k" in limit_status) or ("3+ Days" in game_window)
unit_cap = 0.85 if is_low_or_early else 1.25
final_units = min(raw_qk_units, unit_cap)

# --- STEP 3: INSTANT VERDICT DISPLAY ---
st.divider()
st.subheader("📊 Trigger Verdict")

if key_trap and ev_pct < 5.0:
    st.error("🛑 **PASS — KEY NUMBER TRAP**")
    st.markdown(
        f"**Why:** Even with **{ev_pct:.2f}% EV**, taking a football underdog at `+2.5` or `+6.5` without crossing the key number (3 or 7) is a long-term trap below 5% EV."
    )
elif ev_pct < min_ev_hurdle:
    st.error(f"🛑 **PASS — EDGE TOO THIN ({ev_pct:+.2f}% EV)**")
    reasons = []
    if "3+ Days" in game_window and ev_pct >= 2.5:
        reasons.append(f"- **Time Lockup Penalty:** Games 3+ days away require at least **+{min_ev_hurdle:.1f}% EV** to justify tying up bankroll and taking on injury/weather variance.")
    else:
        reasons.append(f"- **Below Minimum Threshold:** At `{rebet_odds:+d}`, your live edge is **{ev_pct:+.2f}% EV**, which falls below our **+{min_ev_hurdle:.1f}% EV** minimum needed to clear Rebet's tax/fee friction.")
    reasons.append(f"- **Worst Playable Price:** To bet this line, Rebet needs to be at **`{max_american_playable:+d}` or better** (Fair Value is `{fv_american:+d}`).")
    st.markdown("\n".join(reasons))

elif final_units < 0.40:
    st.warning(f"✋ **PASS — SUB-MINIMUM STAKE ({raw_qk_units:.2f}U)**")
    st.markdown(
        f"**Why:** The bet has a +{ev_pct:.2f}% edge, but Quarter-Kelly sizing (`{raw_qk_units:.2f}U`) is below our `0.40U` minimum floor."
    )
else:
    st.success("✅ **GREEN LIGHT — PULL THE TRIGGER!**")
    m1, m2, m3 = st.columns(3)
    m1.metric("🎯 Recommended Units", f"{final_units:.2f} U")
    m2.metric("📈 Live Edge (EV%)", f"+{ev_pct:.2f}%")
    m3.metric("⚖️ Worst Playable Odds", f"{max_american_playable:+d}")

    notes = [
        f"- **True Fair Value:** `{fv_american:+d}` (`{win_pct:.2f}%` win probability vs. Rebet's `{implied_be*100:.2f}%` break-even).",
        "- **Graph Confirmation:** Odds are steaming in your favor and Pinnacle limits are healthy."
    ]
    if raw_qk_units > unit_cap:
        notes.append(
            f"- **🛡️ Risk Cap Applied:** The bot's raw QK is `{raw_qk_units:.2f}U`, which we automatically capped at **`{unit_cap:.2f}U`** because limits are still at `1k` or the game is `3+ Days Out`."
        )
    else:
        notes.append(f"- **Sizing:** Standard Quarter-Kelly sizing (`{final_units:.2f}U`).")
    notes.append(
        f"- **Note on 'Already Sent Before' Alerts:** Even if the bot shows `⚠️ Already sent before`, this bet is **100% good to place** as long as your Rebet screen gives you `{max_american_playable:+d}` or better."
    )
    st.info("\n".join(notes))

with st.expander("💵 Optional: Convert Units to Dollars ($)"):
    unit_val = st.number_input("Your 1U Dollar Size ($)", min_value=1.0, value=default_unit_dollar, step=5.0)
    st.query_params["unit"] = str(unit_val)
    if ev_pct >= min_ev_hurdle and final_units >= 0.40 and not (key_trap and ev_pct < 5.0):
        st.markdown(f"**Exact Wager Amount:** **`${final_units * unit_val:.2f}`** *(for `{final_units:.2f}U`)*")

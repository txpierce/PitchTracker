from datetime import datetime
import pandas as pd
import streamlit as st
from supabase import create_client

# Connect to Supabase Cloud Database using Streamlit Secrets
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(
    page_title="Sliders Live Analytics", page_icon="⚾", layout="centered"
)
st.title("⚾ South Texas Sliders Live Hub")

# Sidebar Mode Switcher
mode = st.sidebar.selectbox(
    "Select Mode", ["Our Pitcher Tracker", "Opponent Pitcher Scout"]
)


# Helper function to fetch live data from Supabase
def get_data():
  try:
    response = supabase.table("pitch_logs").select("*").execute()
    return pd.DataFrame(response.data)
  except Exception:
    return pd.DataFrame()


df = get_data()

# -------------------------------------------------------------
# MODE 1: OUR PITCHER TRACKER (Dugout Tool)
# -------------------------------------------------------------
if mode == "Our Pitcher Tracker":
  st.subheader("🟢 Live Pitcher Tracker")

  with st.form("our_pitcher_form", clear_on_submit=True):
    pitcher = st.selectbox(
        "Pitcher Name / #",
        ["Player A (RHP)", "Player B (LHP)", "Player C (RHP)"],
    )
    count = st.selectbox(
        "Current Count", ["0-0", "0-1", "1-0", "1-1", "0-2", "1-2", "2-2", "3-2"]
    )
    pitch_type = st.selectbox(
        "Pitch Type", ["Fastball", "Slider", "Curveball", "Changeup"]
    )
    result = st.selectbox(
        "Result", ["Ball", "Called Strike", "Whiff", "Foul", "In Play"]
    )

    submitted = st.form_submit_button("Log Pitch")
    if submitted:
      supabase.table("pitch_logs").insert({
          "mode": "Our Pitcher",
          "pitcher": pitcher,
          "count": count,
          "pitch_type": pitch_type,
          "result": result,
      }).execute()
      st.success("Pitch logged live!")
      st.rerun()

  # Real-Time Display for Our Pitchers
  if not df.empty and "mode" in df.columns:
    our_df = df[df["mode"] == "Our Pitcher"]
    if not our_df.empty:
      st.divider()
      st.subheader("📊 Live Outing Stats")
      selected_p = st.selectbox(
          "View Pitcher Stats:", our_df["pitcher"].unique()
      )
      p_data = our_df[our_df["pitcher"] == selected_p]

      st.metric("Total Pitches Thrown", len(p_data))

      if len(p_data) > 0:
        st.write("**Pitch Mix Distribution (%)**")
        mix = p_data["pitch_type"].value_counts(normalize=True) * 100
        st.dataframe(mix.round(1))

# -------------------------------------------------------------
# MODE 2: OPPONENT PITCHER SCOUT (Stands / Dugout Tool)
# -------------------------------------------------------------
elif mode == "Opponent Pitcher Scout":
  st.subheader("🔍 Opponent Pitcher Real-Time Scout")

  with st.form("scout_form", clear_on_submit=True):
    opp_pitcher = st.text_input(
        "Opposing Pitcher (Name or #)", value="Opponent RHP #24"
    )
    count = st.selectbox(
        "Opponent Count", ["0-0", "0-1", "1-0", "1-1", "0-2", "1-2", "2-2", "3-2"]
    )
    pitch_type = st.selectbox(
        "Pitch Thrown", ["Fastball", "Slider", "Curveball", "Changeup"]
    )
    result = st.selectbox(
        "Result",
        ["Ball", "Called Strike", "Whiff", "Foul", "Hit Hard", "Weak Contact"],
    )

    submitted = st.form_submit_button("Log Opponent Pitch")
    if submitted:
      supabase.table("pitch_logs").insert({
          "mode": "Opponent Scout",
          "pitcher": opp_pitcher,
          "count": count,
          "pitch_type": pitch_type,
          "result": result,
      }).execute()
      st.success("Opponent pitch logged!")
      st.rerun()

  # Real-Time Hitter Cheat Sheet
  if not df.empty and "mode" in df.columns:
    opp_df = df[df["mode"] == "Opponent Scout"]
    if not opp_df.empty:
      st.divider()
      st.subheader("💡 Instant Hitter Cheat Sheet")
      selected_opp = st.selectbox(
          "Select Opposing Pitcher:", opp_df["pitcher"].unique()
      )
      opp_data = opp_df[opp_df["pitcher"] == selected_opp]

      st.write(f"**Total Pitches Tracked:** {len(opp_data)}")

      col1, col2 = st.columns(2)
      with col1:
        st.write("**Overall Pitch Mix**")
        st.dataframe(
            (opp_data["pitch_type"].value_counts(normalize=True) * 100).round(1)
        )

      with col2:
        st.write("**2-Strike Putaway Tendency**")
        two_strike_data = opp_data[opp_data["count"].isin(["0-2", "1-2", "2-2", "3-2"])]
        if not two_strike_data.empty:
          st.dataframe(
              (
                  two_strike_data["pitch_type"].value_counts(normalize=True)
                  * 100
              ).round(1)
          )
        else:
          st.info("Log 2-strike counts to see putaway data.")

import streamlit as st
import pandas as pd
from supabase import create_client

# Page Config
st.set_page_config(page_title="South Texas Sliders - Pitch Tracker", page_icon="⚾", layout="centered")

# Initialize Supabase Client using Streamlit Secrets
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.title("⚾ South Texas Sliders Pitch Tracker")

# Sidebar Mode Selection
st.sidebar.header("Navigation")
mode = st.sidebar.radio("Select Mode", ["Our Pitcher Tracker", "Opponent Pitcher Scout"])

# Fetch existing pitch logs from Supabase
@st.cache_data(ttl=2)
def load_data():
    try:
        response = supabase.table("pitch_logs").select("*").execute()
        return pd.DataFrame(response.data)
    except Exception as e:
        return pd.DataFrame()

df = load_data()

if mode == "Our Pitcher Tracker":
    st.header("📊 Our Pitcher Tracker")
    
    with st.form("pitch_form", clear_on_submit=True):
        pitcher_name = st.text_input("Pitcher Name")
        col1, col2 = st.columns(2)
        with col1:
            count = st.selectbox("Count (Balls-Strikes)", ["0-0", "1-0", "0-1", "1-1", "2-0", "2-1", "3-0", "3-1", "3-2", "0-2", "1-2", "2-2"])
            pitch_type = st.selectbox("Pitch Type", ["Fastball", "Slider", "Curveball", "Changeup", "Splitter", "Sinker"])
        with col2:
            result = st.selectbox("Result", ["Called Strike", "Swinging Strike", "Ball", "Foul", "In Play - Out", "In Play - Hit", "Hit By Pitch"])
            
        submitted = st.form_submit_button("Log Pitch")
        
        if submitted:
            if pitcher_name.strip() == "":
                st.warning("Please enter a pitcher name.")
            else:
                try:
                    supabase.table("pitch_logs").insert({
                        "mode": mode,
                        "pitcher": pitcher_name,
                        "count": count,
                        "pitch_type": pitch_type,
                        "result": result
                    }).execute()
                    st.success(f"Logged {pitch_type} for {pitcher_name}!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error logging pitch: {e}")

    st.markdown("---")
    st.subheader("📈 Live Outing Stats")
    
    if not df.empty and "pitcher" in df.columns:
        our_df = df[df["mode"] == "Our Pitcher Tracker"]
        if not our_df.empty:
            selected_pitcher = st.selectbox("Select Pitcher to View", our_df["pitcher"].unique())
            pitcher_df = our_df[our_df["pitcher"] == selected_pitcher]
            
            st.metric("Total Pitches Thrown", len(pitcher_df))
            
            if len(pitcher_df) > 0:
                st.write("### Pitch Mix Distribution")
                mix = pitcher_df["pitch_type"].value_counts(normalize=True) * 100
                st.dataframe(mix.round(1).astype(str) + '%')
        else:
            info_text = "No pitches logged for our pitchers yet."
            st.info(info_text)
    else:
        st.info("No pitch data logged yet today.")

else:
    st.header("🎯 Opponent Pitcher Scout")
    
    with st.form("scout_form", clear_on_submit=True):
        opp_pitcher = st.text_input("Opponent Pitcher Name / #")
        col1, col2 = st.columns(2)
        with col1:
            count = st.selectbox("Count (Balls-Strikes)", ["0-0", "1-0", "0-1", "1-1", "2-0", "2-1", "3-0", "3-1", "3-2", "0-2", "1-2", "2-2"], key="opp_count")
            pitch_type = st.selectbox("Pitch Type", ["Fastball", "Slider", "Curveball", "Changeup", "Splitter", "Sinker"], key="opp_type")
        with col2:
            result = st.selectbox("Result", ["Called Strike", "Swinging Strike", "Ball", "Foul", "In Play - Out", "In Play - Hit", "Hit By Pitch"], key="opp_result")
            
        submitted = st.form_submit_button("Log Opponent Pitch")
        
        if submitted:
            if opp_pitcher.strip() == "":
                st.warning("Please enter an opponent pitcher identifier.")
            else:
                try:
                    supabase.table("pitch_logs").insert({
                        "mode": mode,
                        "pitcher": opp_pitcher,
                        "count": count,
                        "pitch_type": pitch_type,
                        "result": result
                    }).execute()
                    st.success(f"Logged opponent pitch!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error logging pitch: {e}")

    st.markdown("---")
    st.subheader("💡 Instant Hitter Cheat Sheet")
    
    if not df.empty and "mode" in df.columns:
        opp_df = df[df["mode"] == "Opponent Pitcher Scout"]
        if not opp_df.empty:
            selected_opp = st.selectbox("Select Opponent Pitcher", opp_df["pitcher"].unique())
            opp_pitcher_df = opp_df[opp_df["pitcher"] == selected_opp]
            
            st.metric("Total Pitches Charted", len(opp_pitcher_df))
            
            st.write("### Overall Pitch Mix")
            st.dataframe((opp_pitcher_df["pitch_type"].value_counts(normalize=True) * 100).round(1).astype(str) + '%')
            
            st.write("### 2-Strike Tendencies")
            two_strike_df = opp_pitcher_df[opp_pitcher_df["count"].isin(["0-2", "1-2", "2-2", "3-2"])]
            if not two_strike_df.empty:
                st.dataframe((two_strike_df["pitch_type"].value_counts(normalize=True) * 100).round(1).astype(str) + '%')
            else:
                st.info("No 2-strike counts logged yet for this pitcher.")
        else:
            st.info("No opponent pitches charted yet.")
    else:
        st.info("No pitch data logged yet.")

# Sidebar Reset Button
st.sidebar.markdown("---")
st.sidebar.subheader("Game Management")
if st.sidebar.button("🗑️ Clear Game Data / Reset"):
    try:
        supabase.table("pitch_logs").delete().neq("id", 0).execute()
        st.sidebar.success("Game data cleared successfully!")
        st.rerun()
    except Exception as e:
        st.sidebar.error(f"Error clearing data: {e}")

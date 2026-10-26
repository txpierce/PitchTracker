import streamlit as st
import pandas as pd
from supabase import create_client

# Page Config
st.set_page_config(page_title="TX_Pierce - Pitch Tracker", page_icon="⚾", layout="centered")

# Initialize Supabase Client using Streamlit Secrets
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.title("⚾ TX_Pierce Pitch Tracker")

# Sidebar Mode Selection & Lineup Setup
st.sidebar.header("Navigation")
mode = st.sidebar.radio("Select Mode", ["Our Pitcher Tracker", "Opponent Pitcher Scout"])

st.sidebar.markdown("---")
st.sidebar.header("📋 Lineup Setup")
default_lineup = "Batter 1\nBatter 2\nBatter 3\nBatter 4\nBatter 5\nBatter 6\nBatter 7\nBatter 8\nBatter 9"
lineup_input = st.sidebar.text_area("Batting Lineup (One per line)", value=default_lineup, height=150)
batters_list = [b.strip() for b in lineup_input.split("\n") if b.strip()]

# Fetch existing pitch logs from Supabase
@st.cache_data(ttl=2)
def load_data():
    try:
        response = supabase.table("pitch_logs").select("*").order("timestamp", desc=False).execute()
        return pd.DataFrame(response.data)
    except Exception as e:
        return pd.DataFrame()

df = load_data()

if mode == "Our Pitcher Tracker":
    st.header("📊 Our Pitcher Tracker")
    
    # Persistent & Reliever Pitcher Management in Sidebar
    st.sidebar.markdown("---")
    st.sidebar.header("⚙️ Active Pitcher Control")
    
    existing_pitchers = []
    if not df.empty and "pitcher" in df.columns:
        existing_pitchers = list(df[df["mode"] == mode]["pitcher"].unique())
    
    pitcher_options = existing_pitchers + ["➕ Add New Reliever/Pitcher"]
    selected_pitcher_option = st.sidebar.selectbox("Current Pitcher", pitcher_options, index=0 if existing_pitchers else len(pitcher_options)-1)
    
    if selected_pitcher_option == "➕ Add New Reliever/Pitcher":
        current_our_pitcher = st.sidebar.text_input("Enter Reliever Name", value="Reliever 1")
    else:
        current_our_pitcher = selected_pitcher_option

    with st.form("pitch_form", clear_on_submit=True):
        st.write(f"**Logging pitches for:** `{current_our_pitcher}`")
        col1, col2 = st.columns(2)
        with col1:
            count = st.selectbox("Count (Balls-Strikes)", ["0-0", "1-0", "0-1", "1-1", "2-0", "2-1", "3-0", "3-1", "3-2", "0-2", "1-2", "2-2"])
            pitch_type = st.selectbox("Pitch Type", ["Fastball", "Slider", "Curveball", "Changeup", "Splitter", "Sinker"])
        with col2:
            result = st.selectbox("Result", ["Called Strike", "Swinging Strike", "Ball", "Foul", "In Play", "Hit By Pitch"])
            
        st.markdown("---")
        st.write("**If Ball In Play:**")
        col3, col4 = st.columns(2)
        with col3:
            contact_type = st.selectbox("Contact Type", ["N/A", "Ground Ball (GB)", "Fly Ball (FB)", "Line Drive (LD)", "Pop Up (PU)"])
        with col4:
            hit_type = st.selectbox("Hit Outcome", ["N/A", "Out", "Single", "Double", "Triple", "Home Run"])
            
        submitted = st.form_submit_button("Log Pitch")
        
        if submitted:
            try:
                supabase.table("pitch_logs").insert({
                    "mode": mode,
                    "pitcher": current_our_pitcher,
                    "batter": "N/A",
                    "count": count,
                    "pitch_type": pitch_type,
                    "result": result,
                    "contact_type": contact_type if result == "In Play" else "N/A",
                    "hit_type": hit_type if result == "In Play" else "N/A"
                }).execute()
                st.success(f"Logged {pitch_type} for {current_our_pitcher}!")
                st.rerun()
            except Exception as e:
                st.error(f"Error logging pitch: {e}")

    st.markdown("---")
    st.subheader("📈 Live Outing Stats & Advanced Analytics")
    
    if not df.empty and "pitcher" in df.columns:
        our_df = df[df["mode"] == "Our Pitcher Tracker"]
        if not our_df.empty:
            selected_view_pitcher = st.selectbox("Select Pitcher to View", our_df["pitcher"].unique())
            pitcher_df = our_df[our_df["pitcher"] == selected_view_pitcher]
            
            st.metric("Total Pitches Thrown", len(pitcher_df))
            
            if len(pitcher_df) > 0:
                col_a, col_b = st.columns(2)
                
                with col_a:
                    st.write("### Overall Pitch Mix")
                    mix = pitcher_df["pitch_type"].value_counts(normalize=True) * 100
                    st.dataframe(mix.round(1).astype(str) + '%')
                    
                with col_b:
                    st.write("### 🎯 0-0 Pitch Usage")
                    zero_zero = pitcher_df[pitcher_df["count"] == "0-0"]
                    if not zero_zero.empty:
                        zz_mix = zero_zero["pitch_type"].value_counts(normalize=True) * 100
                        st.dataframe(zz_mix.round(1).astype(str) + '%')
                    else:
                        st.info("No 0-0 pitches logged yet.")

                st.write("### 🚨 2-Strike Putaway Tendencies (0-2, 1-2, 2-2, 3-2)")
                two_strike_df = pitcher_df[pitcher_df["count"].isin(["0-2", "1-2", "2-2", "3-2"])]
                if not two_strike_df.empty:
                    ts_mix = two_strike_df["pitch_type"].value_counts(normalize=True) * 100
                    st.dataframe(ts_mix.round(1).astype(str) + '%')
                else:
                    st.info("No 2-strike counts logged yet.")

                st.write("### 📊 Batted Ball Profile (In Play)")
                in_play_df = pitcher_df[pitcher_df["result"] == "In Play"]
                if not in_play_df.empty:
                    c_col1, c_col2 = st.columns(2)
                    with c_col1:
                        st.write("**Contact Types**")
                        st.dataframe(in_play_df["contact_type"].value_counts())
                    with c_col2:
                        st.write("**Hit Outcomes**")
                        st.dataframe(in_play_df["hit_type"].value_counts())
                else:
                    st.info("No balls in play logged yet.")
        else:
            st.info("No pitches logged for our pitchers yet.")
    else:
        st.info("No pitch data logged yet today.")

else:
    st.header("🎯 Opponent Pitcher Scout")
    
    st.sidebar.markdown("---")

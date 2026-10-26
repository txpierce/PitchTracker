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
default_lineup = "Kai Anderson\nJames Doyle\nJackson Hodge\nJake Irwin\nFinley Kayes\nDrake Olson\nCade Pilcik\nSebastian Rojas\nCarson Skuddy\nGael Zambrano"
lineup_input = st.sidebar.text_area("Our Batting Lineup (One per line)", value=default_lineup, height=150)
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
    
    # Persistent Pitcher Selection in Sidebar or Top
    st.sidebar.markdown("---")
    st.sidebar.header("⚙️ Active Pitcher Control")
    current_our_pitcher = st.sidebar.text_input("Active Pitcher Name", value="Starting Pitcher")
    
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
            selected_pitcher = st.selectbox("Select Pitcher to View", our_df["pitcher"].unique())
            pitcher_df = our_df[our_df["pitcher"] == selected_pitcher]
            
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
    st.sidebar.header("⚙️ Active Opponent Pitcher")
    current_opp_pitcher = st.sidebar.text_input("Opponent Pitcher Name / #", value="Opponent Starter")
    
    with st.form("scout_form", clear_on_submit=True):
        st.write(f"**Charting against opponent pitcher:** `{current_opp_pitcher}`")
        
        current_batter = st.selectbox("Current Hitter At Bat", batters_list)
        
        col1, col2 = st.columns(2)
        with col1:
            count = st.selectbox("Count (Balls-Strikes)", ["0-0", "1-0", "0-1", "1-1", "2-0", "2-1", "3-0", "3-1", "3-2", "0-2", "1-2", "2-2"], key="opp_count")
            pitch_type = st.selectbox("Pitch Type", ["Fastball", "Slider", "Curveball", "Changeup", "Splitter", "Sinker"], key="opp_type")
        with col2:
            result = st.selectbox("Result", ["Called Strike", "Swinging Strike", "Ball", "Foul", "In Play", "Hit By Pitch"], key="opp_result")
            
        st.markdown("---")
        st.write("**If Ball In Play:**")
        col3, col4 = st.columns(2)
        with col3:
            contact_type = st.selectbox("Contact Type", ["N/A", "Ground Ball (GB)", "Fly Ball (FB)", "Line Drive (LD)", "Pop Up (PU)"], key="opp_contact")
        with col4:
            hit_type = st.selectbox("Hit Outcome", ["N/A", "Out", "Single", "Double", "Triple", "Home Run"], key="opp_hit")
            
        submitted = st.form_submit_button("Log Opponent Pitch")
        
        if submitted:
            try:
                supabase.table("pitch_logs").insert({
                    "mode": mode,
                    "pitcher": current_opp_pitcher,
                    "batter": current_batter,
                    "count": count,
                    "pitch_type": pitch_type,
                    "result": result,
                    "contact_type": contact_type if result == "In Play" else "N/A",
                    "hit_type": hit_type if result == "In Play" else "N/A"
                }).execute()
                st.success(f"Logged pitch to {current_batter}!")
                st.rerun()
            except Exception as e:
                st.error(f"Error logging pitch: {e}")

    st.markdown("---")
    st.subheader("💡 Instant Hitter Cheat Sheet & Matchup Breakdown")
    
    if not df.empty and "mode" in df.columns:
        opp_df = df[df["mode"] == "Opponent Pitcher Scout"]
        opp_df = opp_df.sort_values(by="timestamp", ascending=True)
        
        if not opp_df.empty:
            selected_opp = st.selectbox("Select Opponent Pitcher", opp_df["pitcher"].unique())
            opp_pitcher_df = opp_df[opp_df["pitcher"] == selected_opp]
            
            st.metric("Total Pitches Charted", len(opp_pitcher_df))
            
            col_x, col_y = st.columns(2)
            with col_x:
                st.write("### Overall Pitch Mix")
                st.dataframe((opp_pitcher_df["pitch_type"].value_counts(normalize=True) * 100).round(1).astype(str) + '%')
            with col_y:
                st.write("### 🎯 0-0 Pitch Usage")
                opp_zz = opp_pitcher_df[opp_pitcher_df["count"] == "0-0"]
                if not opp_zz.empty:
                    st.dataframe((opp_zz["pitch_type"].value_counts(normalize=True) * 100).round(1).astype(str) + '%')
                else:
                    st.info("No 0-0 pitches logged.")
            
            st.write("### 🚨 2-Strike Putaway Tendencies")
            opp_ts = opp_pitcher_df[opp_pitcher_df["count"].isin(["0-2", "1-2", "2-2", "3-2"])]
            if not opp_ts.empty:
                st.dataframe((opp_ts["pitch_type"].value_counts(normalize=True) * 100).round(1).astype(str) + '%')
            else:
                st.info("No 2-strike counts logged yet.")

            # Hitter Breakdown
            if "batter" in opp_pitcher_df.columns:
                st.write("### 🧢 Batter Breakdown vs This Pitcher")
                valid_batters = [b for b in opp_pitcher_df["batter"].unique() if b != "N/A"]
                if valid_batters:
                    selected_batter_view = st.selectbox("Select Hitter to Review", valid_batters)
                    batter_vs_df = opp_pitcher_df[opp_pitcher_df["batter"] == selected_batter_view]
                    st.metric(f"Pitches Seen by {selected_batter_view}", len(batter_vs_df))
                    st.dataframe(batter_vs_df[["count", "pitch_type", "result", "contact_type", "hit_type"]])
                else:
                    st.info("No individual batter matchups logged yet.")

            st.write("### 🔄 Sequential Pattern Recognition")
            opp_pitcher_df = opp_pitcher_df.copy()
            opp_pitcher_df["next_pitch"] = opp_pitcher_df["pitch_type"].shift(-1)
            opp_pitcher_df["next_result"] = opp_pitcher_df["result"].shift(-1)
            
            fb_calls = opp_pitcher_df[(opp_pitcher_df["pitch_type"] == "Fastball") & (opp_pitcher_df["result"].isin(["Called Strike", "Swinging Strike", "Foul"]))]
            
            if not fb_calls.empty:
                selected_trigger = st.selectbox("Select Fastball Previous Outcome", fb_calls["result"].unique())
                triggered_seq = fb_calls[fb_calls["result"] == selected_trigger]
                
                if not triggered_seq.empty and "next_pitch" in triggered_seq.columns:
                    st.write(f"**Follow-up pitch after Fastball -> {selected_trigger}:**")
                    seq_mix = triggered_seq["next_pitch"].value_counts(normalize=True) * 100
                    st.dataframe(seq_mix.round(1).astype(str) + '%')
                else:
                    st.info("Not enough sequential data logged yet for this pattern.")
            else:
                st.info("Log more fastball outcomes to unlock sequence tracking.")
        else:
            st.info("No opponent pitches charted yet.")
    else:
        st.info("No pitch data logged yet.")

# Sidebar Reset Button
st.sidebar.markdown("---")
st.sidebar.subheader("Game Management")
if st.sidebar.button("🗑️ Clear Game Data / Result"):
    try:
        supabase.table("pitch_logs").delete().neq("id", 0).execute()
        st.sidebar.success("Game data cleared successfully!")
        st.rerun()
    except Exception as e:
        st.sidebar.error(f"Error clearing data: {e}")

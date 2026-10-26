import streamlit as st
import pandas as pd
from supabase import create_client
import time

# Page Config
st.set_page_config(page_title="TX_Pierce - Pitch Tracker", page_icon="⚾", layout="centered")

# Initialize Supabase Client using Streamlit Secrets
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.title("⚾ TX_Pierce Pitch Tracker")

# Sidebar Mode Selection
st.sidebar.header("Navigation")
mode = st.sidebar.radio("Select Mode", [
    "Our Pitcher Tracker", 
    "Our Pitching Coach Dashboard", 
    "Opponent Pitcher Scout", 
    "Hitter On-Deck Cheat Sheet"
])

# --- DUAL LINEUP SETUP ---
st.sidebar.markdown("---")
st.sidebar.header("📋 Lineup Configurations")

# 1. Our Lineup (Used when charting Opponent Pitchers / On-Deck Cheat Sheet)
default_our_lineup = "Our Batter 1\nOur Batter 2\nOur Batter 3\nOur Batter 4\nOur Batter 5\nOur Batter 6\nOur Batter 7\nOur Batter 8\nOur Batter 9"
our_lineup_input = st.sidebar.text_area("Our Batting Lineup", value=default_our_lineup, height=120)
our_batters_list = [b.strip() for b in our_lineup_input.split("\n") if b.strip()]

# 2. Opponent Lineup (Used when tracking Our Pitchers)
default_opp_lineup = "Opponent Batter 1\nOpponent Batter 2\nOpponent Batter 3\nOpponent Batter 4\nOpponent Batter 5\nOpponent Batter 6\nOpponent Batter 7\nOpponent Batter 8\nOpponent Batter 9"
opp_lineup_input = st.sidebar.text_area("Opponent Batting Lineup", value=default_opp_lineup, height=120)
opp_batters_list = [b.strip() for b in opp_lineup_input.split("\n") if b.strip()]

# Initialize Session State for Counts & Lineup Indices Separately
if "our_pitcher_balls" not in st.session_state:
    st.session_state.our_pitcher_balls = 0
if "our_pitcher_strikes" not in st.session_state:
    st.session_state.our_pitcher_strikes = 0
if "our_pitcher_batter_index" not in st.session_state:
    st.session_state.our_pitcher_batter_index = 0

if "opp_scout_balls" not in st.session_state:
    st.session_state.opp_scout_balls = 0
if "opp_scout_strikes" not in st.session_state:
    st.session_state.opp_scout_strikes = 0
if "opp_scout_batter_index" not in st.session_state:
    st.session_state.opp_scout_batter_index = 0

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
    
    st.sidebar.markdown("---")
    st.sidebar.header("⚙️ Active Pitcher Control")
    
    existing_pitchers = []
    if not df.empty and "pitcher" in df.columns:
        existing_pitchers = list(df[df["mode"] == "Our Pitcher Tracker"]["pitcher"].unique())
    
    pitcher_options = existing_pitchers + ["➕ Add New Reliever/Pitcher"]
    selected_pitcher_option = st.sidebar.selectbox("Current Pitcher", pitcher_options, index=0 if existing_pitchers else len(pitcher_options)-1)
    
    if selected_pitcher_option == "➕ Add New Reliever/Pitcher":
        current_our_pitcher = st.sidebar.text_input("Enter Reliever Name", value="Reliever 1")
    else:
        current_our_pitcher = selected_pitcher_option

    # Manual Opponent Hitter Override for Our Pitcher Tracker
    st.sidebar.markdown("---")
    st.sidebar.header("🛠️ Scorekeeper Correction")
    if opp_batters_list:
        if st.session_state.our_pitcher_batter_index >= len(opp_batters_list):
            st.session_state.our_pitcher_batter_index = 0
            
        manual_override_opp = st.sidebar.selectbox(
            "Override Current Opponent Hitter", 
            opp_batters_list, 
            index=st.session_state.our_pitcher_batter_index,
            key="our_mode_hitter_override"
        )
        
        new_override_index = opp_batters_list.index(manual_override_opp)
        if new_override_index != st.session_state.our_pitcher_batter_index:
            st.session_state.our_pitcher_batter_index = new_override_index
            st.session_state.our_pitcher_balls = 0
            st.session_state.our_pitcher_strikes = 0

    current_batter = opp_batters_list[st.session_state.our_pitcher_batter_index] if opp_batters_list else "Opponent Batter 1"
    current_count_str = f"{st.session_state.our_pitcher_balls}-{st.session_state.our_pitcher_strikes}"
    
    st.info(f"⚾ **Facing Opponent Hitter:** `{current_batter}` | 🎯 **Current Count:** `{current_count_str}`")

    with st.form("our_pitch_form", clear_on_submit=False):
        st.write(f"**Logging pitches for our pitcher:** `{current_our_pitcher}`")
        col1, col2 = st.columns(2)
        with col1:
            pitch_type = st.selectbox("Pitch Type", ["Fastball", "Slider", "Curveball", "Changeup", "Splitter", "Sinker"], key="our_pitch_type")
        with col2:
            result = st.selectbox("Result", ["Called Strike", "Swinging Strike", "Ball", "Foul", "In Play", "Hit By Pitch"], key="our_result")
            
        st.markdown("---")
        st.write("**If Ball In Play:**")
        col3, col4 = st.columns(2)
        with col3:
            contact_type = st.selectbox("Contact Type", ["N/A", "Ground Ball (GB)", "Fly Ball (FB)", "Line Drive (LD)", "Pop Up (PU)"], key="our_contact")
        with col4:
            hit_type = st.selectbox("Hit Outcome", ["N/A", "Out", "Single", "Double", "Triple", "Home Run"], key="our_hit")
            
        btn_col1, btn_col2 = st.columns(2)
        with btn_col1:
            submitted = st.form_submit_button("Log Pitch & Advance Count")
        with btn_col2:
            complete_at_bat = st.form_submit_button("Complete At-Bat & Next Hitter ➔")
            
        if submitted or complete_at_bat:
            try:
                supabase.table("pitch_logs").insert({
                    "mode": "Our Pitcher Tracker",
                    "pitcher": current_our_pitcher,
                    "batter": current_batter,
                    "count": current_count_str,
                    "pitch_type": pitch_type,
                    "result": result,
                    "contact_type": contact_type if result == "In Play" else "N/A",
                    "hit_type": hit_type if result == "In Play" else "N/A"
                }).execute()
                
                if complete_at_bat:
                    st.session_state.our_pitcher_balls = 0
                    st.session_state.our_pitcher_strikes = 0
                    st.session_state.our_pitcher_batter_index = (st.session_state.our_pitcher_batter_index + 1) % len(opp_batters_list)
                    st.success(f"At-bat complete for {current_batter}! Advanced to next hitter.")
                else:
                    if result in ["Called Strike", "Swinging Strike"]:
                        if st.session_state.our_pitcher_strikes < 2:
                            st.session_state.our_pitcher_strikes += 1
                    elif result == "Ball":
                        if st.session_state.our_pitcher_balls < 3:
                            st.session_state.our_pitcher_balls += 1
                    elif result == "Foul":
                        if st.session_state.our_pitcher_strikes < 2:
                            st.session_state.our_pitcher_strikes += 1
                    elif result in ["In Play", "Hit By Pitch"]:
                        st.session_state.our_pitcher_balls = 0
                        st.session_state.our_pitcher_strikes = 0
                        st.session_state.our_pitcher_batter_index = (st.session_state.our_pitcher_batter_index + 1) % len(opp_batters_list)
                        
                    st.success(f"Logged {pitch_type} ({result}). Count is now {st.session_state.our_pitcher_balls}-{st.session_state.our_pitcher_strikes}")
                
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Error logging pitch: {e}")

    # Undo Last Pitch Button
    if st.button("↩️ Undo Last Logged Pitch (Our Tracker)"):
        try:
            recent_res = supabase.table("pitch_logs").select("id").eq("mode", "Our Pitcher Tracker").order("timestamp", desc=True).limit(1).execute()
            if recent_res.data:
                last_id = recent_res.data[0]["id"]
                supabase.table("pitch_logs").delete().eq("id", last_id).execute()
                st.cache_data.clear()
                st.success("Successfully deleted the last logged pitch!")
                st.rerun()
            else:
                st.warning("No pitches to undo.")
        except Exception as e:
            st.error(f"Error undoing pitch: {e}")

    st.markdown("---")
    st.subheader("📈 Live Outing Stats & Advanced Analytics")
    
    if not df.empty and "pitcher" in df.columns:
        our_df = df[df["mode"] == "Our Pitcher Tracker"]
        if not our_df.empty:
            selected_view_pitcher = st.selectbox("Select Pitcher to View", our_df["pitcher"].unique(), key="view_our_pitcher")
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

                st.write("### 📊 Pitch Type % Breakdown by Count")
                if not pitcher_df.empty:
                    count_pitch_table = pd.crosstab(pitcher_df["count"], pitcher_df["pitch_type"], normalize="index") * 100
                    st.dataframe(count_pitch_table.round(1).astype(str) + '%')
                else:
                    st.info("No pitch data logged yet.")

                st.write("### 📊 Batted Ball Profile & Pitch Breakdown")
                in_play_df = pitcher_df[pitcher_df["contact_type"] != "N/A"]
                if not in_play_df.empty:
                    c_col1, c_col2 = st.columns(2)
                    with c_col1:
                        st.write("**Contact Types (% by Pitch Type)**")
                        contact_table = pd.crosstab(in_play_df["pitch_type"], in_play_df["contact_type"], normalize="index") * 100
                        st.dataframe(contact_table.round(1).astype(str) + '%')
                    with c_col2:
                        st.write("**Hit Outcomes (% by Pitch Type)**")
                        hit_table = pd.crosstab(in_play_df["pitch_type"], in_play_df["hit_type"], normalize="index") * 100
                        st.dataframe(hit_table.round(1).astype(str) + '%')
                else:
                    st.info("No balls in play logged yet.")
        else:
            st.info("No pitches logged for our pitchers yet.")
    else:
        st.info("No pitch data logged yet today.")

elif mode == "Our Pitching Coach Dashboard":
    st.header("📋 Our Pitching Coach Dashboard")
    st.write("Real-time data and matchup breakdown for our pitching staff.")
    
    auto_refresh_coach = st.checkbox("🔄 Auto-Refresh Screen (Every 5 Seconds)", value=False, key="coach_refresh")
    
    if not df.empty and "mode" in df.columns:
        our_df = df[df["mode"] == "Our Pitcher Tracker"]
        if not our_df.empty:
            coach_opp = st.selectbox("Select Our Pitcher to Review", our_df["pitcher"].unique(), key="coach_pitcher_select")
            coach_pitcher_df = our_df[our_df["pitcher"] == coach_opp]
            
            st.metric("Total Pitches Thrown", len(coach_pitcher_df))
            
            col_x, col_y = st.columns(2)
            with col_x:
                st.write("### Overall Pitch Mix")
                st.dataframe((coach_pitcher_df["pitch_type"].value_counts(normalize=True) * 100).round(1).astype(str) + '%')
            with col_y:
                st.write("### 🎯 0-0 Pitch Usage")
                coach_zz = coach_pitcher_df[coach_pitcher_df["count"] == "0-0"]
                if not coach_zz.empty:
                    st.dataframe((coach_zz["pitch_type"].value_counts(normalize=True) * 100).round(1).astype(str) + '%')
                else:
                    st.info("No 0-0 pitches logged.")
            
            st.write("### 🚨 2-Strike Putaway Tendencies")
            coach_ts = coach_pitcher_df[coach_pitcher_df["count"].isin(["0-2", "1-2", "2-2", "3-2"])]
            if not coach_ts.empty:
                st.dataframe((coach_ts["pitch_type"].value_counts(normalize=True) * 100).round(1).astype(str) + '%')
            else:
                st.info("No 2-strike counts logged yet.")

            st.write("### 📊 Pitch Type % Breakdown by Count")
            if not coach_pitcher_df.empty:
                coach_count_table = pd.crosstab(coach_pitcher_df["count"], coach_pitcher_df["pitch_type"], normalize="index") * 100
                st.dataframe(coach_count_table.round(1).astype(str) + '%')
            else:
                st.info("No pitch data logged yet.")

            if "batter" in coach_pitcher_df.columns:
                st.write("### 🧢 Opponent Batter Breakdown vs This Pitcher")
                valid_batters = [b for b in coach_pitcher_df["batter"].unique() if b != "N/A"]
                if valid_batters:
                    coach_batter = st.selectbox("Toggle / Select Opponent Hitter", valid_batters, key="coach_batter_select")
                    batter_vs_df = coach_pitcher_df[coach_pitcher_df["batter"] == coach_batter]
                    
                    st.metric(f"Total Pitches Seen by {coach_batter}", len(batter_vs_df))
                    
                    if not batter_vs_df.empty:
                        st.write("**Pitch Type % Breakdown by Count**")
                        count_pitch_table = pd.crosstab(batter_vs_df["count"], batter_vs_df["pitch_type"], normalize="index") * 100
                        st.dataframe(count_pitch_table.round(1).astype(str) + '%')
                    else:
                        st.info("No pitches logged for this hitter yet.")
                else:
                    st.info("No individual batter matchups logged yet.")
            else:
                st.info("Batter tracking column not found.")

            st.write("### 🔄 Sequential Pattern Recognition")
            coach_seq_df = coach_pitcher_df.copy()
            coach_seq_df["next_pitch"] = coach_seq_df["pitch_type"].shift(-1)
            coach_seq_df["next_result"] = coach_seq_df["result"].shift(-1)
            
            coach_fb_calls = coach_seq_df[(coach_seq_df["pitch_type"] == "Fastball") & (coach_seq_df["result"].isin(["Called Strike", "Swinging Strike", "Foul"]))]
            
            if not coach_fb_calls.empty:
                coach_selected_trigger = st.selectbox("Select Fastball Previous Outcome", coach_fb_calls["result"].unique(), key="coach_seq_trigger")
                coach_triggered_seq = coach_fb_calls[coach_fb_calls["result"] == coach_selected_trigger]
                
                if not coach_triggered_seq.empty and "next_pitch" in coach_triggered_seq.columns:
                    st.write(f"**Follow-up pitch after Fastball -> {coach_selected_trigger}:**")
                    coach_seq_mix = coach_triggered_seq["next_pitch"].value_counts(normalize=True) * 100
                    st.dataframe(coach_seq_mix.round(1).astype(str) + '%')
                else:
                    st.info("Not enough sequential data logged yet for this pattern.")
            else:
                st.info("Log more fastball outcomes to unlock sequence tracking.")
        else:
            st.info("No pitches logged for our pitchers yet.")
    else:
        st.info("No pitch data logged yet today.")
        
    if auto_refresh_coach:
        time.sleep(5)
        st.cache_data.clear()
        st.rerun()

elif mode == "Opponent Pitcher Scout":
    st.header("🎯 Opponent Pitcher Scout")
    
    st.sidebar.markdown("---")
    st.sidebar.header("⚙️ Active Opponent Pitcher")
    
    existing_opps = []
    if not df.empty and "mode" in df.columns:
        existing_opps = list(df[df["mode"] == "Opponent Pitcher Scout"]["pitcher"].unique())
        
    opp_options = existing_opps + ["➕ Add New Opponent Pitcher"]
    selected_opp_option = st.sidebar.selectbox("Opponent Pitcher", opp_options, index=0 if existing_opps else len(opp_options)-1, key="opp_select_side")
    
    if selected_opp_option == "➕ Add New Opponent Pitcher":
        current_opp_pitcher = st.sidebar.text_input("Enter Opponent Pitcher Name / #", value="Opponent Reliever")
    else:
        current_opp_pitcher = selected_opp_option

    # Opponent Scout Manual Hitter Override (uses Our Lineup)
    st.sidebar.markdown("---")
    st.sidebar.header("🛠️ Scorekeeper Correction")
    if our_batters_list:
        if st.session_state.opp_scout_batter_index >= len(our_batters_list):
            st.session_state.opp_scout_batter_index = 0
            
        manual_override_our = st.sidebar.selectbox(
            "Override Current Our Hitter", 
            our_batters_list, 
            index=st.session_state.opp_scout_batter_index,
            key="opp_scout_hitter_override"
        )
        
        new_override_index = our_batters_list.index(manual_override_our)
        if new_override_index != st.session_state.opp_scout_batter_index:
            st.session_state.opp_scout_batter_index = new_override_index
            st.session_state.opp_scout_balls = 0
            st.session_state.opp_scout_strikes = 0

    current_batter = our_batters_list[st.session_state.opp_scout_batter_index] if our_batters_list else "Our Batter 1"
    current_count_str = f"{st.session_state.opp_scout_balls}-{st.session_state.opp_scout_strikes}"
    
    st.info(f"⚾ **Current Our Hitter:** `{current_batter}` | 🎯 **Current Count:** `{current_count_str}`")

    with st.form("scout_form", clear_on_submit=False):
        st.write(f"**Charting against opponent pitcher:** `{current_opp_pitcher}`")
        
        col1, col2 = st.columns(2)
        with col1:
            pitch_type = st.selectbox("Pitch Type", ["Fastball", "Slider", "Curveball", "Changeup", "Splitter", "Sinker"], key="scout_type")
        with col2:
            result = st.selectbox("Result", ["Called Strike", "Swinging Strike", "Ball", "Foul", "In Play", "Hit By Pitch"], key="scout_result")
            
        st.markdown("---")
        st.write("**If Ball In Play:**")
        col3, col4 = st.columns(2)
        with col3:
            contact_type = st.selectbox("Contact Type", ["N/A", "Ground Ball (GB)", "Fly Ball (FB)", "Line Drive (LD)", "Pop Up (PU)"], key="scout_contact")
        with col4:
            hit_type = st.selectbox("Hit Outcome", ["N/A", "Out", "Single", "Double", "Triple", "Home Run"], key="scout_hit")
            
        btn_col1, btn_col2 = st.columns(2)
        with btn_col1:
            submitted = st.form_submit_button("Log Pitch & Advance Count")
        with btn_col2:
            complete_at_bat = st.form_submit_button("Complete At-Bat & Next Hitter ➔")
            
        if submitted or complete_at_bat:
            try:
                supabase.table("pitch_logs").insert({
                    "mode": "Opponent Pitcher Scout",
                    "pitcher": current_opp_pitcher,
                    "batter": current_batter,
                    "count": current_count_str,
                    "pitch_type": pitch_type,
                    "result": result,
                    "contact_type": contact_type if result == "In Play" else "N/A",
                    "hit_type": hit_type if result == "In Play" else "N/A"
                }).execute()
                
                if complete_at_bat:
                    st.session_state.opp_scout_balls = 0
                    st.session_state.opp_scout_strikes = 0
                    st.session_state.opp_scout_batter_index = (st.session_state.opp_scout_batter_index + 1) % len(our_batters_list)
                    st.success(f"At-bat complete for {current_batter}! Advanced to next hitter.")
                else:
                    if result in ["Called Strike", "Swinging Strike"]:
                        if st.session_state.opp_scout_strikes < 2:
                            st.session_state.opp_scout_strikes += 1
                    elif result == "Ball":
                        if st.session_state.opp_scout_balls < 3:
                            st.session_state.opp_scout_balls += 1
                    elif result == "Foul":
                        if st.session_state.opp_scout_strikes < 2:
                            st.session_state.opp_scout_strikes += 1
                    elif result in ["In Play", "Hit By Pitch"]:
                        st.session_state.opp_scout_balls = 0
                        st.session_state.opp_scout_strikes = 0
                        st.session_state.opp_scout_batter_index = (st.session_state.opp_scout_batter_index + 1) % len(our_batters_list)
                        
                    st.success(f"Logged {pitch_type} ({result}). Count is now {st.session_state.opp_scout_balls}-{st.session_state.opp_scout_strikes}")
                
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Error logging pitch: {e}")

    # Undo Last Pitch Button for Opponent Scout
    if st.button("↩️ Undo Last Logged Pitch (Opponent Scout)"):
        try:
            recent_res = supabase.table("pitch_logs").select("id").eq("mode", "Opponent Pitcher Scout").order("timestamp", desc=True).limit(1).execute()
            if recent_res.data:
                last_id = recent_res.data[0]["id"]
                supabase.table("pitch_logs").delete().eq("id", last_id).execute()
                st.cache_data.clear()
                st.success("Successfully deleted the last logged pitch!")
                st.rerun()
            else:
                st.warning("No pitches to undo.")
        except Exception as e:
            st.error(f"Error undoing pitch: {e}")

    st.markdown("---")
    st.subheader("💡 Instant Hitter Cheat Sheet & Matchup Breakdown")
    
    if not df.empty and "mode" in df.columns:
        opp_df = df[df["mode"] == "Opponent Pitcher Scout"]
        opp_df = opp_df.sort_values(by="timestamp", ascending=True)
        
        if not opp_df.empty:
            selected_opp = st.selectbox("Select Opponent Pitcher to View", opp_df["pitcher"].unique(), key="view_opp_pitcher")
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

            st.write("### 🔄 Sequential Pattern Recognition")
            opp_pitcher_df = opp_pitcher_df.copy()
            opp_pitcher_df["next_pitch"] = opp_pitcher_df["pitch_type"].shift(-1)
            opp_pitcher_df["next_result"] = opp_pitcher_df["result"].shift(-1)
            
            fb_calls = opp_pitcher_df[(opp_pitcher_df["pitch_type"] == "Fastball") & (opp_pitcher_df["result"].isin(["Called Strike", "Swinging Strike", "Foul"]))]
            
            if not fb_calls.empty:
                selected_trigger = st.selectbox("Select Fastball Previous Outcome", fb_calls["result"].unique(), key="seq_trigger")
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

else:
    st.header("🧢 Hitter On-Deck Cheat Sheet")
    st.write("Dedicated view for hitters to review full opponent pitcher scouting and count breakdowns[cite: 5].")
    
    auto_refresh = st.checkbox("🔄 Auto-Refresh Screen (Every 5 Seconds)", value=False)
    
    if not df.empty and "mode" in df.columns:
        opp_df = df[df["mode"] == "Opponent Pitcher Scout"]
        if not opp_df.empty:
            deck_opp = st.selectbox("Select Current Opponent Pitcher", opp_df["pitcher"].unique(), key="deck_opp_select")
            deck_pitcher_df = opp_df[opp_df["pitcher"] == deck_opp]
            
            st.metric("Total Pitches Charted", len(deck_pitcher_df))
            
            col_x, col_y = st.columns(2)
            with col_x:
                st.write("### Overall Pitch Mix")
                st.dataframe((deck_pitcher_df["pitch_type"].value_counts(normalize=True) * 100).round(1).astype(str) + '%')
            with col_y:
                st.write("### 🎯 0-0 Pitch Usage")
                deck_zz = deck_pitcher_df[deck_pitcher_df["count"] == "0-0"]
                if not deck_zz.empty:
                    st.dataframe((deck_zz["pitch_type"].value_counts(normalize=True) * 100).round(1).astype(str) + '%')
                else:
                    st.info("No 0-0 pitches logged.")
            
            st.write("### 🚨 2-Strike Putaway Tendencies")
            deck_ts = deck_pitcher_df[deck_pitcher_df["count"].isin(["0-2", "1-2", "2-2", "3-2"])]
            if not deck_ts.empty:
                st.dataframe((deck_ts["pitch_type"].value_counts(normalize=True) * 100).round(1).astype(str) + '%')
            else:
                st.info("No 2-strike counts logged yet.")

            if "batter" in deck_pitcher_df.columns:
                st.write("### 🧢 Batter Breakdown vs This Pitcher")
                valid_batters = [b for b in deck_pitcher_df["batter"].unique() if b != "N/A"]
                if valid_batters:
                    deck_batter = st.selectbox("Select Hitter to Review", valid_batters, key="deck_batter_select")
                    batter_vs_df = deck_pitcher_df[deck_pitcher_df["batter"] == deck_batter]
                    
                    st.metric(f"Total Pitches Seen by {deck_batter}", len(batter_vs_df))
                    
                    if not batter_vs_df.empty:
                        st.write("**Pitch Type % Breakdown by Count**")
                        count_pitch_table = pd.crosstab(batter_vs_df["count"], batter_vs_df["pitch_type"], normalize="index") * 100
                        st.dataframe(count_pitch_table.round(1).astype(str) + '%')
                    else:
                        st.info("No pitches logged for this hitter against this pitcher yet.")
                else:
                    st.info("No individual batter matchups logged yet.")
            else:
                st.info("Batter tracking column not found.")

            st.write("### 🔄 Sequential Pattern Recognition")
            deck_seq_df = deck_pitcher_df.copy()
            deck_seq_df["next_pitch"] = deck_seq_df["pitch_type"].shift(-1)
            deck_seq_df["next_result"] = deck_seq_df["result"].shift(-1)
            
            deck_fb_calls = deck_seq_df[(deck_seq_df["pitch_type"] == "Fastball") & (deck_seq_df["result"].isin(["Called Strike", "Swinging Strike", "Foul"]))]
            
            if not deck_fb_calls.empty:
                deck_selected_trigger = st.selectbox("Select Fastball Previous Outcome", deck_fb_calls["result"].unique(), key="deck_seq_trigger")
                deck_triggered_seq = deck_fb_calls[deck_fb_calls["result"] == deck_selected_trigger]
                
                if not deck_triggered_seq.empty and "next_pitch" in deck_triggered_seq.columns:
                    st.write(f"**Follow-up pitch after Fastball -> {deck_selected_trigger}:**")
                    deck_seq_mix = deck_triggered_seq["next_pitch"].value_counts(normalize=True) * 100
                    st.dataframe(deck_seq_mix.round(1).astype(str) + '%')
                else:
                    st.info("Not enough sequential data logged yet for this pattern.")
            else:
                st.info("Log more fastball outcomes to unlock sequence tracking.")
        else:
            st.info("No opponent pitches charted yet.")
    else:
        st.info("No pitch data logged yet today.")
        
    if auto_refresh:
        time.sleep(5)
        st.cache_data.clear()
        st.rerun()

# Sidebar Reset Button
st.sidebar.markdown("---")
st.sidebar.subheader("Game Management")
if st.sidebar.button("🗑️ Clear Game Data / Reset"):
    try:
        supabase.table("pitch_logs").delete().neq("id", 0).execute()
        st.session_state.our_pitcher_balls = 0
        st.session_state.our_pitcher_strikes = 0
        st.session_state.our_pitcher_batter_index = 0
        st.session_state.opp_scout_balls = 0
        st.session_state.opp_scout_strikes = 0
        st.session_state.opp_scout_batter_index = 0
        st.sidebar.success("Game data cleared successfully!")
        st.rerun()
    except Exception as e:
        st.sidebar.error(f"Error clearing data: {e}")

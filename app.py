import streamlit as st
import pandas as pd
from supabase import create_client
import time
import plotly.express as px
import plotly.graph_objects as go

# Page Config
st.set_page_config(page_title="TX_Pierce - Pitch Tracker", page_icon="⚾", layout="centered")

# --- CUSTOM CSS FOR GLOWING EDGE HIGHLIGHTS & METRIC CARDS ---
st.markdown("""
<style>
.metric-card {
    background-color: #1e1e2f;
    border: 1px solid #2a2a40;
    border-radius: 12px;
    padding: 16px;
    text-align: center;
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    margin-bottom: 10px;
}
.metric-card h3 {
    color: #a0a0c0;
    font-size: 14px;
    margin-bottom: 4px;
}
.metric-card h2 {
    color: #ffffff;
    font-size: 26px;
    font-weight: 700;
}
.glow-bar-container {
    background-color: #2a2a40;
    border-radius: 8px;
    overflow: hidden;
    height: 12px;
    width: 100%;
    margin-bottom: 16px;
}
.glow-bar-fill {
    height: 100%;
    background: linear-gradient(90deg, #1c83e1, #00ccff);
    box-shadow: 0 0 10px #00ccff, 0 0 20px #1c83e1;
    border-radius: 8px;
}
</style>
""", unsafe_allow_html=True)

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
    "Hitter On-Deck Cheat Sheet",
    "Bullpen Charting"
])

# --- DUAL LINEUP SETUP ---
st.sidebar.markdown("---")
st.sidebar.header("📋 Lineup Configurations")

default_our_lineup = "Our Batter 1\nOur Batter 2\nOur Batter 3\nOur Batter 4\nOur Batter 5\nOur Batter 6\nOur Batter 7\nOur Batter 8\nOur Batter 9"
our_lineup_input = st.sidebar.text_area("Our Batting Lineup", value=default_our_lineup, height=120)
our_batters_list = [b.strip() for b in our_lineup_input.split("\n") if b.strip()]

default_opp_lineup = "Opponent Batter 1\nOpponent Batter 2\nOpponent Batter 3\nOpponent Batter 4\nOpponent Batter 5\nOpponent Batter 6\nOpponent Batter 7\nOpponent Batter 8\nOpponent Batter 9"
opp_lineup_input = st.sidebar.text_area("Opponent Batting Lineup", value=default_opp_lineup, height=120)
opp_batters_list = [b.strip() for b in opp_lineup_input.split("\n") if b.strip()]

# Initialize Session State
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

# Initialize Bullpen Click Coordinates in Session State if missing
if "bp_target_x" not in st.session_state:
    st.session_state.bp_target_x = 0.0
if "bp_target_y" not in st.session_state:
    st.session_state.bp_target_y = 2.0
if "bp_actual_x" not in st.session_state:
    st.session_state.bp_actual_x = 0.0
if "bp_actual_y" not in st.session_state:
    st.session_state.bp_actual_y = 2.0

# Fetch existing pitch logs from Supabase
@st.cache_data(ttl=2)
def load_data():
    try:
        response = supabase.table("pitch_logs").select("*").order("timestamp", desc=False).execute()
        return pd.DataFrame(response.data)
    except Exception as e:
        return pd.DataFrame()

df = load_data()

# --- HELPER: RENDER VISUAL BARS & GLOW CARDS ---
def render_glowing_bars(series, title_text="Pitch Distribution"):
    st.write(f"### {title_text}")
    if series.empty:
        st.info("No data available for visual breakdown.")
        return
    for pitch_type, pct in series.items():
        st.markdown(f"**{pitch_type}** ({pct:.1f}%)")
        st.markdown(f"""
        <div class="glow-bar-container">
            <div class="glow-bar-fill" style="width: {min(max(pct, 2), 100)}%;"></div>
        </div>
        """, unsafe_allow_html=True)

def render_glowing_metric_cards(series, title_text="0-0 Usage Breakdown"):
    st.write(f"### {title_text}")
    if series.empty:
        st.info("No data available.")
        return
    cols = st.columns(min(len(series), 3))
    for idx, (pitch_type, pct) in enumerate(series.items()):
        with cols[idx % len(cols)]:
            st.markdown(f"""
            <div class="metric-card">
                <h3>{pitch_type}</h3>
                <h2>{pct:.1f}%</h2>
            </div>
            """, unsafe_allow_html=True)

# --- MAIN APP MODES ---
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

    st.sidebar.markdown("---")
    st.sidebar.header("🛠️ Scorekeeper Correction")
    if opp_batters_list:
        if st.session_state.our_pitcher_batter_index >= len(opp_batters_list):
            st.session_state.our_pitcher_batter_index = 0
            
        manual_override_opp = st.sidebar.selectbox(
            "Override Current Opponent Hitter", 
            opp_batters_list, 
            index=st.session_state.our_pitcher_batter_index
        )
        
        new_override_index = opp_batters_list.index(manual_override_opp)
        if new_override_index != st.session_state.our_pitcher_batter_index:
            st.session_state.our_pitcher_batter_index = new_override_index
            st.session_state.our_pitcher_balls = 0
            st.session_state.our_pitcher_strikes = 0

    current_batter = opp_batters_list[st.session_state.our_pitcher_batter_index] if opp_batters_list else "Opponent Batter 1"
    current_count_str = f"{st.session_state.our_pitcher_balls}-{st.session_state.our_pitcher_strikes}"
    
    st.info(f"⚾ **Facing Opponent Hitter:** `{current_batter}` | 🎯 **Current Count:** `{current_count_str}`")

    with st.form("our_pitch_form", clear_on_submit=True):
        st.write(f"**Logging pitches for our pitcher:** `{current_our_pitcher}`")
        col1, col2 = st.columns(2)
        with col1:
            pitch_type = st.selectbox("Pitch Type", ["Fastball", "Slider", "Curveball", "Changeup", "Splitter", "Sinker"], key="our_pitch_type")
        with col2:
            result = st.selectbox("Result", [
                "Called Strike", "Swinging Strike", "Chase Swing & Miss", 
                "Chase Contact / Foul", "Ball", "Foul", "In Play", "Hit By Pitch"
            ], key="our_result")
            
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
                
                if complete_at_bat or result in ["In Play", "Hit By Pitch"]:
                    st.session_state.our_pitcher_balls = 0
                    st.session_state.our_pitcher_strikes = 0
                    st.session_state.our_pitcher_batter_index = (st.session_state.our_pitcher_batter_index + 1) % len(opp_batters_list)
                    st.success(f"At-bat complete for {current_batter}! Advanced to next hitter.")
                else:
                    if result in ["Called Strike", "Swinging Strike", "Chase Swing & Miss"]:
                        if st.session_state.our_pitcher_strikes < 2:
                            st.session_state.our_pitcher_strikes += 1
                    elif result == "Ball":
                        if st.session_state.our_pitcher_balls < 3:
                            st.session_state.our_pitcher_balls += 1
                    elif result in ["Foul", "Chase Contact / Foul"]:
                        if st.session_state.our_pitcher_strikes < 2:
                            st.session_state.our_pitcher_strikes += 1
                            
                    st.success(f"Logged {pitch_type} ({result}). Count is now {st.session_state.our_pitcher_balls}-{st.session_state.our_pitcher_strikes}")
                
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Error logging pitch: {e}")

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
                    mix = pitcher_df["pitch_type"].value_counts(normalize=True) * 100
                    render_glowing_bars(mix, title_text="📊 Overall Pitch Mix (Visual Bars)")
                with col_b:
                    zero_zero = pitcher_df[pitcher_df["count"] == "0-0"]
                    if not zero_zero.empty:
                        zz_mix = zero_zero["pitch_type"].value_counts(normalize=True) * 100
                        render_glowing_metric_cards(zz_mix, title_text="🎯 0-0 Pitch Usage")
                    else:
                        st.info("No 0-0 pitches logged yet.")

                ts_df = pitcher_df[pitcher_df["count"].isin(["0-2", "1-2", "2-2", "3-2"])]
                if not ts_df.empty:
                    ts_mix = ts_df["pitch_type"].value_counts(normalize=True) * 100
                    render_glowing_bars(ts_mix, title_text="🚨 2-Strike Putaway Bar Breakdown")
                else:
                    st.info("No 2-strike counts logged yet.")

                st.write("### 🎯 Advanced Metrics (Whiff %, Called Strike %, Total Strike %, Chase)")
                metrics_rows = []
                for p_type in pitcher_df["pitch_type"].unique():
                    p_sub = pitcher_df[pitcher_df["pitch_type"] == p_type]
                    total_p = len(p_sub)
                    called_strikes = len(p_sub[p_sub["result"] == "Called Strike"])
                    swinging_strikes = len(p_sub[p_sub["result"].isin(["Swinging Strike", "Chase Swing & Miss"])])
                    total_swings = len(p_sub[p_sub["result"].isin(["Swinging Strike", "Chase Swing & Miss", "Chase Contact / Foul", "Foul", "In Play"])])
                    chase_count = len(p_sub[p_sub["result"].isin(["Chase Swing & Miss", "Chase Contact / Foul"])])
                    total_strikes = len(p_sub[p_sub["result"].isin(["Called Strike", "Swinging Strike", "Chase Swing & Miss", "Chase Contact / Foul", "Foul", "In Play"])])
                    
                    cs_pct = (called_strikes / total_p * 100) if total_p > 0 else 0.0
                    whiff_pct = (swinging_strikes / total_swings * 100) if total_swings > 0 else 0.0
                    total_strike_pct = (total_strikes / total_p * 100) if total_p > 0 else 0.0
                    
                    metrics_rows.append({
                        "Pitch Type": p_type,
                        "Total Thrown": total_p,
                        "Called Strike %": f"{cs_pct:.1f}%",
                        "Whiff % (on Swings)": f"{whiff_pct:.1f}%",
                        "Total Strike %": f"{total_strike_pct:.1f}%",
                        "Chase Count": chase_count
                    })
                st.dataframe(pd.DataFrame(metrics_rows), hide_index=True)

                st.write("### 📊 Pitch Type % Breakdown by Count")
                st.dataframe(pd.crosstab(pitcher_df["count"], pitcher_df["pitch_type"], normalize="index").mul(100).round(1).astype(str) + '%')

                st.write("### 📊 Batted Ball Profile & Pitch Breakdown")
                in_play_df = pitcher_df[pitcher_df["contact_type"] != "N/A"]
                if not in_play_df.empty:
                    c1, c2 = st.columns(2)
                    with c1:
                        st.write("**Contact Types**")
                        st.dataframe(pd.crosstab(in_play_df["pitch_type"], in_play_df["contact_type"], normalize="index").mul(100).round(1).astype(str) + '%')
                    with c2:
                        st.write("**Hit Outcomes**")
                        st.dataframe(pd.crosstab(in_play_df["pitch_type"], in_play_df["hit_type"], normalize="index").mul(100).round(1).astype(str) + '%')
        else:
            st.info("No pitches logged for our pitchers yet.")

elif mode == "Our Pitching Coach Dashboard":
    st.header("📋 Our Pitching Coach Dashboard")
    st.write("Real-time visual diagnostic feedback, 1st-pitch strike percentages, 3-ball count frequency, and pitch mix realities for our pitching staff.")
    
    auto_refresh_coach = st.checkbox("🔄 Auto-Refresh Screen (Every 5 Seconds)", value=False, key="coach_refresh")
    
    if not df.empty and "mode" in df.columns:
        our_df = df[df["mode"] == "Our Pitcher Tracker"]
        if not our_df.empty:
            coach_opp = st.selectbox("Select Our Pitcher to Review", our_df["pitcher"].unique(), key="coach_pitcher_select")
            coach_pitcher_df = our_df[our_df["pitcher"] == coach_opp]
            
            total_pitches = len(coach_pitcher_df)
            st.metric("Total Pitches Thrown", total_pitches)
            
            col_m1, col_m2 = st.columns(2)
            
            with col_m1:
                fp_df = coach_pitcher_df[coach_pitcher_df["count"] == "0-0"]
                if not fp_df.empty:
                    fp_strikes = len(fp_df[fp_df["result"].isin(["Called Strike", "Swinging Strike", "Chase Swing & Miss", "Chase Contact / Foul", "Foul", "In Play"])])
                    fp_strike_pct = (fp_strikes / len(fp_df)) * 100
                    st.markdown(f"""
                    <div class="metric-card">
                        <h3>🎯 1st-Pitch Strike % (FPS%)</h3>
                        <h2>{fp_strike_pct:.1f}%</h2>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class="metric-card">
                        <h3>🎯 1st-Pitch Strike % (FPS%)</h3>
                        <h2>0.0%</h2>
                    </div>
                    """, unsafe_allow_html=True)

            with col_m2:
                three_ball_df = coach_pitcher_df[coach_pitcher_df["count"].isin(["3-0", "3-1", "3-2"])]
                three_ball_pct = (len(three_ball_df) / total_pitches * 100) if total_pitches > 0 else 0.0
                st.markdown(f"""
                <div class="metric-card">
                    <h3>⚠️ 3-Ball Count Frequency</h3>
                    <h2>{three_ball_pct:.1f}%</h2>
                </div>
                """, unsafe_allow_html=True)
            
            col_x, col_y = st.columns(2)
            with col_x:
                mix = coach_pitcher_df["pitch_type"].value_counts(normalize=True) * 100
                render_glowing_bars(mix, title_text="📊 Overall Pitch Mix (Visual Bars)")
            with col_y:
                coach_zz = coach_pitcher_df[coach_pitcher_df["count"] == "0-0"]
                if not coach_zz.empty:
                    render_glowing_metric_cards(coach_zz["pitch_type"].value_counts(normalize=True) * 100, title_text="🎯 0-0 Pitch Usage")
                else:
                    st.info("No 0-0 pitches logged.")
            
            coach_ts = coach_pitcher_df[coach_pitcher_df["count"].isin(["0-2", "1-2", "2-2", "3-2"])]
            if not coach_ts.empty:
                render_glowing_bars(coach_ts["pitch_type"].value_counts(normalize=True) * 100, title_text="🚨 2-Strike Putaway Bar Breakdown")
            else:
                st.info("No 2-strike counts logged yet.")

            st.write("### 🎯 Advanced Metrics (Whiff %, Called Strike %, Total Strike %, Chase)")
            metrics_rows = []
            for p_type in coach_pitcher_df["pitch_type"].unique():
                p_sub = coach_pitcher_df[coach_pitcher_df["pitch_type"] == p_type]
                total_p = len(p_sub)
                called_strikes = len(p_sub[p_sub["result"] == "Called Strike"])
                swinging_strikes = len(p_sub[p_sub["result"].isin(["Swinging Strike", "Chase Swing & Miss"])])
                total_swings = len(p_sub[p_sub["result"].isin(["Swinging Strike", "Chase Swing & Miss", "Chase Contact / Foul", "Foul", "In Play"])])
                chase_count = len(p_sub[p_sub["result"].isin(["Chase Swing & Miss", "Chase Contact / Foul"])])
                total_strikes = len(p_sub[p_sub["result"].isin(["Called Strike", "Swinging Strike", "Chase Swing & Miss", "Chase Contact / Foul", "Foul", "In Play"])])
                
                cs_pct = (called_strikes / total_p * 100) if total_p > 0 else 0.0
                whiff_pct = (swinging_strikes / total_swings * 100) if total_swings > 0 else 0.0
                total_strike_pct = (total_strikes / total_p * 100) if total_p > 0 else 0.0
                
                metrics_rows.append({
                    "Pitch Type": p_type,
                    "Total Thrown": total_p,
                    "Called Strike %": f"{cs_pct:.1f}%",
                    "Whiff % (on Swings)": f"{whiff_pct:.1f}%",
                    "Total Strike %": f"{total_strike_pct:.1f}%",
                    "Chase Count": chase_count
                })
            st.dataframe(pd.DataFrame(metrics_rows), hide_index=True)

            # --- INDIVIDUAL HITTER MATCHUP BREAKDOWN WITH SEPARATE TABLES PER PITCH ---
            st.markdown("---")
            st.subheader("👤 Individual Hitter Matchup & History Breakdown")
            
            logged_hitters = list(coach_pitcher_df["batter"].unique()) if "batter" in coach_pitcher_df.columns else []
            hitter_review_options = logged_hitters if logged_hitters else opp_batters_list
            
            if hitter_review_options:
                selected_review_hitter = st.selectbox("Select Opponent Hitter to Review Matchup", hitter_review_options, key="coach_hitter_review_select")
                hitter_matchup_df = coach_pitcher_df[coach_pitcher_df["batter"] == selected_review_hitter]
                
                if not hitter_matchup_df.empty:
                    st.metric(f"Total Pitches Thrown to {selected_review_hitter}", len(hitter_matchup_df))
                    
                    hc1, hc2 = st.columns(2)
                    with hc1:
                        st.write("**Pitch Types Thrown to Hitter**")
                        h_mix = hitter_matchup_df["pitch_type"].value_counts(normalize=True) * 100
                        render_glowing_bars(h_mix, title_text="Hitter Pitch Mix Faced")
                    with hc2:
                        st.write("**Result Breakdown by Pitch**")
                        
                    for pt in hitter_matchup_df["pitch_type"].unique():
                        pt_df = hitter_matchup_df[hitter_matchup_df["pitch_type"] == pt]
                        
                        take_strike = len(pt_df[pt_df["result"] == "Called Strike"])
                        take_ball = len(pt_df[pt_df["result"] == "Ball"])
                        chase_strike = len(pt_df[pt_df["result"].isin(["Swinging Strike", "Chase Swing & Miss", "Chase Contact / Foul"])])
                        foul_ball = len(pt_df[pt_df["result"].isin(["Foul"])])
                        put_in_play = len(pt_df[pt_df["result"] == "In Play"])
                        
                        single_pitch_df = pd.DataFrame([{
                            "Take for Strike": take_strike,
                            "Take for Ball": take_ball,
                            "Chase for Strike": chase_strike,
                            "Foul Ball": foul_ball,
                            "Put in Play": put_in_play
                        }])
                        
                        st.markdown(f"**📌 Pitch: {pt}** (Total: {len(pt_df)})")
                        st.dataframe(single_pitch_df, hide_index=True)
                    
                    st.write("**Detailed Pitch Log History vs. Hitter**")
                    st.dataframe(hitter_matchup_df[["timestamp", "count", "pitch_type", "result", "contact_type", "hit_type"]], hide_index=True)
                else:
                    st.info(f"No logged pitch data found for {selected_review_hitter} against {coach_opp}.")
            else:
                st.info("No opponent batters available for review.")

            st.markdown("---")
            st.markdown("### 🧠 Dugout Coach Feedback & Diagnostic Insights")
            if total_pitches >= 5:
                mix_full = coach_pitcher_df["pitch_type"].value_counts(normalize=True) * 100
                top_pitch = mix_full.idxmax()
                top_pct = mix_full.max()
                
                whiff_dict = {}
                for pt in coach_pitcher_df["pitch_type"].unique():
                    pt_sub = coach_pitcher_df[coach_pitcher_df["pitch_type"] == pt]
                    swings = len(pt_sub[pt_sub["result"].isin(["Swinging Strike", "Chase Swing & Miss", "Chase Contact / Foul", "Foul", "In Play"])])
                    sw_miss = len(pt_sub[pt_sub["result"].isin(["Swinging Strike", "Chase Swing & Miss"])])
                    whiff_dict[pt] = (sw_miss / swings * 100) if swings > 0 else 0.0
                
                best_whiff_pitch = max(whiff_dict, key=whiff_dict.get) if whiff_dict else top_pitch
                best_whiff_val = whiff_dict.get(best_whiff_pitch, 0.0)
                
                st.info(f"""
                * **Effective Velocity & Mix Realities:** `{coach_opp}` is leaning heavily on the `{top_pitch}` (`{top_pct:.1f}%` usage). 
                * **Whiff Opportunity Alert:** Your highest whiff-generating pitch is currently the `{best_whiff_pitch}` (`{best_whiff_val:.1f}%` whiff rate). Consider dialing up its frequency if hitters are sitting on the primary pitch.
                * **Leverage Check:** 3-ball counts currently represent `{three_ball_pct:.1f}%` of total pitches thrown. Watch for command leakage in deep counts.
                """)
            else:
                st.info("Log at least 5 pitches to unlock automated coaching recommendations.")
        else:
            st.info("No pitches logged for our pitchers yet.")
            
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

    st.sidebar.markdown("---")
    st.sidebar.header("🛠️ Scorekeeper Correction")
    if our_batters_list:
        if st.session_state.opp_scout_batter_index >= len(our_batters_list):
            st.session_state.opp_scout_batter_index = 0
            
        manual_override_our = st.sidebar.selectbox(
            "Override Current Our Hitter", 
            our_batters_list, 
            index=st.session_state.opp_scout_batter_index
        )
        
        selected_index_our = our_batters_list.index(manual_override_our)
        if selected_index_our != st.session_state.opp_scout_batter_index:
            st.session_state.opp_scout_batter_index = selected_index_our

    current_batter = our_batters_list[st.session_state.opp_scout_batter_index] if our_batters_list else "Our Batter 1"
    current_count_str = f"{st.session_state.opp_scout_balls}-{st.session_state.opp_scout_strikes}"
    
    st.info(f"⚾ **Current Our Hitter:** `{current_batter}` | 🎯 **Current Count:** `{current_count_str}`")

    with st.form("scout_form", clear_on_submit=True):
        st.write(f"**Charting against opponent pitcher:** `{current_opp_pitcher}`")
        
        col1, col2 = st.columns(2)
        with col1:
            pitch_type = st.selectbox("Pitch Type", ["Fastball", "Slider", "Curveball", "Changeup", "Splitter", "Sinker"], key="scout_type")
        with col2:
            result = st.selectbox("Result", [
                "Called Strike", "Swinging Strike", "Chase Swing & Miss", 
                "Chase Contact / Foul", "Ball", "Foul", "In Play", "Hit By Pitch"
            ], key="scout_result")
            
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
                
                if complete_at_bat or result in ["In Play", "Hit By Pitch"]:
                    st.session_state.opp_scout_balls = 0
                    st.session_state.opp_scout_strikes = 0
                    st.session_state.opp_scout_batter_index = (st.session_state.opp_scout_batter_index + 1) % len(our_batters_list)
                    st.success(f"At-bat complete for {current_batter}! Advanced to next hitter.")
                else:
                    if result in ["Called Strike", "Swinging Strike", "Chase Swing & Miss"]:
                        if st.session_state.opp_scout_strikes < 2:
                            st.session_state.opp_scout_strikes += 1
                    elif result == "Ball":
                        if st.session_state.opp_scout_balls < 3:
                            st.session_state.opp_scout_balls += 1
                    elif result in ["Foul", "Chase Contact / Foul"]:
                        if st.session_state.opp_scout_strikes < 2:
                            st.session_state.opp_scout_strikes += 1
                            
                    st.success(f"Logged {pitch_type} ({result}). Count is now {st.session_state.opp_scout_balls}-{st.session_state.opp_scout_strikes}")
                
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Error logging pitch: {e}")

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
                mix = opp_pitcher_df["pitch_type"].value_counts(normalize=True) * 100
                render_glowing_bars(mix, title_text="Overall Pitch Mix")
            with col_y:
                opp_zz = opp_pitcher_df[opp_pitcher_df["count"] == "0-0"]
                if not opp_zz.empty:
                    render_glowing_metric_cards(opp_zz["pitch_type"].value_counts(normalize=True) * 100, title_text="🎯 0-0 Pitch Usage")
                else:
                    st.info("No 0-0 pitches logged.")
            
            opp_ts = opp_pitcher_df[opp_pitcher_df["count"].isin(["0-2", "1-2", "2-2", "3-2"])]
            if not opp_ts.empty:
                render_glowing_bars(opp_ts["pitch_type"].value_counts(normalize=True) * 100, title_text="Putaway Breakdown")
            else:
                st.info("No 2-strike counts logged yet.")

            st.write("### 🎯 Advanced Metrics (Whiff %, Called Strike %, Total Strike %, Chase)")
            metrics_rows = []
            for p_type in opp_pitcher_df["pitch_type"].unique():
                p_sub = opp_pitcher_df[opp_pitcher_df["pitch_type"] == p_type]
                total_p = len(p_sub)
                called_strikes = len(p_sub[p_sub["result"] == "Called Strike"])
                swinging_strikes = len(p_sub[p_sub["result"].isin(["Swinging Strike", "Chase Swing & Miss"])])
                total_swings = len(p_sub[p_sub["result"].isin(["Swinging Strike", "Chase Swing & Miss", "Chase Contact / Foul", "Foul", "In Play"])])
                chase_count = len(p_sub[p_sub["result"].isin(["Chase Swing & Miss", "Chase Contact / Foul"])])
                total_strikes = len(p_sub[p_sub["result"].isin(["Called Strike", "Swinging Strike", "Chase Swing & Miss", "Chase Contact / Foul", "Foul", "In Play"])])
                
                cs_pct = (called_strikes / total_p * 100) if total_p > 0 else 0.0
                whiff_pct = (swinging_strikes / total_swings * 100) if total_swings > 0 else 0.0
                total_strike_pct = (total_strikes / total_p * 100) if total_p > 0 else 0.0
                
                metrics_rows.append({
                    "Pitch Type": p_type,
                    "Total Thrown": total_p,
                    "Called Strike %": f"{cs_pct:.1f}%",
                    "Whiff % (on Swings)": f"{whiff_pct:.1f}%",
                    "Total Strike %": f"{total_strike_pct:.1f}%",
                    "Chase Count": chase_count
                })
            st.dataframe(pd.DataFrame(metrics_rows), hide_index=True)
        else:
            st.info("No opponent pitches charted yet.")
    else:
        st.info("No pitch data logged yet.")

elif mode == "Hitter On-Deck Cheat Sheet":
    st.header("🧢 Hitter On-Deck Cheat Sheet")
    st.write("Dedicated view for hitters to review full opponent pitcher scouting, count breakdowns, and live game-plan action cards.")
    
    auto_refresh = st.checkbox("🔄 Auto-Refresh Screen (Every 5 Seconds)", value=False)
    
    if not df.empty and "mode" in df.columns:
        opp_df = df[df["mode"] == "Opponent Pitcher Scout"]
        if not opp_df.empty:
            deck_opp = st.selectbox("Select Current Opponent Pitcher", opp_df["pitcher"].unique(), key="deck_opp_select")
            deck_pitcher_df = opp_df[opp_df["pitcher"] == deck_opp]
            
            total_deck_pitches = len(deck_pitcher_df)
            st.metric("Total Pitches Charted", total_deck_pitches)
            
            # --- FULL PITCHER DIAGNOSTICS & METRICS FOR ON-DECK VIEW ---
            col_dm1, col_dm2 = st.columns(2)
            with col_dm1:
                deck_fp = deck_pitcher_df[deck_pitcher_df["count"] == "0-0"]
                if not deck_fp.empty:
                    deck_fp_strikes = len(deck_fp[deck_fp["result"].isin(["Called Strike", "Swinging Strike", "Chase Swing & Miss", "Chase Contact / Foul", "Foul", "In Play"])])
                    deck_fp_pct = (deck_fp_strikes / len(deck_fp)) * 100
                    st.markdown(f"""
                    <div class="metric-card">
                        <h3>🎯 1st-Pitch Strike % (FPS%)</h3>
                        <h2>{deck_fp_pct:.1f}%</h2>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class="metric-card">
                        <h3>🎯 1st-Pitch Strike % (FPS%)</h3>
                        <h2>0.0%</h2>
                    </div>
                    """, unsafe_allow_html=True)

            with col_dm2:
                deck_three_ball = deck_pitcher_df[deck_pitcher_df["count"].isin(["3-0", "3-1", "3-2"])]
                deck_three_pct = (len(deck_three_ball) / total_deck_pitches * 100) if total_deck_pitches > 0 else 0.0
                st.markdown(f"""
                <div class="metric-card">
                    <h3>⚠️ 3-Ball Count Frequency</h3>
                    <h2>{deck_three_pct:.1f}%</h2>
                </div>
                """, unsafe_allow_html=True)

            col_dx, col_dy = st.columns(2)
            with col_dx:
                deck_mix = deck_pitcher_df["pitch_type"].value_counts(normalize=True) * 100
                render_glowing_bars(deck_mix, title_text="📊 Overall Pitch Mix (Visual Bars)")
            with col_dy:
                deck_zz_card = deck_pitcher_df[deck_pitcher_df["count"] == "0-0"]
                if not deck_zz_card.empty:
                    render_glowing_metric_cards(deck_zz_card["pitch_type"].value_counts(normalize=True) * 100, title_text="🎯 0-0 Pitch Usage")
                else:
                    st.info("No 0-0 pitches logged.")

            deck_ts_bars = deck_pitcher_df[deck_pitcher_df["count"].isin(["0-2", "1-2", "2-2", "3-2"])]
            if not deck_ts_bars.empty:
                render_glowing_bars(deck_ts_bars["pitch_type"].value_counts(normalize=True) * 100, title_text="🚨 2-Strike Putaway Bar Breakdown")
            else:
                st.info("No 2-strike counts logged yet.")

            st.write("### 🎯 Advanced Metrics (Whiff %, Called Strike %, Total Strike %, Chase)")
            deck_metrics_rows = []
            for p_type in deck_pitcher_df["pitch_type"].unique():
                p_sub = deck_pitcher_df[deck_pitcher_df["pitch_type"] == p_type]
                total_p = len(p_sub)
                called_strikes = len(p_sub[p_sub["result"] == "Called Strike"])
                swinging_strikes = len(p_sub[p_sub["result"].isin(["Swinging Strike", "Chase Swing & Miss"])])
                total_swings = len(p_sub[p_sub["result"].isin(["Swinging Strike", "Chase Swing & Miss", "Chase Contact / Foul", "Foul", "In Play"])])
                chase_count = len(p_sub[p_sub["result"].isin(["Chase Swing & Miss", "Chase Contact / Foul"])])
                total_strikes = len(p_sub[p_sub["result"].isin(["Called Strike", "Swinging Strike", "Chase Swing & Miss", "Chase Contact / Foul", "Foul", "In Play"])])
                
                cs_pct = (called_strikes / total_p * 100) if total_p > 0 else 0.0
                whiff_pct = (swinging_strikes / total_swings * 100) if total_swings > 0 else 0.0
                total_strike_pct = (total_strikes / total_p * 100) if total_p > 0 else 0.0
                
                deck_metrics_rows.append({
                    "Pitch Type": p_type,
                    "Total Thrown": total_p,
                    "Called Strike %": f"{cs_pct:.1f}%",
                    "Whiff % (on Swings)": f"{whiff_pct:.1f}%",
                    "Total Strike %": f"{total_strike_pct:.1f}%",
                    "Chase Count": chase_count
                })
            st.dataframe(pd.DataFrame(deck_metrics_rows), hide_index=True)

            # --- INDIVIDUAL HITTER REVIEW & STRATEGIC APPROACH ---
            st.markdown("---")
            st.subheader("👤 Individual Hitter Matchup & At-Bat Approach")
            
            deck_hitters = list(deck_pitcher_df["batter"].unique()) if "batter" in deck_pitcher_df.columns else []
            deck_hitter_options = deck_hitters if deck_hitters else our_batters_list
            
            if deck_hitter_options:
                selected_deck_hitter = st.selectbox("Select Our Hitter to Review Matchup", deck_hitter_options, key="deck_hitter_review_select")
                hitter_scout_df = deck_pitcher_df[deck_pitcher_df["batter"] == selected_deck_hitter]
                
                if not hitter_scout_df.empty:
                    st.metric(f"Total Pitches Seen by {selected_deck_hitter}", len(hitter_scout_df))
                    
                    hc1, hc2 = st.columns(2)
                    with hc1:
                        st.write("**Pitch Mix Faced**")
                        h_mix_deck = hitter_scout_df["pitch_type"].value_counts(normalize=True) * 100
                        render_glowing_bars(h_mix_deck, title_text="Pitch Distribution")
                    with hc2:
                        st.write("**Result Breakdown by Pitch**")
                    
                    for pt in hitter_scout_df["pitch_type"].unique():
                        pt_df = hitter_scout_df[hitter_scout_df["pitch_type"] == pt]
                        
                        take_strike = len(pt_df[pt_df["result"] == "Called Strike"])
                        take_ball = len(pt_df[pt_df["result"] == "Ball"])
                        chase_strike = len(pt_df[pt_df["result"].isin(["Swinging Strike", "Chase Swing & Miss", "Chase Contact / Foul"])])
                        foul_ball = len(pt_df[pt_df["result"].isin(["Foul"])])
                        put_in_play = len(pt_df[pt_df["result"] == "In Play"])
                        
                        single_pitch_df = pd.DataFrame([{
                            "Take for Strike": take_strike,
                            "Take for Ball": take_ball,
                            "Chase for Strike": chase_strike,
                            "Foul Ball": foul_ball,
                            "Put in Play": put_in_play
                        }])
                        
                        st.markdown(f"**📌 Pitch: {pt}** (Total Seen: {len(pt_df)})")
                        st.dataframe(single_pitch_df, hide_index=True)
                    
                    st.write("**Detailed At-Bat Log History**")
                    st.dataframe(hitter_scout_df[["timestamp", "count", "pitch_type", "result", "contact_type", "hit_type"]], hide_index=True)
                else:
                    st.info(f"No logged pitch data found for {selected_deck_hitter} against {deck_opp}.")
            else:
                st.info("No our batters available for review.")

            st.markdown("---")
            st.markdown("### 🔥 Live Dugout Game Plan & Hitter Notice")
            if len(deck_pitcher_df) >= 3:
                deck_zz = deck_pitcher_df[deck_pitcher_df["count"] == "0-0"]
                fav_00 = (deck_zz["pitch_type"].value_counts(normalize=True) * 100).idxmax() if not deck_zz.empty else "Fastball"
                fav_00_pct = (deck_zz["pitch_type"].value_counts(normalize=True) * 100).max() if not deck_zz.empty else 50.0

                deck_ts = deck_pitcher_df[deck_pitcher_df["count"].isin(["0-2", "1-2", "2-2", "3-2"])]
                putaway_pitch = (deck_ts["pitch_type"].value_counts(normalize=True) * 100).idxmax() if not deck_ts.empty else "Breaking Ball"
                putaway_pct = (deck_ts["pitch_type"].value_counts(normalize=True) * 100).max() if not deck_ts.empty else 50.0

                st.success(f"""
                * 🟢 **0-0 Plan (First-Pitch Hunt):** Expect a **{fav_00}** (`{fav_00_pct:.1f}%` of the time on 0-0). If it's over the plate, put a good swing on it early!
                * ⚠️ **2-Strike Trap Notice:** Watch out for the **{putaway_pitch}** (`{putaway_pct:.1f}%` in putaway counts). Expand your zone discipline or protect the plate.
                """)
            else:
                st.info("Waiting for more opponent pitches to generate live dugout game plan cards.")
        else:
            st.info("No opponent pitches charted yet.")
    else:
        st.info("No pitch data logged yet today.")
        
    if auto_refresh:
        time.sleep(5)
        st.cache_data.clear()
        st.rerun()

else:
    st.header("🎯 Bullpen Charting & Command Analysis")
    st.write("Chart bullpen sessions visually from the pitcher's perspective. Select your target location on the strike zone, then select where the pitch actually went.")
    
    st.sidebar.markdown("---")
    st.sidebar.header("⚙️ Bullpen Pitcher Control")
    
    existing_bullpens = []
    if not df.empty and "mode" in df.columns:
        existing_bullpens = list(df[df["mode"] == "Bullpen Charting"]["pitcher"].unique())
        
    bp_options = existing_bullpens + ["➕ Add New Bullpen Pitcher"]
    selected_bp_option = st.sidebar.selectbox("Bullpen Pitcher", bp_options, index=0 if existing_bullpens else len(bp_options)-1, key="bp_select_side")
    
    if selected_bp_option == "➕ Add New Bullpen Pitcher":
        current_bp_pitcher = st.sidebar.text_input("Enter Pitcher Name / #", value="Pitcher 1", key="bp_name_input")
    else:
        current_bp_pitcher = selected_bp_option

    with st.form("bullpen_form_v3", clear_on_submit=True):
        st.write(f"**Logging Bullpen Session for:** `{current_bp_pitcher}`")
        
        bp_col1, bp_col2 = st.columns(2)
        with bp_col1:
            bp_pitch_type = st.selectbox("Pitch Type", ["Fastball", "Slider", "Curveball", "Changeup", "Splitter", "Sinker"], key="bp_type_v3")
        with bp_col2:
            bp_result = st.selectbox("Result", ["Strike", "Ball"], key="bp_result_v3")
            
        st.markdown("---")
        st.subheader("📍 Visual Strike Zone Plotter (Pitcher Perspective)")
        st.info("Use the coordinate inputs below to target and plot the pitch. (Catcher's perspective: X: -1.5 [Left/Glove] to +1.5 [Right/Arm-side], Y: 0.5 [Low] to 3.5 [High]).")
        
        c_in1, c_in2 = st.columns(2)
        with c_in1:
            st.markdown("### 🎯 1st Click: Intended Target (Red Dot)")
            t_x = st.slider("Target X (Horizontal)", -1.5, 1.5, st.session_state.bp_target_x, 0.05, key="tz_x")
            t_y = st.slider("Target Y (Vertical)", 0.5, 3.5, st.session_state.bp_target_y, 0.05, key="tz_y")
        with c_in2:
            st.markdown("### 📍 2nd Click: Actual Location (Blue Dot)")
            a_x = st.slider("Actual X (Horizontal)", -1.5, 1.5, st.session_state.bp_actual_x, 0.05, key="az_x")
            a_y = st.slider("Actual Y (Vertical)", 0.5, 3.5, st.session_state.bp_actual_y, 0.05, key="az_y")
            
        # Live interactive visual preview of the current pitch being plotted
        preview_fig = go.Figure()
        # Strike Zone Box (-0.83 to 0.83, 1.5 to 3.5)
        preview_fig.add_shape(type="rect", x0=-0.83, y0=1.5, x1=0.83, y1=3.5, line=dict(color="white", width=3))
        # Home plate pentagon outline at bottom
        preview_fig.add_shape(type="path", path="M -0.7 0.7 L 0.7 0.7 L 0.7 0.5 L 0.0 0.2 L -0.7 0.5 Z", line=dict(color="gray", width=2))
        
        # Add Target (Red) and Actual (Blue)
        preview_fig.add_trace(go.Scatter(x=[t_x], y=[t_y], mode="markers+text", marker=dict(color="#ff4b4b", size=16), text=["TARGET"], textposition="top center", name="Intended Target"))
        preview_fig.add_trace(go.Scatter(x=[a_x], y=[a_y], mode="markers+text", marker=dict(color="#1c83e1", size=16), text=["ACTUAL"], textposition="bottom center", name="Actual Location"))
        
        preview_fig.update_layout(
            title="Live Pitch Plot Preview",
            xaxis_title="Horizontal (Catcher's Glove ◄ ► Arm-side)",
            yaxis_title="Vertical Height",
            range_x=[-2.0, 2.0], range_y=[0.0, 4.0],
            plot_bgcolor="#1e1e2f", paper_bgcolor="#1e1e2f", font_color="white",
            height=400, margin=dict(l=20, r=20, t=40, b=20)
        )
        st.plotly_chart(preview_fig, use_container_width=True)
        
        bp_submitted_v3 = st.form_submit_button("Log Pitch to Session 🎯")
        
        if bp_submitted_v3:
            try:
                supabase.table("pitch_logs").insert({
                    "mode": "Bullpen Charting",
                    "pitcher": current_bp_pitcher,
                    "batter": "Bullpen Session",
                    "count": "0-0",
                    "pitch_type": bp_pitch_type,
                    "result": bp_result,
                    "contact_type": f"{t_x},{t_y}", # Target X,Y
                    "hit_type": f"{a_x},{a_y}"       # Actual X,Y
                }).execute()
                st.success(f"Logged {bp_pitch_type} ({bp_result}) successfully!")
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Error logging bullpen pitch: {e}")

    if st.button("↩️ Undo Last Logged Bullpen Pitch"):
        try:
            recent_res = supabase.table("pitch_logs").select("id").eq("mode", "Bullpen Charting").order("timestamp", desc=True).limit(1).execute()
            if recent_res.data:
                last_id = recent_res.data[0]["id"]
                supabase.table("pitch_logs").delete().eq("id", last_id).execute()
                st.cache_data.clear()
                st.success("Successfully deleted the last bullpen pitch!")
                st.rerun()
            else:
                st.warning("No bullpen pitches to undo.")
        except Exception as e:
            st.error(f"Error undoing bullpen pitch: {e}")

    st.markdown("---")
    st.subheader("📊 Bullpen Session Analytics & Command Maps")
    
    if not df.empty and "mode" in df.columns:
        bp_df = df[df["mode"] == "Bullpen Charting"]
        if not bp_df.empty:
            selected_bp_view = st.selectbox("Select Bullpen Pitcher to Review", bp_df["pitcher"].unique(), key="bp_view_select")
            pitcher_bp_df = bp_df[bp_df["pitcher"] == selected_bp_view]
            
            total_bp_pitches = len(pitcher_bp_df)
            total_strikes_bp = len(pitcher_bp_df[pitcher_bp_df["result"] == "Strike"])
            overall_strike_pct = (total_strikes_bp / total_bp_pitches * 100) if total_bp_pitches > 0 else 0.0
            
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                st.metric("Total Pitches Thrown", total_bp_pitches)
            with col_b2:
                st.markdown(f"""
                <div class="metric-card">
                    <h3>🎯 Overall Strike %</h3>
                    <h2>{overall_strike_pct:.1f}%</h2>
                </div>
                """, unsafe_allow_html=True)
                
            st.write("### 📈 Strike % by Pitch Type")
            bp_metrics_rows = []
            for p_type in pitcher_bp_df["pitch_type"].unique():
                p_sub = pitcher_bp_df[pitcher_bp_df["pitch_type"] == p_type]
                p_total = len(p_sub)
                p_strikes = len(p_sub[p_sub["result"] == "Strike"])
                p_strike_pct = (p_strikes / p_total * 100) if p_total > 0 else 0.0
                
                bp_metrics_rows.append({
                    "Pitch Type": p_type,
                    "Total Thrown": p_total,
                    "Strikes": p_strikes,
                    "Strike %": f"{p_strike_pct:.1f}%"
                })
            st.dataframe(pd.DataFrame(bp_metrics_rows), hide_index=True)
            
            st.markdown("---")
            st.subheader("🎨 Command Target vs. Actual Strike Zone Plot")
            st.info("🔴 **Red Dots:** Intended Target | 🔵 **Blue Dots:** Actual Location")
            
            plot_data = []
            for idx, row in pitcher_bp_df.iterrows():
                try:
                    t_coords = str(row["contact_type"]).split(",")
                    a_coords = str(row["hit_type"]).split(",")
                    if len(t_coords) == 2 and len(a_coords) == 2:
                        plot_data.append({
                            "Pitcher": row["pitcher"],
                            "Pitch Type": row["pitch_type"],
                            "X": float(t_coords[0]),
                            "Y": float(t_coords[1]),
                            "Type": "Target (Intended)"
                        })
                        plot_data.append({
                            "Pitcher": row["pitcher"],
                            "Pitch Type": row["pitch_type"],
                            "X": float(a_coords[0]),
                            "Y": float(a_coords[1]),
                            "Type": "Actual (Result)"
                        })
                except:
                    continue
                    
            if plot_data:
                plot_df = pd.DataFrame(plot_data)
                
                selected_plot_pitch = st.selectbox("Filter Command Map by Pitch Type", ["All Pitches"] + list(pitcher_bp_df["pitch_type"].unique()))
                if selected_plot_pitch != "All Pitches":
                    plot_df = plot_df[plot_df["Pitch Type"] == selected_plot_pitch]
                
                fig_bp = px.scatter(
                    plot_df, x="X", y="Y", color="Type", symbol="Type",
                    color_discrete_map={"Target (Intended)": "#ff4b4b", "Actual (Result)": "#1c83e1"},
                    range_x=[-2.0, 2.0], range_y=[0.0, 4.0],
                    title=f"Command Map for {selected_bp_view} ({selected_plot_pitch})"
                )
                
                # Strike zone box and home plate
                fig_bp.add_shape(type="rect", x0=-0.83, y0=1.5, x1=0.83, y1=3.5, line=dict(color="white", width=2))
                fig_bp.add_shape(type="path", path="M -0.7 0.7 L 0.7 0.7 L 0.7 0.5 L 0.0 0.2 L -0.7 0.5 Z", line=dict(color="gray", width=2))

                fig_bp.update_layout(
                    xaxis_title="Horizontal Location (Glove ◄ ► Arm-side)",
                    yaxis_title="Vertical Location (Height)",
                    plot_bgcolor="#1e1e2f",
                    paper_bgcolor="#1e1e2f",
                    font_color="white"
                )
                st.plotly_chart(fig_bp, use_container_width=True)
            else:
                st.info("Log pitches to generate command maps.")
        else:
            st.info("No bullpen sessions logged yet.")
    else:
        st.info("No pitch data logged yet.")

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

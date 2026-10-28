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
    border-radius: 6px;
    overflow: hidden;
    height: 8px;
    width: 100%;
    margin-top: 4px;
    margin-bottom: 8px;
}
.glow-bar-fill {
    height: 100%;
    background: linear-gradient(90deg, #1c83e1, #00ccff);
    box-shadow: 0 0 8px #00ccff, 0 0 15px #1c83e1;
    border-radius: 6px;
}
.pitch-card {
    background-color: #161622;
    border: 1px solid #2a2a40;
    border-radius: 10px;
    padding: 14px;
    margin-bottom: 12px;
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
if "selected_our_pitcher" not in st.session_state:
    st.session_state.selected_our_pitcher = "Reliever 1"

if "opp_scout_balls" not in st.session_state:
    st.session_state.opp_scout_balls = 0
if "opp_scout_strikes" not in st.session_state:
    st.session_state.opp_scout_strikes = 0
if "opp_scout_batter_index" not in st.session_state:
    st.session_state.opp_scout_batter_index = 0
if "selected_opp_pitcher" not in st.session_state:
    st.session_state.selected_opp_pitcher = "Opponent Reliever"

# Fetch existing pitch logs from Supabase
@st.cache_data(ttl=2)
def load_data():
    try:
        response = supabase.table("pitch_logs").select("*").order("timestamp", desc=False).execute()
        return pd.DataFrame(response.data)
    except Exception as e:
        return pd.DataFrame()

df = load_data()

# --- HELPER: CUSTOM PITCH SORTING & RENDERERS ---
PITCH_ORDER = ["Fastball", "Curveball", "Slider", "Changeup", "Splitter", "Sinker", "Sweeper"]

def sort_pitch_series(series_or_index):
    """Sorts a pandas Series or Index based on the preferred PITCH_ORDER."""
    existing_items = list(series_or_index)
    sorted_list = [p for p in PITCH_ORDER if p in existing_items]
    # Include any unexpected residual pitch types at the end
    for item in existing_items:
        if item not in sorted_list:
            sorted_list.append(item)
    return sorted_list

def render_glowing_bars(series, title_text="Pitch Distribution"):
    st.write(f"### {title_text}")
    if series.empty:
        st.info("No data available for visual breakdown.")
        return
    
    sorted_index = sort_pitch_series(series.index)
    for pitch_type in sorted_index:
        pct = series[pitch_type]
        st.markdown(f"**{pitch_type}** ({pct:.1f}%)")
        st.markdown(f"""
        <div class="glow-bar-container">
            <div class="glow-bar-fill" style="width: {min(max(pct, 2), 100)}%;"></div>
        </div>
        """, unsafe_allow_html=True)

def render_clean_advanced_metrics(pitcher_df):
    st.write("### 🎯 Advanced Metrics Breakdown")
    if pitcher_df.empty or "pitch_type" not in pitcher_df.columns:
        st.info("No pitch data available for advanced metrics.")
        return

    unique_pitches = pitcher_df["pitch_type"].unique()
    sorted_pitches = sort_pitch_series(unique_pitches)

    for p_type in sorted_pitches:
        p_sub = pitcher_df[pitcher_df["pitch_type"] == p_type]
        if p_sub.empty:
            continue
        total_p = len(p_sub)
        called_strikes = len(p_sub[p_sub["result"] == "Called Strike"])
        swinging_strikes = len(p_sub[p_sub["result"].isin(["Swinging Strike", "Chase Swing & Miss"])])
        total_swings = len(p_sub[p_sub["result"].isin(["Swinging Strike", "Chase Swing & Miss", "Chase Contact / Foul", "Foul", "In Play"])])
        chase_count = len(p_sub[p_sub["result"].isin(["Chase Swing & Miss", "Chase Contact / Foul"])])
        ball_count = len(p_sub[p_sub["result"] == "Ball"])
        in_play_count = len(p_sub[p_sub["result"] == "In Play"])
        total_strikes = len(p_sub[p_sub["result"].isin(["Called Strike", "Swinging Strike", "Chase Swing & Miss", "Chase Contact / Foul", "Foul", "In Play"])])
        
        cs_pct = (called_strikes / total_p * 100) if total_p > 0 else 0.0
        whiff_pct = (swinging_strikes / total_swings * 100) if total_swings > 0 else 0.0
        total_strike_pct = (total_strikes / total_p * 100) if total_p > 0 else 0.0

        st.markdown(f"""
        <div class="pitch-card">
            <div style="font-size: 16px; font-weight: 700; color: #ffffff; margin-bottom: 8px;">
                ⚾ {p_type} &nbsp;|&nbsp; <span style="color: #a0a0c0; font-size: 13px;">Thrown: {total_p} &bull; Balls: {ball_count} &bull; In Play: {in_play_count} &bull; Chase: {chase_count}</span>
            </div>
            <div style="display: flex; gap: 15px; margin-bottom: 8px;">
                <div style="flex: 1;">
                    <span style="font-size: 12px; color: #a0a0c0;">Total Strike %: <b>{total_strike_pct:.1f}%</b> ({total_strikes}/{total_p})</span>
                    <div class="glow-bar-container"><div class="glow-bar-fill" style="width: {min(max(total_strike_pct, 2), 100)}%;"></div></div>
                </div>
                <div style="flex: 1;">
                    <span style="font-size: 12px; color: #a0a0c0;">Whiff % (Swings): <b>{whiff_pct:.1f}%</b> ({swinging_strikes}/{total_swings})</span>
                    <div class="glow-bar-container"><div class="glow-bar-fill" style="width: {min(max(whiff_pct, 2), 100)}%;"></div></div>
                </div>
                <div style="flex: 1;">
                    <span style="font-size: 12px; color: #a0a0c0;">Called Strike %: <b>{cs_pct:.1f}%</b> ({called_strikes}/{total_p})</span>
                    <div class="glow-bar-container"><div class="glow-bar-fill" style="width: {min(max(cs_pct, 2), 100)}%;"></div></div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

def render_table_count_breakdown(pitcher_df):
    st.write("### 📊 Pitch Type % Breakdown by Count")
    if pitcher_df.empty or "count" not in pitcher_df.columns:
        st.info("No data available.")
        return
    
    ct_table = pd.crosstab(pitcher_df["count"], pitcher_df["pitch_type"], normalize="index").mul(100).round(1)
    # Reorder columns based on PITCH_ORDER
    existing_cols = [c for c in PITCH_ORDER if c in ct_table.columns]
    other_cols = [c for c in ct_table.columns if c not in existing_cols]
    ct_table = ct_table[existing_cols + other_cols]
    
    st.dataframe(ct_table.astype(str) + '%', use_container_width=True)

def render_clean_batted_ball_profile(pitcher_df):
    st.write("### 📊 Batted Ball Profile & Outcomes")
    in_play_df = pitcher_df[pitcher_df["contact_type"] != "N/A"]
    if in_play_df.empty:
        st.info("No batted ball data recorded yet.")
        return
    
    contact_matrix = pd.crosstab(in_play_df["pitch_type"], in_play_df["contact_type"], normalize="index").mul(100).round(1)
    hit_matrix = pd.crosstab(in_play_df["pitch_type"], in_play_df["hit_type"], normalize="index").mul(100).round(1)
    
    all_pitches = list(set(list(contact_matrix.index) + list(hit_matrix.index)))
    sorted_pitches = sort_pitch_series(all_pitches)
    
    for pt in sorted_pitches:
        contact_html = ""
        if pt in contact_matrix.index:
            for c_type, c_val in contact_matrix.loc[pt].items():
                if c_val > 0:
                    contact_html += f"<span style='background: #1e1e2f; padding: 4px 8px; border-radius: 6px; font-size: 12px; margin-right: 6px; border: 1px solid #2a2a40;'>{c_type}: <b>{c_val:.1f}%</b></span>"
                    
        hit_html = ""
        if pt in hit_matrix.index:
            for h_type, h_val in hit_matrix.loc[pt].items():
                if h_val > 0:
                    hit_html += f"<span style='background: #1e1e2f; padding: 4px 8px; border-radius: 6px; font-size: 12px; margin-right: 6px; border: 1px solid #2a2a40;'>{h_type}: <b>{h_val:.1f}%</b></span>"

        st.markdown(f"""
        <div class="pitch-card">
            <div style="font-size: 16px; font-weight: 700; color: #ffffff; margin-bottom: 8px;">
                ⚾ {pt}
            </div>
            <div style="margin-bottom: 8px;">
                <div style="font-size: 12px; color: #a0a0c0; margin-bottom: 4px;">Contact Types:</div>
                <div>{contact_html if contact_html else '<span style="color:#666; font-size:12px;">N/A</span>'}</div>
            </div>
            <div>
                <div style="font-size: 12px; color: #a0a0c0; margin-bottom: 4px;">Hit Outcomes:</div>
                <div>{hit_html if hit_html else '<span style="color:#666; font-size:12px;">N/A</span>'}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

def render_clean_hitter_matchup(hitter_matchup_df):
    st.write("### 📊 Result Breakdown by Pitch")
    matchup_pitches = hitter_matchup_df["pitch_type"].unique()
    sorted_matchup_pitches = sort_pitch_series(matchup_pitches)
    
    for pt in sorted_matchup_pitches:
        pt_df = hitter_matchup_df[hitter_matchup_df["pitch_type"] == pt]
        total_pt = len(pt_df)
        
        take_strike = len(pt_df[pt_df["result"] == "Called Strike"])
        take_ball = len(pt_df[pt_df["result"] == "Ball"])
        chase_strike = len(pt_df[pt_df["result"].isin(["Swinging Strike", "Chase Swing & Miss", "Chase Contact / Foul"])])
        foul_ball = len(pt_df[pt_df["result"].isin(["Foul"])])
        put_in_play = len(pt_df[pt_df["result"] == "In Play"])
        
        st.markdown(f"""
        <div class="pitch-card">
            <div style="font-size: 16px; font-weight: 700; color: #ffffff; margin-bottom: 8px;">
                📌 {pt} &nbsp;|&nbsp; <span style="color: #a0a0c0; font-size: 13px;">Total Thrown: {total_pt}</span>
            </div>
            <div style="display: flex; gap: 10px; flex-wrap: wrap;">
                <div style="flex: 1; min-width: 80px; background: #1e1e2f; padding: 8px; border-radius: 6px; text-align: center;">
                    <span style="font-size: 11px; color: #a0a0c0;">Take Strike</span>
                    <div style="font-size: 16px; font-weight: 700; color: #fff;">{take_strike}</div>
                </div>
                <div style="flex: 1; min-width: 80px; background: #1e1e2f; padding: 8px; border-radius: 6px; text-align: center;">
                    <span style="font-size: 11px; color: #a0a0c0;">Take Ball</span>
                    <div style="font-size: 16px; font-weight: 700; color: #fff;">{take_ball}</div>
                </div>
                <div style="flex: 1; min-width: 80px; background: #1e1e2f; padding: 8px; border-radius: 6px; text-align: center;">
                    <span style="font-size: 11px; color: #a0a0c0;">Chase Strike</span>
                    <div style="font-size: 16px; font-weight: 700; color: #fff;">{chase_strike}</div>
                </div>
                <div style="flex: 1; min-width: 80px; background: #1e1e2f; padding: 8px; border-radius: 6px; text-align: center;">
                    <span style="font-size: 11px; color: #a0a0c0;">Foul Ball</span>
                    <div style="font-size: 16px; font-weight: 700; color: #fff;">{foul_ball}</div>
                </div>
                <div style="flex: 1; min-width: 80px; background: #1e1e2f; padding: 8px; border-radius: 6px; text-align: center;">
                    <span style="font-size: 11px; color: #a0a0c0;">Put in Play</span>
                    <div style="font-size: 16px; font-weight: 700; color: #fff;">{put_in_play}</div>
                </div>
            </div>
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
    
    current_default_index = 0
    if st.session_state.selected_our_pitcher in pitcher_options:
        current_default_index = pitcher_options.index(st.session_state.selected_our_pitcher)
    elif existing_pitchers:
        current_default_index = 0
    else:
        current_default_index = len(pitcher_options) - 1

    selected_pitcher_option = st.sidebar.selectbox("Current Pitcher", pitcher_options, index=current_default_index, key="sidebar_our_pitcher_select")
    
    if selected_pitcher_option == "➕ Add New Reliever/Pitcher":
        current_our_pitcher = st.sidebar.text_input("Enter Reliever Name", value="Reliever 1", key="new_reliever_input")
        st.session_state.selected_our_pitcher = current_our_pitcher
    else:
        current_our_pitcher = selected_pitcher_option
        st.session_state.selected_our_pitcher = current_our_pitcher

    st.sidebar.markdown("---")
    st.sidebar.header("🛠️ Scorekeeper Correction")
    if opp_batters_list:
        if st.session_state.our_pitcher_batter_index >= len(opp_batters_list):
            st.session_state.our_pitcher_batter_index = 0
            
        manual_override_opp = st.sidebar.selectbox(
            "Override Current Opponent Hitter", 
            opp_batters_list, 
            index=st.session_state.our_pitcher_batter_index,
            key="our_hitter_override_select"
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
            pitch_type = st.selectbox("Pitch Type", PITCH_ORDER, key="our_pitch_type")
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
                    render_glowing_bars(mix, title_text="📊 Overall Pitch Mix")
                with col_b:
                    zero_zero = pitcher_df[pitcher_df["count"] == "0-0"]
                    if not zero_zero.empty:
                        zz_mix = zero_zero["pitch_type"].value_counts(normalize=True) * 100
                        render_glowing_bars(zz_mix, title_text="🎯 0-0 Pitch Usage")
                    else:
                        st.info("No 0-0 pitches logged yet.")

                ts_df = pitcher_df[pitcher_df["count"].isin(["0-2", "1-2", "2-2", "3-2"])]
                if not ts_df.empty:
                    ts_mix = ts_df["pitch_type"].value_counts(normalize=True) * 100
                    render_glowing_bars(ts_mix, title_text="🚨 2-Strike Putaway Breakdown")
                else:
                    st.info("No 2-strike counts logged yet.")

                render_clean_advanced_metrics(pitcher_df)
                render_table_count_breakdown(pitcher_df)
                render_clean_batted_ball_profile(pitcher_df)
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
            
            selected_age_group = st.selectbox("Select Pitcher Age Group (USA Pitch Smart)", [
                "7–8", "9–10", "11–12", "13–14", "15–16", "17–18", "19–22"
            ], key="pitch_smart_age")

            def get_pitch_smart_rest(age_group, count):
                if count == 0:
                    return "0 Days Rest", "Daily Max: See Table"
                
                if age_group == "7–8":
                    max_p = 50
                    if count <= 20: rest = "0 Days Rest (1–20)"
                    elif count <= 35: rest = "1 Day Rest (21–35)"
                    elif count <= 50: rest = "2 Days Rest (36–50)"
                    else: rest = "Exceeds Daily Maximum!"
                elif age_group == "9–10":
                    max_p = 75
                    if count <= 20: rest = "0 Days Rest (1–20)"
                    elif count <= 35: rest = "1 Day Rest (21–35)"
                    elif count <= 50: rest = "2 Days Rest (36–50)"
                    elif count <= 65: rest = "3 Days Rest (51–65)"
                    else: rest = "4 Days Rest (66+)"
                elif age_group in ["11–12", "13–14"]:
                    max_p = 85 if age_group == "11–12" else 95
                    if count <= 20: rest = "0 Days Rest (1–20)"
                    elif count <= 35: rest = "1 Day Rest (21–35)"
                    elif count <= 50: rest = "2 Days Rest (36–50)"
                    elif count <= 65: rest = "3 Days Rest (51–65)"
                    else: rest = "4 Days Rest (66+)"
                elif age_group == "15–16":
                    max_p = 95
                    if count <= 30: rest = "0 Days Rest (1–30)"
                    elif count <= 45: rest = "1 Day Rest (31–45)"
                    elif count <= 60: rest = "2 Days Rest (46–60)"
                    elif count <= 75: rest = "3 Days Rest (61–75)"
                    else: rest = "4 Days Rest (76+)"
                elif age_group == "17–18":
                    max_p = 105
                    if count <= 30: rest = "0 Days Rest (1–30)"
                    elif count <= 45: rest = "1 Day Rest (31–45)"
                    elif count <= 60: rest = "2 Days Rest (46–60)"
                    elif count <= 80: rest = "3 Days Rest (61–80)"
                    else: rest = "4 Days Rest (81+)"
                else:
                    max_p = 120
                    if count <= 30: rest = "0 Days Rest (1–30)"
                    elif count <= 45: rest = "1 Day Rest (31–45)"
                    elif count <= 60: rest = "2 Days Rest (46–60)"
                    elif count <= 80: rest = "3 Days Rest (61–80)"
                    else: rest = "4 Days Rest (81–105+)"
                
                return rest, f"Daily Max: {max_p}"

            rest_req, max_limit_str = get_pitch_smart_rest(selected_age_group, total_pitches)

            col_stat1, col_stat2 = st.columns(2)
            with col_stat1:
                st.metric("Total Pitches Thrown", total_pitches)
            with col_stat2:
                st.markdown(f"""
                <div class="metric-card" style="padding: 10px;">
                    <h3>⚾ Pitch Smart Rest Required</h3>
                    <h2 style="font-size: 20px; color: #00ccff;">{rest_req}</h2>
                    <p style="color: #a0a0c0; font-size: 12px; margin: 0;">({max_limit_str} for {selected_age_group} yrs)</p>
                </div>
                """, unsafe_allow_html=True)
            
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
                render_glowing_bars(mix, title_text="📊 Overall Pitch Mix")
            with col_y:
                coach_zz = coach_pitcher_df[coach_pitcher_df["count"] == "0-0"]
                if not coach_zz.empty:
                    render_glowing_bars(coach_zz["pitch_type"].value_counts(normalize=True) * 100, title_text="🎯 0-0 Pitch Usage")
                else:
                    st.info("No 0-0 pitches logged.")
            
            coach_ts = coach_pitcher_df[coach_pitcher_df["count"].isin(["0-2", "1-2", "2-2", "3-2"])]
            if not coach_ts.empty:
                render_glowing_bars(coach_ts["pitch_type"].value_counts(normalize=True) * 100, title_text="🚨 2-Strike Putaway Breakdown")
            else:
                st.info("No 2-strike counts logged yet.")

            render_clean_advanced_metrics(coach_pitcher_df)
            render_table_count_breakdown(coach_pitcher_df)
            render_clean_batted_ball_profile(coach_pitcher_df)

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
                        pass
                        
                    render_clean_hitter_matchup(hitter_matchup_df)
                    
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
    
    opp_default_index = 0
    if st.session_state.selected_opp_pitcher in opp_options:
        opp_default_index = opp_options.index(st.session_state.selected_opp_pitcher)
    elif existing_opps:
        opp_default_index = 0
    else:
        opp_default_index = len(opp_options) - 1

    selected_opp_option = st.sidebar.selectbox("Opponent Pitcher", opp_options, index=opp_default_index, key="opp_select_side")
    
    if selected_opp_option == "➕ Add New Opponent Pitcher":
        current_opp_pitcher = st.sidebar.text_input("Enter Opponent Pitcher Name / #", value="Opponent Reliever", key="new_opp_input")
        st.session_state.selected_opp_pitcher = current_opp_pitcher
    else:
        current_opp_pitcher = selected_opp_option
        st.session_state.selected_opp_pitcher = current_opp_pitcher

    st.sidebar.markdown("---")
    st.sidebar.header("🛠️ Scorekeeper Correction")
    if our_batters_list:
        if st.session_state.opp_scout_batter_index >= len(our_batters_list):
            st.session_state.opp_scout_batter_index = 0
            
        manual_override_our = st.sidebar.selectbox(
            "Override Current Our Hitter", 
            our_batters_list, 
            index=st.session_state.opp_scout_batter_index,
            key="opp_hitter_override_select"
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
            pitch_type = st.selectbox("Pitch Type", PITCH_ORDER, key="scout_type")
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
                    render_glowing_bars(opp_zz["pitch_type"].value_counts(normalize=True) * 100, title_text="🎯 0-0 Pitch Usage")
                else:
                    st.info("No 0-0 pitches logged.")
            
            opp_ts = opp_pitcher_df[opp_pitcher_df["count"].isin(["0-2", "1-2", "2-2", "3-2"])]
            if not opp_ts.empty:
                render_glowing_bars(opp_ts["pitch_type"].value_counts(normalize=True) * 100, title_text="Putaway Breakdown")
            else:
                st.info("No 2-strike counts logged yet.")

            render_clean_advanced_metrics(opp_pitcher_df)
            render_table_count_breakdown(opp_pitcher_df)
            render_clean_batted_ball_profile(opp_pitcher_df)
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
                render_glowing_bars(deck_mix, title_text="📊 Overall Pitch Mix")
            with col_dy:
                deck_zz_card = deck_pitcher_df[deck_pitcher_df["count"] == "0-0"]
                if not deck_zz_card.empty:
                    render_glowing_bars(deck_zz_card["pitch_type"].value_counts(normalize=True) * 100, title_text="🎯 0-0 Pitch Usage")
                else:
                    st.info("No 0-0 pitches logged.")

            deck_ts_bars = deck_pitcher_df[deck_pitcher_df["count"].isin(["0-2", "1-2", "2-2", "3-2"])]
            if not deck_ts_bars.empty:
                render_glowing_bars(deck_ts_bars["pitch_type"].value_counts(normalize=True) * 100, title_text="🚨 2-Strike Putaway Breakdown")
            else:
                st.info("No 2-strike counts logged yet.")

            render_clean_advanced_metrics(deck_pitcher_df)
            render_table_count_breakdown(deck_pitcher_df)
            render_clean_batted_ball_profile(deck_pitcher_df)

            st.markdown("---")
            st.subheader("👤 Individual Hitter Review & Strategic Approach")
            
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
                        pass
                    
                    render_clean_hitter_matchup(hitter_scout_df)
                    
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
    st.header("🎯 Bullpen Charting & Analysis")
    st.write("Chart bullpen sessions quickly by recording pitch type and result (Strike/Ball), tracking total volume, and viewing strike percentages by pitch type.")
    
    st.sidebar.markdown("---")
    st.sidebar.header("⚙️ Bullpen Pitcher Control")
    
    if st.sidebar.button("🗑️ Clear Bullpen Data & Start New"):
        try:
            supabase.table("pitch_logs").delete().eq("mode", "Bullpen Charting").execute()
            st.sidebar.success("Bullpen session cleared successfully!")
            st.cache_data.clear()
            st.rerun()
        except Exception as e:
            st.sidebar.error(f"Error clearing bullpen data: {e}")

    existing_bullpens = []
    if not df.empty and "mode" in df.columns:
        existing_bullpens = list(df[df["mode"] == "Bullpen Charting"]["pitcher"].unique())
        
    bp_options = existing_bullpens + ["➕ Add New Bullpen Pitcher"]
    selected_bp_option = st.sidebar.selectbox("Bullpen Pitcher", bp_options, index=0 if existing_bullpens else len(bp_options)-1, key="bp_select_side")
    
    if selected_bp_option == "➕ Add New Bullpen Pitcher":
        current_bp_pitcher = st.sidebar.text_input("Enter Pitcher Name / #", value="Pitcher 1", key="bp_name_input")
    else:
        current_bp_pitcher = selected_bp_option

    with st.form("bullpen_form_v7", clear_on_submit=True):
        st.write(f"**Logging Bullpen Session for:** `{current_bp_pitcher}`")
        
        bp_col1, bp_col2 = st.columns(2)
        with bp_col1:
            bp_pitch_type = st.selectbox("Pitch Type", PITCH_ORDER, key="bp_type_v7")
        with bp_col2:
            bp_result = st.selectbox("Result", ["Strike", "Ball"], key="bp_result_v7")
            
        bp_submitted_v7 = st.form_submit_button("Log Pitch to Session 🎯")
        
        if bp_submitted_v7:
            try:
                supabase.table("pitch_logs").insert({
                    "mode": "Bullpen Charting",
                    "pitcher": current_bp_pitcher,
                    "batter": "Bullpen Session",
                    "count": "0-0",
                    "pitch_type": bp_pitch_type,
                    "result": bp_result,
                    "contact_type": "N/A", 
                    "hit_type": "N/A"      
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
                st.success("Successfully deleted the bullpen pitch!")
                st.rerun()
            else:
                st.warning("No bullpen pitches to undo.")
        except Exception as e:
            st.error(f"Error undoing bullpen pitch: {e}")

    st.markdown("---")
    st.subheader("📊 Bullpen Session Analytics")
    
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
            
            bp_pitches = pitcher_bp_df["pitch_type"].unique()
            sorted_bp_pitches = sort_pitch_series(bp_pitches)
            
            for p_type in sorted_bp_pitches:
                p_sub = pitcher_bp_df[pitcher_bp_df["pitch_type"] == p_type]
                p_total = len(p_sub)
                p_strikes = len(p_sub[p_sub["result"] == "Strike"])
                p_strike_pct = (p_strikes / p_total * 100) if p_total > 0 else 0.0
                
                st.markdown(f"**{p_type}** ({p_strike_pct:.1f}% | {p_strikes}/{p_total})")
                st.markdown(f"""
                <div class="glow-bar-container">
                    <div class="glow-bar-fill" style="width: {min(max(p_strike_pct, 2), 100)}%;"></div>
                </div>
                """, unsafe_allow_html=True)
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




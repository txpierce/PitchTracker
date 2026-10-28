import streamlit as st
import pandas as pd
from supabase import create_client
import time
import io
from datetime import datetime

# ReportLab imports for PDF generation
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

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

# Sidebar Mode Selection
st.sidebar.header("Navigation")
mode = st.sidebar.radio("Select Mode", [
    "Our Pitcher Tracker", 
    "Our Pitching Coach Dashboard", 
    "Opponent Pitcher Scout", 
    "Hitter On-Deck Cheat Sheet",
    "Bullpen Charting"
], key="main_navigation_radio")

# --- DUAL LINEUP SETUP ---
st.sidebar.markdown("---")
st.sidebar.header("📋 Lineup Configurations")

default_our_lineup = "Our Batter 1\nOur Batter 2\nOur Batter 3\nOur Batter 4\nOur Batter 5\nOur Batter 6\nOur Batter 7\nOur Batter 8\nOur Batter 9"
our_lineup_input = st.sidebar.text_area("Our Batting Lineup", value=default_our_lineup, height=120)
our_batters_list = [b.strip() for b in our_lineup_input.split("\n") if b.strip()]

default_opp_lineup = "Opponent Batter 1\nOpponent Batter 2\nOpponent Batter 3\nOpponent Batter 4\nOpponent Batter 5\nOpponent Batter 6\nOpponent Batter 7\nOpponent Batter 8\nOpponent Batter 9"
opp_lineup_input = st.sidebar.text_area("Opponent Batting Lineup", value=default_opp_lineup, height=120)
opp_batters_list = [b.strip() for b in opp_lineup_input.split("\n") if b.strip()]

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
    existing_items = list(series_or_index)
    sorted_list = [p for p in PITCH_ORDER if p in existing_items]
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
        total_strikes = len(p_sub[p_sub["result"].isin(["Called Strike", "Swinging Strike", "Chase Swing & Miss", "Chase Contact / Foul", "Foul", "In Play", "Strikeout"])])
        
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
    
    count_totals = pitcher_df["count"].value_counts().rename("Total Pitches")
    ct_table = pd.crosstab(pitcher_df["count"], pitcher_df["pitch_type"], normalize="index").mul(100).round(1)
    ct_table.insert(0, "Total Pitches", count_totals)
    
    existing_cols = [c for c in PITCH_ORDER if c in ct_table.columns]
    other_cols = [c for c in ct_table.columns if c not in existing_cols and c != "Total Pitches"]
    ct_table = ct_table[["Total Pitches"] + existing_cols + other_cols]
    
    formatted_table = ct_table.copy()
    for col in existing_cols + other_cols:
        formatted_table[col] = formatted_table[col].astype(str) + '%'
        
    column_config = {
        "count": st.column_config.TextColumn("Count", width="small"),
        "Total Pitches": st.column_config.NumberColumn("Total Pitches", width="small"),
    }
    for col in existing_cols + other_cols:
        column_config[col] = st.column_config.TextColumn(col, width="small")
        
    st.dataframe(formatted_table, use_container_width=True, column_config=column_config)

def calculate_coach_situational_metrics(pitcher_df):
    if pitcher_df.empty:
        return 0.0, 0.0, 0.0
    
    pa_list = []
    current_pa = []
    sorted_df = pitcher_df.sort_values(by="timestamp", ascending=True) if "timestamp" in pitcher_df.columns else pitcher_df
    
    for idx, row in sorted_df.iterrows():
        cnt = row["count"]
        if cnt == "0-0" and current_pa:
            pa_list.append(current_pa)
            current_pa = []
        current_pa.append(row)
    if current_pa:
        pa_list.append(current_pa)
        
    two_of_three_strikes_count = 0
    valid_pas_for_2of3 = 0
    
    for pa in pa_list:
        first_three = pa[:3]
        if len(first_three) >= 3:
            valid_pas_for_2of3 += 1
            strikes_in_first_3 = sum(1 for p in first_three if p["result"] in ["Called Strike", "Swinging Strike", "Chase Swing & Miss", "Chase Contact / Foul", "Foul", "In Play", "Strikeout"])
            if strikes_in_first_3 >= 2:
                two_of_three_strikes_count += 1
                
    two_of_three_pct = (two_of_three_strikes_count / valid_pas_for_2of3 * 100) if valid_pas_for_2of3 > 0 else 0.0
    
    ahead_even_counts = ["0-1", "0-2", "1-2", "1-1", "2-2"]
    ahead_even_df = pitcher_df[pitcher_df["count"].isin(ahead_even_counts)]
    total_non_00 = len(pitcher_df[pitcher_df["count"] != "0-0"])
    ahead_even_pct = (len(ahead_even_df) / total_non_00 * 100) if total_non_00 > 0 else 0.0
    
    behind_counts = ["1-0", "2-0", "3-0", "2-1", "3-1", "3-2"]
    behind_df = pitcher_df[pitcher_df["count"].isin(behind_counts)]
    total_pitches = len(pitcher_df)
    behind_pct = (len(behind_df) / total_pitches * 100) if total_pitches > 0 else 0.0
    
    return two_of_three_pct, ahead_even_pct, behind_pct

# --- PDF GENERATOR HELPERS ---
def generate_pdf_report(report_title, pitcher_name, stats_df):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    story = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=18, textColor=colors.HexColor("#1c83e1"), spaceAfter=6)
    subtitle_style = ParagraphStyle('SubTitleStyle', parent=styles['Normal'], fontSize=11, textColor=colors.HexColor("#555555"), spaceAfter=15)
    section_style = ParagraphStyle('SectionStyle', parent=styles['Heading2'], fontSize=14, textColor=colors.HexColor("#2a2a40"), spaceBefore=12, spaceAfter=6)
    body_style = ParagraphStyle('BodyStyle', parent=styles['Normal'], fontSize=10, textColor=colors.HexColor("#333333"), spaceAfter=4)
    
    story.append(Paragraph(f"⚾ TX_Pierce Report: {report_title}", title_style))
    story.append(Paragraph(f"<b>Subject:</b> {pitcher_name} &nbsp;|&nbsp; <b>Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#1c83e1"), spaceAfter=10))
    
    if stats_df.empty:
        story.append(Paragraph("No pitch data available for this report.", body_style))
    else:
        total_p = len(stats_df)
        two_3_pct, ah_ev_pct, bh_pct = calculate_coach_situational_metrics(stats_df)
        
        story.append(Paragraph(f"<b>Total Pitches Analyzed:</b> {total_p} &nbsp;|&nbsp; <b>2 Out of First 3 Strike %:</b> {two_3_pct:.1f}%", body_style))
        story.append(Paragraph(f"<b>Ahead / Even Count % (Excl. 0-0):</b> {ah_ev_pct:.1f}% &nbsp;|&nbsp; <b>Behind Count %:</b> {bh_pct:.1f}%", body_style))
        story.append(Spacer(1, 10))
        
        story.append(Paragraph("📊 Overall Pitch Mix Distribution", section_style))
        mix_counts = stats_df["pitch_type"].value_counts()
        mix_pcts = (stats_df["pitch_type"].value_counts(normalize=True) * 100).round(1)
        
        mix_data = [["Pitch Type", "Count", "Usage %"]]
        for pt in sort_pitch_series(mix_counts.index):
            mix_data.append([pt, str(mix_counts[pt]), f"{mix_pcts[pt]:.1f}%"])
            
        t_mix = Table(mix_data, colWidths=[200, 100, 100])
        t_mix.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#f0f2f6")),
            ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor("#2a2a40")),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('ALIGN', (1,0), (-1,-1), 'CENTER'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#dcdcdc"))
        ]))
        story.append(t_mix)
        story.append(Spacer(1, 15))
        
        story.append(Paragraph("🎯 Advanced Metrics Breakdown", section_style))
        adv_data = [["Pitch Type", "Thrown", "Total Strike %", "Whiff % (Swings)", "Called Strike %"]]
        
        for p_type in sort_pitch_series(stats_df["pitch_type"].unique()):
            p_sub = stats_df[stats_df["pitch_type"] == p_type]
            tp = len(p_sub)
            called_s = len(p_sub[p_sub["result"] == "Called Strike"])
            swing_s = len(p_sub[p_sub["result"].isin(["Swinging Strike", "Chase Swing & Miss"])])
            swings = len(p_sub[p_sub["result"].isin(["Swinging Strike", "Chase Swing & Miss", "Chase Contact / Foul", "Foul", "In Play"])])
            strikes = len(p_sub[p_sub["result"].isin(["Called Strike", "Swinging Strike", "Chase Swing & Miss", "Chase Contact / Foul", "Foul", "In Play", "Strikeout"])])
            
            cs_p = (called_s / tp * 100) if tp > 0 else 0.0
            wh_p = (swing_s / swings * 100) if swings > 0 else 0.0
            tot_s_p = (strikes / tp * 100) if tp > 0 else 0.0
            
            adv_data.append([p_type, str(tp), f"{tot_s_p:.1f}%", f"{wh_p:.1f}%", f"{cs_p:.1f}%"])
            
        t_adv = Table(adv_data, colWidths=[130, 70, 110, 110, 110])
        t_adv.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#f0f2f6")),
            ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor("#2a2a40")),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('ALIGN', (1,0), (-1,-1), 'CENTER'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#dcdcdc"))
        ]))
        story.append(t_adv)
        story.append(Spacer(1, 15))

        if "count" in stats_df.columns:
            story.append(Paragraph("📊 Pitch Type % Breakdown by Count", section_style))
            count_totals = stats_df["count"].value_counts()
            ct_table = pd.crosstab(stats_df["count"], stats_df["pitch_type"], normalize="index").mul(100).round(1)
            ct_table.insert(0, "Total Pitches", count_totals)
            
            existing_cols = [c for c in PITCH_ORDER if c in ct_table.columns]
            other_cols = [c for c in ct_table.columns if c not in existing_cols and c != "Total Pitches"]
            ct_table = ct_table[["Total Pitches"] + existing_cols + other_cols]
            
            ct_header = ["Count", "Total Pitches"] + existing_cols + other_cols
            ct_rows = [ct_header]
            for idx, row in ct_table.iterrows():
                row_data = [str(idx), str(int(row["Total Pitches"]))] + [f"{val:.1f}%" if pd.notnull(val) else "0.0%" for col_name, val in row.items() if col_name != "Total Pitches"]
                ct_rows.append(row_data)
                
            t_ct = Table(ct_rows)
            t_ct.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#f0f2f6")),
                ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor("#2a2a40")),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0,0), (-1,-1), 4),
                ('TOPPADDING', (0,0), (-1,-1), 4),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#dcdcdc"))
            ]))
            story.append(t_ct)

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

def generate_bullpen_pdf_report(pitcher_name, bullpen_df):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    story = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=18, textColor=colors.HexColor("#1c83e1"), spaceAfter=6)
    subtitle_style = ParagraphStyle('SubTitleStyle', parent=styles['Normal'], fontSize=11, textColor=colors.HexColor("#555555"), spaceAfter=15)
    section_style = ParagraphStyle('SectionStyle', parent=styles['Heading2'], fontSize=14, textColor=colors.HexColor("#2a2a40"), spaceBefore=12, spaceAfter=6)
    body_style = ParagraphStyle('BodyStyle', parent=styles['Normal'], fontSize=10, textColor=colors.HexColor("#333333"), spaceAfter=4)
    
    story.append(Paragraph("⚾ TX_Pierce Report: Bullpen Session Analysis", title_style))
    story.append(Paragraph(f"<b>Pitcher:</b> {pitcher_name} &nbsp;|&nbsp; <b>Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#1c83e1"), spaceAfter=10))
    
    if bullpen_df.empty:
        story.append(Paragraph("No bullpen session data available for this report.", body_style))
    else:
        total_p = len(bullpen_df)
        total_s = len(bullpen_df[bullpen_df["result"] == "Strike"])
        overall_pct = (total_s / total_p * 100) if total_p > 0 else 0.0
        
        story.append(Paragraph(f"<b>Total Pitches Thrown:</b> {total_p} &nbsp;|&nbsp; <b>Overall Strike %:</b> {overall_pct:.1f}% ({total_s}/{total_p})", body_style))
        story.append(Spacer(1, 10))
        
        story.append(Paragraph("📊 Strike % & Volume by Pitch Type", section_style))
        bp_data = [["Pitch Type", "Total Thrown", "Strikes", "Strike %"]]
        
        bp_pitches = bullpen_df["pitch_type"].unique()
        for p_type in sort_pitch_series(bp_pitches):
            p_sub = bullpen_df[bullpen_df["pitch_type"] == p_type]
            p_total = len(p_sub)
            p_strikes = len(p_sub[p_sub["result"] == "Strike"])
            p_strike_pct = (p_strikes / p_total * 100) if p_total > 0 else 0.0
            
            bp_data.append([p_type, str(p_total), str(p_strikes), f"{p_strike_pct:.1f}%"])
            
        t_bp = Table(bp_data, colWidths=[180, 100, 100, 120])
        t_bp.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#f0f2f6")),
            ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor("#2a2a40")),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('ALIGN', (1,0), (-1,-1), 'CENTER'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#dcdcdc"))
        ]))
        story.append(t_bp)

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

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
    
    if "prev_our_pitcher" not in st.session_state:
        st.session_state.prev_our_pitcher = selected_pitcher_option

    if selected_pitcher_option != st.session_state.prev_our_pitcher:
        st.session_state.prev_our_pitcher = selected_pitcher_option
        if "our_hitter_override_select" in st.session_state:
            del st.session_state["our_hitter_override_select"]

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
            hit_type = st.selectbox("Hit Outcome", [
                "N/A", "Ground Out", "Fly Out", "Line Out", "Pop Out", 
                "Single", "Double", "Triple", "Home Run"
            ], key="our_hit")
            
        btn_col1, btn_col2 = st.columns(2)
        with btn_col1:
            submitted = st.form_submit_button("Log Pitch & Advance Count")
        with btn_col2:
            complete_at_bat = st.form_submit_button("Complete At-Bat & Next Hitter ➔")
            
        if submitted:
            try:
                final_result = result
                final_hit_type = hit_type if result == "In Play" else "N/A"
                
                if st.session_state.our_pitcher_strikes == 2 and result in ["Called Strike", "Swinging Strike", "Chase Swing & Miss", "Foul", "Chase Contact / Foul"]:
                    if result in ["Called Strike", "Swinging Strike", "Chase Swing & Miss"]:
                        final_result = "Strikeout"
                        final_hit_type = "Strikeout"

                supabase.table("pitch_logs").insert({
                    "mode": "Our Pitcher Tracker",
                    "pitcher": current_our_pitcher,
                    "batter": current_batter,
                    "count": current_count_str,
                    "pitch_type": pitch_type,
                    "result": final_result,
                    "contact_type": contact_type if result == "In Play" else "N/A",
                    "hit_type": final_hit_type
                }).execute()
                
                is_strike_result = result in ["Called Strike", "Swinging Strike", "Chase Swing & Miss", "Foul", "Chase Contact / Foul"]
                is_ball_result = (result == "Ball")
                is_hbp = (result == "Hit By Pitch")
                is_in_play = (result == "In Play")

                new_strikes = st.session_state.our_pitcher_strikes
                new_balls = st.session_state.our_pitcher_balls

                if is_strike_result:
                    if result in ["Called Strike", "Swinging Strike", "Chase Swing & Miss"] and new_strikes == 2:
                        is_strikeout = True
                    else:
                        is_strikeout = False
                        if new_strikes < 2:
                            new_strikes += 1
                else:
                    is_strikeout = False

                if is_ball_result:
                    if new_balls == 3:
                        is_walk = True
                    else:
                        is_walk = False
                        new_balls += 1
                else:
                    is_walk = False

                if is_strikeout or is_walk or is_hbp or is_in_play:
                    st.session_state.our_pitcher_balls = 0
                    st.session_state.our_pitcher_strikes = 0
                    st.session_state.our_pitcher_batter_index = (st.session_state.our_pitcher_batter_index + 1) % len(opp_batters_list)
                    if "our_hitter_override_select" in st.session_state:
                        del st.session_state["our_hitter_override_select"]
                    st.success(f"At-bat ended! Advanced to next hitter: {opp_batters_list[st.session_state.our_pitcher_batter_index]}")
                else:
                    st.session_state.our_pitcher_strikes = new_strikes
                    st.session_state.our_pitcher_balls = new_balls
                    st.success(f"Logged {pitch_type} ({result}). Count is now {st.session_state.our_pitcher_balls}-{st.session_state.our_pitcher_strikes}")

                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Error logging pitch: {e}")

        elif complete_at_bat:
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
                
                st.session_state.our_pitcher_balls = 0
                st.session_state.our_pitcher_strikes = 0
                st.session_state.our_pitcher_batter_index = (st.session_state.our_pitcher_batter_index + 1) % len(opp_batters_list)
                
                if "our_hitter_override_select" in st.session_state:
                    del st.session_state["our_hitter_override_select"]
                    
                st.success(f"At-bat complete for {current_batter}! Advanced to next hitter.")
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Error completing at-bat: {e}")

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
            selected_view_pitcher = st.selectbox("Select Pitcher To View", our_df["pitcher"].unique(), key="view_our_pitcher")
            pitcher_df = our_df[our_df["pitcher"] == selected_view_pitcher]
            
            st.metric("Total Pitches Thrown", len(pitcher_df))
            
            if len(pitcher_df) > 0:
                col_a, col_b = st.columns(2)
                with col_a:
                    mix = pitcher_df["pitch_type"].value_counts(normalize=True) * 100
                    render_glowing_bars(mix, title_

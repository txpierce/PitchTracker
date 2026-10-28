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
            
        if submitted or complete_at_bat:
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
                
                if complete_at_bat or result in ["In Play", "Hit By Pitch"] or final_result == "Strikeout":
                    st.session_state.our_pitcher_balls = 0
                    st.session_state.our_pitcher_strikes = 0
                    st.session_state.our_pitcher_batter_index = (st.session_state.our_pitcher_batter_index + 1) % len(opp_batters_list)
                    
                    # FIXED: Delete the selectbox widget cache so it updates on rerun
                    if "our_hitter_override_select" in st.session_state:
                        del st.session_state["our_hitter_override_select"]
                        
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
            selected_view_pitcher = st.selectbox("Select Pitcher To View", our_df["pitcher"].unique(), key="view_our_pitcher")
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
            
            fp_strike_pct = 0.0
            fp_df = coach_pitcher_df[coach_pitcher_df["count"] == "0-0"]
            if not fp_df.empty:
                fp_strikes = len(fp_df[fp_df["result"].isin(["Called Strike", "Swinging Strike", "Chase Swing & Miss", "Chase Contact / Foul", "Foul", "In Play", "Strikeout"])])
                fp_strike_pct = (fp_strikes / len(fp_df)) * 100

            three_ball_pct = (len(coach_pitcher_df[coach_pitcher_df["count"].isin(["3-0", "3-1", "3-2"])]) / total_pitches * 100) if total_pitches > 0 else 0.0
            two_3_pct, ah_ev_pct, bh_pct = calculate_coach_situational_metrics(coach_pitcher_df)

            col_m1, col_m2 = st.columns(2)
            with col_m1:
                st.markdown(f"""
                <div class="metric-card">
                    <h3>🎯 1st-Pitch Strike % (FPS%)</h3>
                    <h2>{fp_strike_pct:.1f}%</h2>
                </div>
                """, unsafe_allow_html=True)
            with col_m2:
                st.markdown(f"""
                <div class="metric-card">
                    <h3>⚠️ 3-Ball Count Frequency</h3>
                    <h2>{three_ball_pct:.1f}%</h2>
                </div>
                """, unsafe_allow_html=True)

            col_cm1, col_cm2, col_cm3 = st.columns(3)
            with col_cm1:
                st.markdown(f"""
                <div class="metric-card">
                    <h3>🟢 2 Out of First 3 Strike %</h3>
                    <h2>{two_3_pct:.1f}%</h2>
                </div>
                """, unsafe_allow_html=True)
            with col_cm2:
                st.markdown(f"""
                <div class="metric-card">
                    <h3>🔵 Ahead / Even Count %</h3>
                    <h2>{ah_ev_pct:.1f}%</h2>
                    <p style="color: #a0a0c0; font-size: 11px; margin: 0;">(Excl. 0-0)</p>
                </div>
                """, unsafe_allow_html=True)
            with col_cm3:
                st.markdown(f"""
                <div class="metric-card">
                    <h3>⚠️ Behind Count %</h3>
                    <h2>{bh_pct:.1f}%</h2>
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

            st.markdown("---")
            st.subheader("👤 Individual Hitter Matchup & At-Bat Outcome Summary")
            
            logged_hitters = list(coach_pitcher_df["batter"].unique()) if "batter" in coach_pitcher_df.columns else []
            hitter_review_options = logged_hitters if logged_hitters else opp_batters_list
            
            if hitter_review_options:
                selected_review_hitter = st.selectbox("Select Opponent Hitter to Review Matchup", hitter_review_options, key="coach_hitter_review_select")
                hitter_matchup_df = coach_pitcher_df[coach_pitcher_df["batter"] == selected_review_hitter]
                
                if not hitter_matchup_df.empty:
                    st.metric(f"Total Pitches Thrown to {selected_review_hitter}", len(hitter_matchup_df))
                    
                    pa_outcomes = []
                    current_pa_pitches = []
                    sorted_hitter_df = hitter_matchup_df.sort_values(by="timestamp", ascending=True) if "timestamp" in hitter_matchup_df.columns else hitter_matchup_df
                    
                    for idx, row in sorted_hitter_df.iterrows():
                        cnt = row["count"]
                        res = row["result"]
                        hit_outcome = row["hit_type"] if "hit_type" in row else "N/A"
                        
                        if cnt == "0-0" and current_pa_pitches:
                            last_p = current_pa_pitches[-1]
                            if last_p["result"] == "Strikeout":
                                pa_outcomes.append("Strikeout")
                            elif last_p["result"] == "In Play":
                                pa_outcomes.append(last_p.get("hit_type", "Ground Out"))
                            elif last_p["result"] == "Hit By Pitch":
                                pa_outcomes.append("Hit By Pitch")
                            else:
                                pa_outcomes.append("Other / In-Progress")
                            current_pa_pitches = []
                        
                        current_pa_pitches.append(row)
                        
                        if res in ["In Play", "Hit By Pitch", "Strikeout"]:
                            if res == "Strikeout":
                                pa_outcomes.append("Strikeout")
                            elif res == "Hit By Pitch":
                                pa_outcomes.append("Hit By Pitch")
                            else:
                                pa_outcomes.append(hit_outcome if hit_outcome != "N/A" else "Ground Out")
                            current_pa_pitches = []
                            
                    if current_pa_pitches:
                        last_p = current_pa_pitches[-1]
                        if last_p["result"] == "Strikeout":
                            pa_outcomes.append("Strikeout")
                        elif last_p["result"] == "In Play":
                            pa_outcomes.append(last_p.get("hit_type", "Ground Out"))
                        elif last_p["result"] == "Hit By Pitch":
                            pa_outcomes.append("Hit By Pitch")
                        else:
                            pa_outcomes.append("In-Progress At-Bat")

                    if pa_outcomes:
                        st.write("### 🏆 At-Bat Outcome Summary")
                        outcome_counts = pd.Series(pa_outcomes).value_counts()
                        outcome_df = pd.DataFrame({"Outcome": outcome_counts.index, "Count": outcome_counts.values})
                        st.dataframe(outcome_df, use_container_width=True, hide_index=True)

                    hc1, hc2 = st.columns(2)
                    with hc1:
                        h_mix = hitter_matchup_df["pitch_type"].value_counts(normalize=True) * 100
                        render_glowing_bars(h_mix, title_text="Pitch Mix Faced by Hitter")
                    with hc2:
                        h_zz = hitter_matchup_df[hitter_matchup_df["count"] == "0-0"]
                        if not h_zz.empty:
                            render_glowing_bars(h_zz["pitch_type"].value_counts(normalize=True) * 100, title_text="0-0 Usage vs Hitter")
                        else:
                            st.info("No 0-0 pitches logged against this hitter.")
                            
                    render_clean_advanced_metrics(hitter_matchup_df)
                    render_table_count_breakdown(hitter_matchup_df)
                    
                    st.write("### 📝 Detailed Pitch Log History vs. Hitter")
                    display_cols = [c for c in ["timestamp", "count", "pitch_type", "result", "contact_type", "hit_type"] if c in hitter_matchup_df.columns]
                    st.dataframe(hitter_matchup_df[display_cols], use_container_width=True)
                else:
                    st.info(f"No logged pitch data found for {selected_review_hitter} against {coach_opp}.")
            else:
                st.info("No opponent batters available for review.")

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
    
    if "prev_opp_pitcher" not in st.session_state:
        st.session_state.prev_opp_pitcher = selected_opp_option

    if selected_opp_option != st.session_state.prev_opp_pitcher:
        st.session_state.prev_opp_pitcher = selected_opp_option
        if "opp_hitter_override_select" in st.session_state:
            del st.session_state["opp_hitter_override_select"]

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
            hit_type = st.selectbox("Hit Outcome", [
                "N/A", "Ground Out", "Fly Out", "Line Out", "Pop Out", 
                "Single", "Double", "Triple", "Home Run"
            ], key="scout_hit")
            
        btn_col1, btn_col2 = st.columns(2)
        with btn_col1:
            submitted = st.form_submit_button("Log Pitch & Advance Count")
        with btn_col2:
            complete_at_bat = st.form_submit_button("Complete At-Bat & Next Hitter ➔")
            
        if submitted or complete_at_bat:
            try:
                final_result = result
                final_hit_type = hit_type if result == "In Play" else "N/A"
                
                if st.session_state.opp_scout_strikes == 2 and result in ["Called Strike", "Swinging Strike", "Chase Swing & Miss", "Foul", "Chase Contact / Foul"]:
                    if result in ["Called Strike", "Swinging Strike", "Chase Swing & Miss"]:
                        final_result = "Strikeout"
                        final_hit_type = "Strikeout"

                supabase.table("pitch_logs").insert({
                    "mode": "Opponent Pitcher Scout",
                    "pitcher": current_opp_pitcher,
                    "batter": current_batter,
                    "count": current_count_str,
                    "pitch_type": pitch_type,
                    "result": final_result,
                    "contact_type": contact_type if result == "In Play" else "N/A",
                    "hit_type": final_hit_type
                }).execute()
                
                if complete_at_bat or result in ["In Play", "Hit By Pitch"] or final_result == "Strikeout":
                    st.session_state.opp_scout_balls = 0
                    st.session_state.opp_scout_strikes = 0
                    st.session_state.opp_scout_batter_index = (st.session_state.opp_scout_batter_index + 1) % len(our_batters_list)
                    
                    # FIXED: Delete the selectbox widget cache so it updates on rerun
                    if "opp_hitter_override_select" in st.session_state:
                        del st.session_state["opp_hitter_override_select"]
                        
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
                    deck_fp_strikes = len(deck_fp[deck_fp["result"].isin(["Called Strike", "Swinging Strike", "Chase Swing & Miss", "Chase Contact / Foul", "Foul", "In Play", "Strikeout"])])
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

# Sidebar Game Management, CSV, & PDF Export
st.sidebar.markdown("---")
st.sidebar.subheader("Game Management & Exports")

if not df.empty:
    st.sidebar.download_button(
        label="📥 Export Raw Logs (CSV)",
        data=df.to_csv(index=False).encode('utf-8'),
        file_name="TX_Pierce_Pitch_Logs_Export.csv",
        mime="text/csv",
    )
    
    if mode in ["Our Pitcher Tracker", "Our Pitching Coach Dashboard"]:
        active_mode_df = df[df["mode"] == "Our Pitcher Tracker"]
        current_target = st.session_state.get("selected_our_pitcher", "Pitcher")
        pitcher_report_df = active_mode_df[active_mode_df["pitcher"] == current_target] if not active_mode_df.empty else pd.DataFrame()
        pdf_bytes = generate_pdf_report("Our Pitcher Report", current_target, pitcher_report_df)
        
        st.sidebar.download_button(
            label="📄 Export Calculated PDF Report",
            data=pdf_bytes,
            file_name=f"TX_Pierce_{current_target.replace(' ', '_')}_Report.pdf",
            mime="application/pdf",
        )
    elif mode in ["Opponent Pitcher Scout", "Hitter On-Deck Cheat Sheet"]:
        active_mode_df = df[df["mode"] == "Opponent Pitcher Scout"]
        current_target = st.session_state.get("selected_opp_pitcher", "Opponent Pitcher")
        pitcher_report_df = active_mode_df[active_mode_df["pitcher"] == current_target] if not active_mode_df.empty else pd.DataFrame()
        pdf_bytes = generate_pdf_report("Opponent Scout Report", current_target, pitcher_report_df)
        
        st.sidebar.download_button(
            label="📄 Export Calculated PDF Report",
            data=pdf_bytes,
            file_name=f"TX_Pierce_Scout_{current_target.replace(' ', '_')}_Report.pdf",
            mime="application/pdf",
        )
    elif mode == "Bullpen Charting":
        active_mode_df = df[df["mode"] == "Bullpen Charting"]
        current_bp_target = locals().get("selected_bp_view", locals().get("current_bp_pitcher", "Bullpen Pitcher"))
        bullpen_report_df = active_mode_df[active_mode_df["pitcher"] == current_bp_target] if not active_mode_df.empty else pd.DataFrame()
        pdf_bytes = generate_bullpen_pdf_report(current_bp_target, bullpen_report_df)
        
        st.sidebar.download_button(
            label="📄 Export Calculated PDF Report",
            data=pdf_bytes,
            file_name=f"TX_Pierce_Bullpen_{current_bp_target.replace(' ', '_')}_Report.pdf",
            mime="application/pdf",
        )
else:
    st.sidebar.info("No data available to export.")

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

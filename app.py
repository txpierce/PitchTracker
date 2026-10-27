elif mode == "Our Pitcher Tracker":
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

    # Ensure session state for the selectbox widget exists
    if "our_mode_hitter_override" not in st.session_state:
        st.session_state.our_mode_hitter_override = opp_batters_list[0] if opp_batters_list else "Opponent Batter 1"

    st.sidebar.markdown("---")
    st.sidebar.header("🛠️ Scorekeeper Correction")
    
    if opp_batters_list:
        # Keep index bounded
        if st.session_state.our_pitcher_batter_index >= len(opp_batters_list):
            st.session_state.our_pitcher_batter_index = 0
            
        # Sync widget state with session index
        current_batter_name = opp_batters_list[st.session_state.our_pitcher_batter_index]
        
        manual_override_opp = st.sidebar.selectbox(
            "Override Current Opponent Hitter", 
            opp_batters_list, 
            index=st.session_state.our_pitcher_batter_index,
            key="our_mode_hitter_override"
        )
        
        # If user manually changed it via sidebar dropdown
        selected_index = opp_batters_list.index(manual_override_opp)
        if selected_index != st.session_state.our_pitcher_batter_index:
            st.session_state.our_pitcher_batter_index = selected_index

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

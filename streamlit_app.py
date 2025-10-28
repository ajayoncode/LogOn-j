import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import re
from pathlib import Path
from session_manager import session_manager
from streamlit.components.v1 import html
from string import Template

# Try to import plotly, but make it optional
try:
    import plotly.express as px
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

# Page configuration
st.set_page_config(
    page_title="LogOn",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .project-header {
        font-size: 1.5rem;
        font-weight: bold;
        color: #2e8b57;
        margin-top: 2rem;
        margin-bottom: 1rem;
        padding: 0.5rem;
        background-color: #f0f8ff;
        border-left: 4px solid #2e8b57;
    }
    /* Center align Date & Time column */
    .dataframe th:nth-child(1),
    .dataframe td:nth-child(1) {
        text-align: center !important;
    }
    /* Left align Total Minutes column */
    .dataframe th:nth-child(4),
    .dataframe td:nth-child(4) {
        text-align: left !important;
    }
    /* Left align all project breakdown columns */
    .dataframe th:nth-child(2),
    .dataframe td:nth-child(2),
    .dataframe th:nth-child(3),
    .dataframe td:nth-child(3),
    .dataframe th:nth-child(4),
    .dataframe td:nth-child(4),
    .dataframe th:nth-child(5),
    .dataframe td:nth-child(5) {
        text-align: left !important;
    }
    /* Consistent info-like box for custom fields */
    .info-box {
        background-color: #1f2d3d; /* dark blue similar to st.info */
        color: #d1e3f8;
        padding: 0.75rem 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0 0.5rem 0;
    }
    .info-box strong { color: #69aaf0; }
</style>
""", unsafe_allow_html=True)




def create_session_controls():
    """Create session control interface"""
    st.subheader("🎮 Session Controls")
    
    # Initialize session manager if not running
    if not session_manager.running:
        session_manager.start_monitoring()
    
    # Get current session status
    current_session = session_manager.get_current_session_status()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**Current Session Status**")
        if current_session:
            st.success(f"👤 {current_session['type'].title()} Session Active")
            st.info(f"**Project:** {current_session['project']}")
            st.info(f"**Goal:** {current_session['goal']}")
            st.info(f"**Started:** {current_session['start_time']}")

            # Duration in the same UI style as others, with live-updatable span
            now_seconds = int(datetime.now(ZoneInfo('Asia/Kolkata')).timestamp())
            elapsed = max(0, now_seconds - int(current_session.get('start_epoch', 0)))
            mm = str(elapsed // 60).zfill(2)
            ss = str(elapsed % 60).zfill(2)
            st.markdown(f"**Duration:** <span id=\"duration-display\">{mm}:{ss}</span>", unsafe_allow_html=True)
            start_epoch = int(current_session.get('start_epoch', 0))
            paused_flag = 1 if bool(current_session.get('paused', False)) else 0
            effective_elapsed = int(current_session.get('effective_elapsed', 0))
            script = Template(
                """
                <script>
                (function() {
                  const startEpoch = $start_epoch;
                  const baseTitle = 'LogOn ';
                  const pausedInit = $paused_flag === 1;
                  const effectiveInit = $effective_elapsed; // seconds
                  // Derive a base epoch for effective elapsed time when running
                  let baseEffectiveEpoch = Math.floor(Date.now()/1000) - effectiveInit;
                  // Persist pause state across script reloads
                  try { window.parent.__logonPaused = pausedInit; } catch(e){}
                  try { window.parent.__logonEffective = effectiveInit; } catch(e){}
                  function fmtSeconds(totalSeconds){
                    const mm = String(Math.floor(totalSeconds/60)).padStart(2,'0');
                    const ss = String(totalSeconds%60).padStart(2,'0');
                    return mm + ':' + ss;
                  }
                  function tick(){
                    if(!startEpoch) return;
                    const isPaused = !!(window.parent && window.parent.__logonPaused);
                    let sec;
                    if (isPaused) {
                      sec = (window.parent && typeof window.parent.__logonEffective === 'number') ? window.parent.__logonEffective : effectiveInit;
                    } else {
                      const now = Math.floor(Date.now()/1000);
                      sec = Math.max(0, now - baseEffectiveEpoch);
                      try { window.parent.__logonEffective = sec; } catch(e){}
                    }
                    const text = fmtSeconds(sec);
                    const el = window.parent.document.getElementById('duration-display');
                    if (el) { el.textContent = text; }
                    try { window.parent.document.title = '⏱ ' + text + ' - ' + baseTitle; } catch(e){}
                  }
                  tick();
                  if(!window.parent.__logonTimer){ window.parent.__logonTimer = setInterval(tick, 1000); }
                })();
                </script>
                """
            ).substitute(start_epoch=start_epoch, paused_flag=paused_flag, effective_elapsed=effective_elapsed)
            html(script, height=0)
        else:
            st.warning("No active session")
            # Reset tab title when no session
            html(
                """
                <script>
                (function(){
                  try { if (window.parent.__logonTimer) { clearInterval(window.parent.__logonTimer); window.parent.__logonTimer = null; } } catch(e){}
                  try { window.parent.document.title = 'LogOn Dashboard'; } catch(e){}
                })();
                </script>
                """,
                height=0,
            )
    
    with col2:
        st.markdown("**Manual Session Controls**")
        
        # Project selection
        verticals = session_manager.get_verticals()
        selected_project = st.selectbox("Select Project", verticals, key="manual_project")
        
        # Goal input
        goal_text = st.text_area("Enter Goal", placeholder="What are you working on?", key="manual_goal")
        
        # Start manual session button
        if st.button("🚀 Start Manual Session", disabled=not goal_text.strip()):
            if session_manager.start_manual_session(selected_project, goal_text.strip()):
                st.success("Manual session started!")
                st.rerun()
            else:
                st.error("Failed to start manual session")
    
    with col3:
        st.markdown("**Session Actions**")
        
        if current_session:
            is_paused = bool(current_session.get('paused', False))
            col_a, col_b = st.columns(2)
            with col_a:
                if not is_paused:
                    if st.button("⏸️ Pause"):
                        if session_manager.pause_session():
                            st.success("Session paused")
                            st.rerun()
                        else:
                            st.error("Failed to pause session")
                else:
                    if st.button("▶️ Resume"):
                        if session_manager.resume_session():
                            st.success("Session resumed")
                            st.rerun()
                        else:
                            st.error("Failed to resume session")
            with col_b:
                if st.button("⏹️ Stop"):
                    if session_manager.stop_current_session():
                        st.success("Session stopped")
                        st.rerun()
                    else:
                        st.error("Failed to stop session")

def create_daily_hours_graph(df):
    """Create a line graph showing daily total hours"""
    if not PLOTLY_AVAILABLE:
        return None
        
    if df.empty:
        return None
    
    # Use the passed dataframe directly (it now contains both original and display columns)
    raw_df = df.copy()
    
    # Convert datetime columns
    if 'start_time' in raw_df.columns:
        raw_df['start_time'] = pd.to_datetime(raw_df['start_time'], errors='coerce', utc=True).dt.tz_convert('Asia/Kolkata')
    if 'duration_minutes' in raw_df.columns:
        raw_df['duration_minutes'] = pd.to_numeric(raw_df['duration_minutes'], errors='coerce')
    
    # Group by IST date and sum duration in hours
    daily_data = raw_df.groupby(raw_df['start_time'].dt.tz_convert('Asia/Kolkata').dt.date)['duration_minutes'].sum() / 60
    daily_data = daily_data.reset_index()
    daily_data.columns = ['date', 'total_hours']
    
    # Sort by date
    daily_data = daily_data.sort_values('date')
    
    # Create the plotly figure
    fig = go.Figure()
    
    # Add line with wave effect
    fig.add_trace(go.Scatter(
        x=daily_data['date'],
        y=daily_data['total_hours'],
        mode='lines+markers',
        line=dict(
            shape='spline',  # Creates wave-like smooth curves
            smoothing=0.3,
            width=3,
            color='#1f77b4'
        ),
        marker=dict(
            size=8,
            color='#ff7f0e',
            line=dict(width=2, color='white')
        ),
        name='Daily Hours',
        hovertemplate='<b>%{x}</b><br>Total Hours: %{y:.2f}<extra></extra>'
    ))

    # Add average horizontal line
    if len(daily_data) > 0:
        avg_hours = daily_data['total_hours'].mean()
        fig.add_hline(
            y=avg_hours,
            line=dict(color='rgba(31, 119, 180, 0.4)', width=2, dash='dash'),
            annotation_text=f"Avg: {avg_hours:.2f}h",
            annotation_position="top left"
        )
    
    # Update layout
    fig.update_layout(
        title={
            'text': 'Daily Total Hours',
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 20}
        },
        xaxis_title='Date',
        yaxis_title='Total Hours',
        hovermode='x unified',
        template='plotly_white',
        height=400,
        margin=dict(l=50, r=50, t=60, b=50)
    )
    
    # Format x-axis to show dates nicely
    fig.update_xaxes(
        tickformat='%b %d',
        tickangle=45
    )
    
    # Format y-axis to show hours with 1 decimal place
    fig.update_yaxes(
        tickformat='.1f'
    )
    
    return fig

def load_session_data_from_csv():
    """Load session data from the unified CSV file"""
    csv_file = "logger_data/sessions.csv"
    
    if not os.path.exists(csv_file):
        return pd.DataFrame()
    
    try:
        # Use pandas read_csv with proper handling of commas in goal field
        df = pd.read_csv(csv_file, encoding='utf-8')
        
        if df.empty:
            return df
        
        # Convert datetime columns - robust to timezone-aware or naive strings
        if 'start_time' in df.columns:
            start_parsed = pd.to_datetime(df['start_time'], errors='coerce')
            if start_parsed.dt.tz is None:
                df['start_time'] = start_parsed.dt.tz_localize('Asia/Kolkata')
            else:
                df['start_time'] = start_parsed.dt.tz_convert('Asia/Kolkata')
        if 'end_time' in df.columns:
            # Handle empty end_time values for in_progress sessions
            end_parsed = pd.to_datetime(df['end_time'], errors='coerce')
            if end_parsed.notna().any():
                if end_parsed.dt.tz is None:
                    df['end_time'] = end_parsed.dt.tz_localize('Asia/Kolkata')
                else:
                    df['end_time'] = end_parsed.dt.tz_convert('Asia/Kolkata')
        # Convert duration_minutes to numeric, handling any string values
        if 'duration_minutes' in df.columns:
            df['duration_minutes'] = pd.to_numeric(df['duration_minutes'], errors='coerce')
            # Fill NaN duration values with 0 for in_progress sessions
            df['duration_minutes'] = df['duration_minutes'].fillna(0)
        
        # Sort by start_time in descending order (latest to oldest)
        df = df.sort_values('start_time', ascending=False)
        
        # Create display columns while preserving original columns
        df['Date & Time'] = df['start_time'].dt.strftime('%d %b %Y %H:%M')
        df['Duration'] = df['duration_minutes'].apply(lambda x: f"{x:.1f} min" if pd.notna(x) else "0.0 min")
        df['Status'] = df['status'].str.replace('_', ' ').str.title()
        df['Type'] = df['session_type'].str.title()
        df['Project'] = df['project']
        df['Goal'] = df['goal']
        
        return df
    except Exception as e:
        st.error(f"Error loading session data: {e}")
        return pd.DataFrame()

def main():
    # Header
    st.markdown('<h1 class="main-header">Logon</h1>', unsafe_allow_html=True)
    
    # Session Controls
    create_session_controls()
    
    # Load session data from CSV
    st.subheader("📈 Session Data")
    
    df = load_session_data_from_csv()
    
    
    if not df.empty:
        # Use the loaded dataframe directly (it now contains both original and display columns)
        raw_df = df.copy()
        if 'start_time' in raw_df.columns:
            # Parse any stored timezone info; if naive, localize to IST
            parsed = pd.to_datetime(raw_df['start_time'], errors='coerce')
            # If timezone-naive, assign IST; otherwise convert to IST
            if parsed.dt.tz is None:
                raw_df['start_time'] = parsed.dt.tz_localize('Asia/Kolkata')
            else:
                raw_df['start_time'] = parsed.dt.tz_convert('Asia/Kolkata')
        if 'duration_minutes' in raw_df.columns:
            raw_df['duration_minutes'] = pd.to_numeric(raw_df['duration_minutes'], errors='coerce')
        
        # Add filters
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Project filter
            projects = ['All'] + sorted(df['Project'].unique().tolist())
            selected_project = st.selectbox("Filter by Project", projects)
            
        with col2:
            # Session type filter
            session_types = ['All'] + sorted(df['Type'].unique().tolist())
            selected_type = st.selectbox("Filter by Type", session_types)
            
        with col3:
            # Date range filter
            if len(raw_df) > 1 and not raw_df['start_time'].isna().all():
                min_date = raw_df['start_time'].min().date()
                max_date = raw_df['start_time'].max().date()
                date_range = st.date_input(
                    "Select Date Range",
                    value=(min_date, max_date),
                    min_value=min_date,
                    max_value=max_date
                )
            else:
                date_range = None
        
        # Apply filters to raw data first
        filtered_raw_df = raw_df.copy()
        if selected_project != 'All':
            # Normalize project comparison to avoid hidden whitespace/case issues
            filtered_raw_df = filtered_raw_df[
                filtered_raw_df['project'].astype(str).str.strip() == str(selected_project).strip()
            ]
        
        if selected_type != 'All':
            # Normalize type comparison (case/whitespace) to match values like 'auto'
            filtered_raw_df = filtered_raw_df[
                filtered_raw_df['session_type'].astype(str).str.strip().str.lower() == selected_type.strip().lower()
            ]
        
        if date_range and len(date_range) == 2:
            # Convert selected dates to timezone-aware timestamps in Asia/Kolkata
            start_date = pd.Timestamp(date_range[0], tz='Asia/Kolkata')
            # Include full end day by moving to next day start and using '<'
            end_date_exclusive = pd.Timestamp(date_range[1], tz='Asia/Kolkata') + pd.Timedelta(days=1)
            filtered_raw_df = filtered_raw_df[
                (filtered_raw_df['start_time'] >= start_date) &
                (filtered_raw_df['start_time'] < end_date_exclusive)
            ]
        
        # Create display dataframe from filtered raw data
        if not filtered_raw_df.empty:
            # The display columns are already created in the load_session_data_from_csv function
            # Just select the display columns
            display_columns = ['Date & Time', 'Project', 'Goal', 'Duration', 'Type', 'Status']
            filtered_df = filtered_raw_df[display_columns].copy()
        else:
            filtered_df = pd.DataFrame()
        
        # Summary statistics
        st.subheader("📊 Summary Statistics")
        col1, col2, col3, col4 = st.columns(4)
        
        # Use the already filtered raw data for calculations
        if not filtered_raw_df.empty:
            with col1:
                total_minutes = filtered_raw_df['duration_minutes'].sum()
                st.metric("Total Time (minutes)", f"{total_minutes:.1f}")
            
            with col2:
                total_hours = total_minutes / 60
                st.metric("Total Time (hours)", f"{total_hours:.1f}")
            
            with col3:
                avg_time = filtered_raw_df['duration_minutes'].mean()
                st.metric("Average Session (minutes)", f"{avg_time:.1f}")
            
            with col4:
                session_count = len(filtered_raw_df)
                st.metric("Total Sessions", session_count)
        
        # Daily Hours Graph
        st.subheader("📈 Daily Hours Trend")
        daily_graph = create_daily_hours_graph(df)
        if daily_graph:
            st.plotly_chart(daily_graph, use_container_width=True)
        elif not PLOTLY_AVAILABLE:
            st.info("📊 Graph feature requires plotly. Install with: pip install plotly")
        else:
            st.info("No data available for the daily hours graph.")
        
        # Project breakdown
        if not filtered_raw_df.empty and len(filtered_raw_df['project'].unique()) > 1:
            st.subheader("📋 Project Breakdown")
            
            # Use filtered raw data for calculations
            breakdown_df = filtered_raw_df.groupby('project').agg({
                'duration_minutes': ['sum', 'mean', 'count']
            }).round(2)
            breakdown_df.columns = ['Total Minutes', 'Avg Minutes', 'Sessions']
            
            # Add Total Hours column
            breakdown_df['Total Hours'] = (breakdown_df['Total Minutes'] / 60).round(2)
            
            # Reorder columns
            breakdown_df = breakdown_df[['Total Minutes', 'Total Hours', 'Avg Minutes', 'Sessions']]
            
            # Format the values for better readability
            formatted_breakdown = breakdown_df.copy()
            formatted_breakdown['Total Minutes'] = formatted_breakdown['Total Minutes'].apply(lambda x: f"{int(x)} min")
            formatted_breakdown['Total Hours'] = formatted_breakdown['Total Hours'].apply(lambda x: f"{x:.1f} hrs")
            formatted_breakdown['Avg Minutes'] = formatted_breakdown['Avg Minutes'].apply(lambda x: f"{int(x)} min")
            formatted_breakdown['Sessions'] = formatted_breakdown['Sessions'].apply(lambda x: f"{int(x)} sessions")
            
            st.dataframe(formatted_breakdown, width='stretch')
        
        # Display the session data
        st.subheader("📋 Session History")
        if not filtered_df.empty:
            st.dataframe(filtered_df, width='stretch')
        else:
            st.info("No sessions found matching the selected filters.")
        
        # Download CSV option
        csv_data = filtered_df.to_csv(index=False)
        st.download_button(
            label="📥 Download CSV",
            data=csv_data,
            file_name="logon_sessions.csv",
            mime="text/csv"
        )
    else:
        st.warning("No session data available. Start a session to see data here.")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import redis
import json
import logging
from datetime import datetime
import os
import plotly.express as px

# Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Setup Validation
@st.cache_resource
def get_redis_client():
    """Cached Redis connection (reused across requests)."""
    try:
        if "redis" in REDIS_URL:
            r = redis.Redis.from_url(REDIS_URL, decode_responses=True)
            r.ping()
            return r
        return None
    except Exception as e:
        logging.error(f"Redis connect error: {e}")
        return None

r_client = get_redis_client()

def get_stream_data(redis_client, stream_key, count=100):
    """Fetch structured data from Redis Stream."""
    if not redis_client:
        return []
    try:
        data = redis_client.xrevrange(stream_key, count=count)
        parsed = []
        for msg_id, payload in data:
            if isinstance(payload, dict):
                 # Handle potentially stringified json in 'data' field or flattened fields
                 if 'data' in payload and isinstance(payload['data'], str):
                     try:
                         item = json.loads(payload['data'])
                     except:
                         item = payload
                 else:
                     item = payload
                 
                 item['id'] = msg_id
                 parsed.append(item)
        return parsed
    except Exception as e:
        logging.error(f"Stream read error: {e}")
        return []

def get_queue_metrics(redis_client):
    """
    Get detailed queue metrics with correct semantics.
    
    Returns:
        dict with keys:
        - stream_length: Total messages in stream (historical)
        - lag: Messages not yet delivered to consumer group
        - in_flight: Messages delivered but not ACKed
        - oldest_pending_ms: Idle time of oldest unacked message
        - analyzed_count: Total in papers:analyzed
        - last_processed_id: Last doc processed by agent_core
        - last_processed_ts: Timestamp of last processing
    """
    metrics = {
        'stream_length': 0,
        'lag': 0,
        'in_flight': 0,
        'oldest_pending_ms': 0,
        'analyzed_count': 0,
        'last_processed_id': None,
        'last_processed_ts': None,
    }
    
    if not redis_client:
        return metrics
    
    try:
        # Stream length (historical)
        metrics['stream_length'] = redis_client.xlen("papers:pending") or 0
        metrics['analyzed_count'] = redis_client.xlen("papers:analyzed") or 0
        
        # Get consumer group info for lag
        try:
            groups = redis_client.xinfo_groups("papers:pending")
            for g in groups:
                if g.get('name') == 'agent_group':
                    metrics['lag'] = g.get('lag', 0) or 0
                    break
        except redis.ResponseError:
            pass  # No consumer group exists
        
        # Get pending (in-flight) messages
        try:
            pending_info = redis_client.xpending("papers:pending", "agent_group")
            if pending_info:
                metrics['in_flight'] = pending_info.get('pending', 0) or 0
                # Get oldest pending idle time
                if metrics['in_flight'] > 0:
                    pending_details = redis_client.xpending_range(
                        "papers:pending", "agent_group", "-", "+", 1
                    )
                    if pending_details:
                        metrics['oldest_pending_ms'] = pending_details[0].get('time_since_delivered', 0)
        except redis.ResponseError:
            pass  # No consumer group or no pending
        
        # Get heartbeat from agent_core
        metrics['last_processed_id'] = redis_client.get("agent_core:last_doc_id")
        metrics['last_processed_ts'] = redis_client.get("agent_core:last_processed_ts")
        
    except Exception as e:
        logging.error(f"Error getting queue metrics: {e}")
    
    return metrics


def get_queue_status(metrics):
    """
    Determine queue status based on metrics.
    
    Returns:
        tuple: (emoji, status_text, color)
        - Green: lag=0, in_flight=0 (complete)
        - Yellow: lag>0 or in_flight>0 (processing)
        - Red: in_flight>0 and oldest_pending_ms > 10min (stuck)
    """
    STUCK_THRESHOLD_MS = 10 * 60 * 1000  # 10 minutes
    
    lag = metrics.get('lag', 0)
    in_flight = metrics.get('in_flight', 0)
    oldest_ms = metrics.get('oldest_pending_ms', 0)
    
    if in_flight > 0 and oldest_ms > STUCK_THRESHOLD_MS:
        return "🔴", "Stuck", "red"
    elif lag > 0 or in_flight > 0:
        return "🟡", "Processing", "yellow"
    else:
        return "🟢", "Complete", "green"

# --- Sidebar Setup ---
def setup_sidebar():
    """Setup sidebar ONCE - call this function only at app start."""
    st.sidebar.title("🛡️ AI Safety Radar")
    
    if st.sidebar.button("🔄 Refresh Data", help="Reload all dashboard data from Redis", use_container_width=True):
        st.rerun()
        
    st.sidebar.markdown("---")
    
    # System Status Section
    st.sidebar.subheader("📊 System Status")
    
    # Redis Status
    if r_client:
        st.sidebar.markdown("🟢 **Redis:** Connected")
    else:
        st.sidebar.markdown("🔴 **Redis:** Disconnected")
        
    # Queue Metrics with correct semantics
    if r_client:
        metrics = get_queue_metrics(r_client)
        emoji, status_text, color = get_queue_status(metrics)
        
        st.sidebar.markdown(f"{emoji} **Queue Status:** {status_text}")
        
        # Detailed queue metrics
        st.sidebar.markdown(f"""        
**Stream length (historical):** {metrics['stream_length']}  
**Remaining to process (lag):** {metrics['lag']}  
**In-flight (unacked):** {metrics['in_flight']}  
**Analyzed total:** {metrics['analyzed_count']}
        """)
        
        # Heartbeat info
        if metrics['last_processed_ts']:
            st.sidebar.caption(f"Last processed: {metrics['last_processed_ts']}")
    else:
        st.sidebar.markdown("⚪ **Queue Status:** Unknown")
    
    # Status Reference (clean markdown)
    with st.sidebar.expander("ℹ️ Status Reference"):
        st.markdown("""
**Queue Status:**
- 🟢 Complete: lag=0, in_flight=0
- 🟡 Processing: lag>0 or in_flight>0
- 🔴 Stuck: in_flight>0 for >10 minutes

**Metrics Explained:**
- **Stream length**: Total messages ever (historical)
- **Lag**: Messages not yet delivered to consumer
- **In-flight**: Delivered but not acknowledged
- **Analyzed**: Successfully processed papers
        """)
        
    st.sidebar.markdown("---")
    
    # Manual Controls Section
    st.sidebar.subheader("🎮 Manual Controls")
    
    if r_client:
        if st.sidebar.button("📥 Trigger Ingestion", help="Fetch latest AI security papers (30s)", use_container_width=True):
            r_client.publish("agent:trigger", "ingest")
            st.sidebar.success("✅ Started")
            
        if st.sidebar.button("⚙️ Process Queue", help="Force process pending papers", use_container_width=True):
            r_client.publish("agent:trigger", "process_all")
            st.sidebar.success("✅ Started")
            
        if st.sidebar.button("🗑️ Clear & Reset", help="⚠️ Delete all data", use_container_width=True):
            if st.sidebar.checkbox("Confirm Delete"):
                r_client.delete("papers:analyzed")
                r_client.delete("curator:latest_summary")
                st.sidebar.warning("⚠️ Cleared")
                st.rerun()
        
        # Maintenance: Trim processed history
        with st.sidebar.expander("🔧 Maintenance"):
            st.caption("Trim old messages from streams (keeps recent N)")
            trim_count = st.number_input("Keep last N messages", min_value=10, max_value=1000, value=100)
            if st.button("Trim papers:pending", help="Remove old processed messages"):
                try:
                    trimmed = r_client.xtrim("papers:pending", maxlen=trim_count, approximate=True)
                    st.success(f"Trimmed {trimmed} messages")
                    st.rerun()
                except Exception as e:
                    st.error(f"Trim failed: {e}")
    else:
        st.sidebar.error("Controls disabled (No Redis)")

# --- Main App Entry Point ---
def main():
    # Page Config
    st.set_page_config(
        page_title="AI Safety Radar",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Setup Sidebar ONCE
    setup_sidebar()
    
    # Check Data
    analyzed_threats = get_stream_data(r_client, "papers:analyzed")
    pending_papers = get_stream_data(r_client, "papers:pending")
    
    # Prepare DataFrame
    df = pd.DataFrame()
    if analyzed_threats:
        df = pd.DataFrame(analyzed_threats)
        if 'severity' not in df.columns:
            df['severity'] = 'Unknown'
        else:
            # Normalize severity for display/sorting
            df['severity'] = df['severity'].astype(str).fillna('Unknown')

    # Tab Navigation
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Overview", "📚 Threat Catalog", "🧠 SOTA Tracker", "🔒 Security Status"])
    
    # --- Tab 1: Overview ---
    with tab1:
        st.header("📊 Threat Landscape Overview")
        
        # Metrics
        col1, col2, col3 = st.columns(3)
        total = len(df)
        
        # Use XLEN for total stream counts (simpler, matches Redis state)
        pending_len = 0
        if r_client:
            try:
                pending_len = r_client.xlen("papers:pending")
            except:
                pending_len = 0
        
        critical = 0
        if not df.empty and 'severity' in df.columns:
            critical = len(df[df['severity'].isin(['Critical', 'High', '4', '5'])])
            
        col1.metric("Total Threats", total)
        # Get lag safely
        lag_val = 0
        if r_client:
            try:
                groups = r_client.xinfo_groups("papers:pending")
                if groups:
                    lag_val = groups[0].get('lag', 0) or 0
            except:
                pass
        col2.metric("Remaining (lag)", lag_val)
        col3.metric("Critical Risks", critical)
        
        st.markdown("---")
        
        # Recent Activity Table
        if not df.empty:
            col_recent, col_charts = st.columns([1, 1])
            
            with col_recent:
                st.subheader("🎯 Recent Threats")
                display_cols = ['title', 'attack_type', 'severity', 'published_date']
                # Filter columns that exist
                cols = [c for c in display_cols if c in df.columns]
                st.dataframe(df[cols].head(5), use_container_width=True, hide_index=True)
            
            with col_charts:
                st.subheader("Severity Distribution")
                # Plotly Pie Chart
                fig_sev = px.pie(df, names='severity', title='Threat Severity Breakdown', hole=0.4, 
                         color='severity',
                         color_discrete_map={'Critical': 'red', 'High': 'orange', 'Medium': 'yellow', 'Low': 'green'})
                st.plotly_chart(fig_sev, use_container_width=True)
            
            # Timeline Chart
            if 'published_date' in df.columns:
                 st.subheader("Threat Activity Timeline")
                 try:
                     df_time = df.copy()
                     df_time['published_date'] = pd.to_datetime(df_time['published_date'])
                     counts_by_date = df_time.groupby(df_time['published_date'].dt.date).size().reset_index(name='count')
                     fig_time = px.bar(counts_by_date, x='published_date', y='count', title='Threats by Date')
                     st.plotly_chart(fig_time, use_container_width=True)
                 except Exception as e:
                     st.warning(f"Could not render timeline: {e}")

        else:
            st.info("📭 No data available. Trigger ingestion from sidebar to start monitoring.")

    # --- Tab 2: Threat Catalog ---
    with tab2:
        st.header("📚 Threat Catalog")
        if not df.empty:
            # Filter UI
            col_search, col_filter = st.columns([3, 1])
            with col_search:
                 search = st.text_input("🔍 Search threats", "")
            with col_filter:
                 sev_options = df['severity'].unique().tolist()
                 sev_filter = st.multiselect("Severity", sev_options, default=sev_options)
            
            # Apply Filters
            df_display = df.copy()
            if search:
                mask = df_display.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)
                df_display = df_display[mask]
            
            if sev_filter:
                df_display = df_display[df_display['severity'].isin(sev_filter)]
            
            # Interactive Dataframe
            cols_to_show = ['title', 'severity', 'attack_type', 'published_date']
            for c in cols_to_show:
                if c not in df_display.columns: df_display[c] = "N/A"
                
            event = st.dataframe(
                df_display[cols_to_show], 
                use_container_width=True, 
                selection_mode="single-row",
                on_select="rerun",
                hide_index=True
            )
            
            # Detail View (3-Tab Layout Re-implemented)
            if event.selection and event.selection.rows:
                idx = event.selection.rows[0]
                if idx < len(df_display):
                    threat_data = df_display.iloc[idx].to_dict()
                    
                    st.markdown("---")
                    st.subheader(f"📄 {threat_data.get('title', 'Unknown Title')}")
                    
                    d_tab1, d_tab2, d_tab3 = st.tabs(["📝 Summary", "🔬 Methodology", "📊 Raw Data"])
                    
                    with d_tab1: # Summary Tab
                         col_meta1, col_meta2 = st.columns(2)
                         col_meta1.markdown(f"**Published:** {threat_data.get('published_date', 'N/A')}")
                         col_meta1.markdown(f"**Severity:** {threat_data.get('severity', 'N/A')}")
                         col_meta2.markdown(f"**Type:** {threat_data.get('attack_type', 'N/A')}")
                         col_meta2.markdown(f"**Source:** {threat_data.get('source', 'arxiv')}")
                         
                         st.info(f"**TL;DR:** {threat_data.get('summary_tldr', 'N/A')}")
                         
                         st.markdown("#### Detailed Analysis")
                         st.write(threat_data.get('summary_detailed', 'Not available.'))
                         
                         st.markdown("#### Key Findings")
                         findings = threat_data.get('key_findings', [])
                         if isinstance(findings, list):
                             for f in findings: st.markdown(f"- {f}")
                         else:
                             st.write(str(findings))

                         if threat_data.get('code_repository'):
                             st.markdown(f"🔗 [Code Repository]({threat_data['code_repository']})")

                    with d_tab2: # Methodology Tab
                         st.markdown("#### Methodology Brief")
                         st.write(threat_data.get('methodology_brief', 'N/A'))
                         
                         st.markdown("#### Affected Models")
                         models = threat_data.get('affected_models', [])
                         if isinstance(models, list):
                             for m in models: st.markdown(f"- {m}")
                         else:
                             st.write(str(models))
                             
                         st.markdown("#### Modality")
                         st.write(str(threat_data.get('modality', 'N/A')))

                    with d_tab3: # Raw Data Tab
                         st.json(threat_data)

        else:
            st.info("No threats to display.")

    # --- Tab 3: SOTA Tracker ---
    with tab3:
        st.header("🧠 Intelligence Briefing")
        summary = None
        if r_client:
            summary = r_client.get("curator:latest_summary")
        
        if summary:
            st.markdown(summary)
        else:
            st.caption("No briefing generated yet.")

    # --- Tab 4: Security Status ---
    with tab4:
        st.header("🔒 Security Status")
        
        # Network Isolation Check
        st.subheader("Network Isolation Verification")
        test_results_path = "/app/logs/test_results.json"
        
        col_sec1, col_sec2 = st.columns(2)
        
        with col_sec1:
            if os.path.exists(test_results_path):
                try:
                    with open(test_results_path, 'r') as f:
                        test_data = json.load(f)
                    
                    # Check summary
                    summary_test = test_data.get('summary', {})
                    passed = summary_test.get('passed', 0)
                    failed = summary_test.get('failed', 0)
                    
                    if failed == 0 and passed > 0:
                         st.success(f"✅ Secure Enclave Verified ({passed} tests passed)")
                    else:
                         st.error(f"❌ Security Verification FAILED ({failed} tests failed)")
                         
                    with st.expander("View Verification Report"):
                        st.json(test_data)
                except Exception as e:
                    st.warning(f"Could not parse test results: {e}")
            else:
                st.info("⚠️ No security verification report found. Run security tests.")
    
        with col_sec2:
             st.markdown("**Access Control Mode:** 🔐 Localhost Only")
             st.markdown("**Egress Policy:** 🛑 Deny All (except ArXiv)")

        # Forensic Logs
        st.subheader("Forensic Log Stream")
        log_path = "/app/logs/audit.jsonl"
        if os.path.exists(log_path):
            logs = []
            try:
                 with open(log_path, 'r') as f:
                     lines = f.readlines()
                     for line in lines[-50:]:
                         try:
                             logs.append(json.loads(line))
                         except: 
                             pass
                 if logs:
                     st.dataframe(pd.DataFrame(logs), use_container_width=True)
            except:
                pass

if __name__ == "__main__":
    main()

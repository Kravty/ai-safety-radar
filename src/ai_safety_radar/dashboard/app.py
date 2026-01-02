import streamlit as st
import pandas as pd
import plotly.express as px
import redis
import json
import os
import time
from datetime import datetime

# Page Config
st.set_page_config(
    page_title="AI Safety Radar | Intelligence Dashboard",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Utils
@st.cache_resource
def get_redis_client():
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    try:
        return redis.from_url(redis_url, decode_responses=True)
    except Exception as e:
        return None

def get_stream_data(client, stream_key, count=1000):
    if not client:
        return []
    try:
        # Read from stream. 
        # xrange returns list of (id, {data})
        # We assume data is JSON string in "data" field or direct dict fields
        # Based on RedisClient implementation, we wrap payload in "data" field as JSON string.
        # But wait, RedisClient.add_job does: xadd(queue_name, {"data": json.dumps(payload)})
        
        items = client.xrange(stream_key, min="-", max="+", count=count)
        parsed_items = []
        for msg_id, data in items:
            try:
                if 'data' in data:
                     payload = json.loads(data['data'])
                else:
                     payload = data # Fallback
                
                payload['stream_id'] = msg_id
                parsed_items.append(payload)
            except:
                continue
        return parsed_items
    except Exception as e:
        st.error(f"Error reading stream {stream_key}: {e}")
        return []

# Sidebar
st.sidebar.title("🛡️ AI Safety Radar")
st.sidebar.markdown("---")
refresh = st.sidebar.button("🔄 Refresh Data")

# Redis Connection
r_client = get_redis_client()
redis_status = "🟢 Connected" if r_client and r_client.ping() else "🔴 Disconnected"
st.sidebar.caption(f"Redis Status: {redis_status}")
if not r_client:
    st.warning("Redis is unreachable. Showing cached/empty data.")

# Data Fetching
analyzed_threats = get_stream_data(r_client, "papers:analyzed")
pending_papers = get_stream_data(r_client, "papers:pending")

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["📊 Overview", "🗂️ Threat Catalog", "🌍 SOTA Tracker", "🔒 Security Status"])

with tab1:
    st.header("Threat Landscape Overview")
    
    # Manual Controls
    st.subheader("🔧 Manual Controls")

    col_ctrl1, col_ctrl2 = st.columns(2)

    with col_ctrl1:
        if st.button("⚡ Trigger Processing", type="primary"):
            # Send signal to agent_core to process one batch
            if r_client:
                r_client.publish("agent:trigger", "process_batch")
                st.success("Processing triggered! Check Agent Core logs.")
            else:
                 st.error("Redis disconnected.")
        
        if st.button("⚡ Trigger Processing + Curator"):
             if r_client:
                r_client.publish("agent:trigger", "process_with_curator")
                st.success("Triggered batch processing with Curator synthesis!")
             else:
                st.error("Redis disconnected.")

    with col_ctrl2:
        if st.button("🔄 Reset Consumer Group"):
            # Reset stuck consumer group
            if r_client:
                try:
                    r_client.xgroup_destroy("papers:pending", "agent_group")
                    r_client.xgroup_create("papers:pending", "agent_group", id="0", mkstream=True)
                    st.success("Consumer group reset!")
                except Exception as e:
                    st.error(f"Error resetting group: {e}")
            else:
                 st.error("Redis disconnected.")
                 
    st.markdown("---")

    # KPIs
    st.header("Threat Landscape Overview")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Threats Detected", len(analyzed_threats))
    col2.metric("Pending Ingestion", len(pending_papers))
    
    # Calculate High Severity Count
    high_severity_count = sum(1 for t in analyzed_threats if t.get('severity') in ['High', 'Critical'])
    col3.metric("Critical/High Risk", high_severity_count)
    
    # Charts
    if analyzed_threats:
        df = pd.DataFrame(analyzed_threats)
        
        # Severity Dist
        st.markdown("### Severity Distribution")
        fig_sev = px.pie(df, names='severity', title='Threat Severity Breakdown', hole=0.4, 
                         color='severity',
                         color_discrete_map={'Critical': 'red', 'High': 'orange', 'Medium': 'yellow', 'Low': 'green'})
        st.plotly_chart(fig_sev, use_container_width=True)
        
        # Metrics over time (Simulated if no timestamp, otherwise use published_date)
        if 'published_date' in df.columns:
            st.markdown("### Threat Activity Timeline")
            df['published_date'] = pd.to_datetime(df['published_date'])
            counts_by_date = df.groupby(df['published_date'].dt.date).size().reset_index(name='count')
            fig_time = px.bar(counts_by_date, x='published_date', y='count', title='Threats by Date')
            st.plotly_chart(fig_time, use_container_width=True)
    else:
        st.info("No threat data available yet.")

with tab2:
    st.header("Threat Catalog")
    if analyzed_threats:
        df_catalog = pd.DataFrame(analyzed_threats)
        
        # Filtering
        cols_to_show = ['title', 'severity', 'affected_models', 'published_date', 'abstract']
        # Handle missing cols
        for c in cols_to_show:
            if c not in df_catalog.columns:
                df_catalog[c] = "N/A"
                
        severity_filter = st.multiselect("Filter by Severity", options=df_catalog['severity'].unique(), default=df_catalog['severity'].unique())
        
        filtered_df = df_catalog[df_catalog['severity'].isin(severity_filter)]
        
        st.dataframe(filtered_df[cols_to_show], use_container_width=True)
        
        # Detail view
        st.markdown("### Threat Details")
        selected_threat = st.selectbox("Select Threat to Inspect", options=filtered_df['title'])
        if selected_threat:
            threat_data = filtered_df[filtered_df['title'] == selected_threat].iloc[0]
            st.json(threat_data.to_dict())
            
    else:
        st.write("Catalog is empty.")

with tab3:
    st.header("SOTA Tracker")
    st.markdown("summary of the current threat landscape curated by the **CuratorAgent**.")
    
    if r_client:
        curator_summary = r_client.get("curator:latest_summary")
        if curator_summary:
            st.markdown(curator_summary)
        else:
            st.info("No Curator summary available yet. Run the pipeline to generate one.")
            
            # Placeholder for demo if empty
            st.markdown("""
            > **Simulated Update**: 
            > *Recent analysis indicates a rise in prompt injection attacks targeting multimodal vision models.*
            """)
    else:
         st.error("Cannot fetch SOTA summary: Redis disconnected.")

with tab4:
    st.header("Security & System Status")
    
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
                summary = test_data.get('summary', {})
                passed = summary.get('passed', 0)
                failed = summary.get('failed', 0)
                
                if failed == 0 and passed > 0:
                     st.success(f"✅ Secure Enclave Verified ({passed} tests passed)")
                else:
                     st.error(f"❌ Security Verification FAILED ({failed} tests failed)")
                     
                with st.expander("View Verification Report"):
                    st.json(test_data)
            except Exception as e:
                st.warning(f"Could not parse test results: {e}")
        else:
            st.warning("⚠️ No security verification report found. Run `test_security.sh`.")

    with col_sec2:
        st.subheader("Queue Health")
        st.metric("Redis: Papers Pending", len(pending_papers))
        st.metric("Redis: Papers Analyzed", len(analyzed_threats))

    # Forensic Logs
    st.subheader("Forensic Log Stream (Last 50 Events)")
    log_path = "/app/logs/audit.jsonl"
    if os.path.exists(log_path):
        logs = []
        try:
             # Read last N lines efficiently? 
             # For now just read all and take last 50
             with open(log_path, 'r') as f:
                 lines = f.readlines()
                 for line in lines[-50:]:
                     try:
                         logs.append(json.loads(line))
                     except: 
                         pass
             
             # Show as table
             if logs:
                 df_logs = pd.DataFrame(logs)
                 # Reorder cols
                 if 'timestamp' in df_logs.columns:
                      cols = ['timestamp', 'service_name', 'event_type', 'severity', 'input_hash']
                      existing_cols = [c for c in cols if c in df_logs.columns]
                      st.dataframe(df_logs[existing_cols + [c for c in df_logs.columns if c not in existing_cols]], use_container_width=True)
             else:
                 st.info("Log file empty.")
                 
        except Exception as e:
            st.error(f"Error reading logs: {e}")
    else:
        st.info(f"No forensic logs found at {log_path}")


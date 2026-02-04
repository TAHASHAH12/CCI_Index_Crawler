import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import json
import time
from urllib.parse import quote

# Page configuration
st.set_page_config(
    page_title="Common Crawl URL Query Tool",
    page_icon="🌐",
    layout="wide"
)

# Title and description
st.title("🌐 Common Crawl Index Query Tool")
st.markdown("""
Query the Common Crawl CDX Server API to find archived snapshots of URLs.
Uses the official CDX Server API for fast and reliable queries.
""")

# Initialize session state
if 'results' not in st.session_state:
    st.session_state.results = []
if 'query_run' not in st.session_state:
    st.session_state.query_run = False

# Common Crawl CDX Server list
CDX_SERVERS = {
    "CC-MAIN-2026-04 (Jan 2026 - Latest)": "https://index.commoncrawl.org/CC-MAIN-2026-04-index",
    "CC-MAIN-2025-43 (Oct 2025)": "https://index.commoncrawl.org/CC-MAIN-2025-43-index",
    "CC-MAIN-2025-38 (Sep 2025)": "https://index.commoncrawl.org/CC-MAIN-2025-38-index",
    "CC-MAIN-2025-33 (Aug 2025)": "https://index.commoncrawl.org/CC-MAIN-2025-33-index",
    "CC-MAIN-2025-30 (Jul 2025)": "https://index.commoncrawl.org/CC-MAIN-2025-30-index",
    "CC-MAIN-2025-26 (Jun 2025)": "https://index.commoncrawl.org/CC-MAIN-2025-26-index",
    "CC-MAIN-2025-21 (May 2025)": "https://index.commoncrawl.org/CC-MAIN-2025-21-index",
    "CC-MAIN-2025-18 (Apr 2025)": "https://index.commoncrawl.org/CC-MAIN-2025-18-index",
    "CC-MAIN-2025-13 (Mar 2025)": "https://index.commoncrawl.org/CC-MAIN-2025-13-index",
    "CC-MAIN-2025-08 (Feb 2025)": "https://index.commoncrawl.org/CC-MAIN-2025-08-index",
    "CC-MAIN-2025-05 (Jan 2025)": "https://index.commoncrawl.org/CC-MAIN-2025-05-index",
    "CC-MAIN-2024-51 (Dec 2024)": "https://index.commoncrawl.org/CC-MAIN-2024-51-index",
    "CC-MAIN-2024-46 (Nov 2024)": "https://index.commoncrawl.org/CC-MAIN-2024-46-index",
    "CC-MAIN-2024-42 (Oct 2024)": "https://index.commoncrawl.org/CC-MAIN-2024-42-index",
    "CC-MAIN-2024-38 (Sep 2024)": "https://index.commoncrawl.org/CC-MAIN-2024-38-index",
    "CC-MAIN-2024-33 (Aug 2024)": "https://index.commoncrawl.org/CC-MAIN-2024-33-index",
    "CC-MAIN-2024-30 (Jul 2024)": "https://index.commoncrawl.org/CC-MAIN-2024-30-index",
    "CC-MAIN-2024-26 (Jun 2024)": "https://index.commoncrawl.org/CC-MAIN-2024-26-index",
    "CC-MAIN-2024-22 (May 2024)": "https://index.commoncrawl.org/CC-MAIN-2024-22-index",
    "CC-MAIN-2024-18 (Apr 2024)": "https://index.commoncrawl.org/CC-MAIN-2024-18-index",
}

# Sidebar for configuration
st.sidebar.header("⚙️ Query Settings")

# CDX Server selection
selected_server = st.sidebar.selectbox(
    "Select Common Crawl Index",
    options=list(CDX_SERVERS.keys()),
    index=0,
    help="Choose which Common Crawl monthly index to query"
)

cdx_server = CDX_SERVERS[selected_server]

# Option for custom CDX server
use_custom = st.sidebar.checkbox("Use custom CDX server", value=False)
if use_custom:
    cdx_server = st.sidebar.text_input(
        "Custom CDX Server URL",
        value="https://index.commoncrawl.org/CC-MAIN-2026-04-index",
        help="Enter any CDX-compatible server URL"
    )

# Match type
match_type = st.sidebar.selectbox(
    "Match Type",
    ["exact", "prefix", "host", "domain"],
    index=0,
    help="exact: exact URL | prefix: URL prefix | host: hostname | domain: domain + subdomains"
)

# Result limit per URL
limit = st.sidebar.number_input(
    "Results per URL",
    min_value=1,
    max_value=1000,
    value=10,
    help="Maximum number of results to return per URL"
)

# Timeout settings
timeout_seconds = st.sidebar.number_input(
    "Request Timeout (seconds)",
    min_value=5,
    max_value=60,
    value=10,
    help="HTTP request timeout"
)

# Advanced settings
with st.sidebar.expander("🔧 Advanced Settings"):
    # Date range
    use_date_range = st.checkbox("Use date range filter", value=False)
    
    if use_date_range:
        col1, col2 = st.columns(2)
        with col1:
            from_date = st.date_input("From date", value=datetime.now() - timedelta(days=365))
        with col2:
            to_date = st.date_input("To date", value=datetime.now())
    
    # Status filter
    filter_status = st.text_input(
        "Status filter (optional)",
        placeholder="e.g., 200",
        help="Filter by HTTP status code (e.g., 200, 404)"
    )
    
    # MIME type filter
    filter_mime = st.text_input(
        "MIME type filter (optional)",
        placeholder="e.g., text/html",
        help="Filter by MIME type (e.g., text/html, image/jpeg)"
    )
    
    # Output format
    output_format = st.selectbox("Output format", ["json", "text"], index=0)
    
    # Fields to return
    fl_fields = st.text_input(
        "Fields to return (fl parameter)",
        value="urlkey,timestamp,url,mime,status,digest,length",
        help="Comma-separated list of fields"
    )

# Main interface
st.header("📝 Enter URLs")

# Text area for multiple URLs
url_input = st.text_area(
    "Enter URLs (one per line)",
    height=150,
    placeholder="https://example.com\nhttps://stake.com\nhttps://commoncrawl.org",
    help="Enter one URL per line"
)

# File upload option
st.markdown("**Or upload a text file with URLs:**")
uploaded_file = st.file_uploader(
    "Choose a .txt file",
    type=['txt'],
    help="Upload a text file with one URL per line"
)

# Process uploaded file
if uploaded_file is not None:
    try:
        file_content = uploaded_file.read().decode('utf-8')
        url_input = file_content
    except Exception as e:
        st.error(f"Error reading file: {str(e)}")

# Query button
col1, col2, col3 = st.columns([1, 1, 4])
with col1:
    query_button = st.button("🔍 Query CDX Server", type="primary")
with col2:
    clear_button = st.button("🗑️ Clear Results")

if clear_button:
    st.session_state.results = []
    st.session_state.query_run = False
    st.rerun()

# Function to query CDX Server API
def query_cdx_api(cdx_server, url, match_type, limit, timeout, filter_status=None, filter_mime=None, from_ts=None, to_ts=None, output='json', fl=None):
    """Query CDX Server API directly using requests"""
    try:
        # Build query parameters
        params = {
            'url': url,
            'matchType': match_type,
            'limit': limit,
            'output': output
        }
        
        # Add optional parameters
        if from_ts:
            params['from'] = from_ts
        if to_ts:
            params['to'] = to_ts
        if fl:
            params['fl'] = fl
        
        # Add filters
        if filter_status:
            params['filter'] = f'=status:{filter_status}'
        if filter_mime:
            if 'filter' in params:
                params['filter'] += f',=mime:{filter_mime}'
            else:
                params['filter'] = f'=mime:{filter_mime}'
        
        # Make request
        response = requests.get(
            cdx_server,
            params=params,
            timeout=timeout,
            headers={'User-Agent': 'Streamlit-CDX-Query-Tool/1.0'}
        )
        
        # Check response
        if response.status_code == 200:
            results = []
            
            if output == 'json':
                # Parse JSON lines
                for line in response.text.strip().split('\n'):
                    if line:
                        try:
                            results.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
            else:
                # Parse text format
                for line in response.text.strip().split('\n'):
                    if line:
                        results.append({'raw': line})
            
            return results, None
        else:
            return [], f"HTTP {response.status_code}: {response.text[:100]}"
            
    except requests.exceptions.Timeout:
        return [], f"Timeout: Request exceeded {timeout} seconds"
    except requests.exceptions.ConnectionError:
        return [], "Connection error: Could not connect to CDX server"
    except Exception as e:
        return [], f"Error: {str(e)[:100]}"

# Process queries
if query_button and url_input:
    # Parse URLs
    urls = [url.strip() for url in url_input.split('\n') if url.strip()]
    
    if not urls:
        st.error("Please enter at least one URL.")
    else:
        st.session_state.results = []
        st.session_state.query_run = True
        
        # Prepare date range if specified
        from_ts = None
        to_ts = None
        if use_date_range:
            from_ts = from_date.strftime('%Y%m%d%H%M%S')
            to_ts = to_date.strftime('%Y%m%d%H%M%S')
        
        # Display query info
        st.info(f"🔍 Querying **{selected_server}** with match type: **{match_type}**")
        
        # Progress tracking
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Query each URL
        for idx, url in enumerate(urls):
            status_text.text(f"⏳ Querying {idx + 1}/{len(urls)}: {url}")
            
            start_time = time.time()
            
            # Query CDX API
            results, error = query_cdx_api(
                cdx_server,
                url,
                match_type,
                limit,
                timeout_seconds,
                filter_status,
                filter_mime,
                from_ts,
                to_ts,
                output_format,
                fl_fields
            )
            
            elapsed = time.time() - start_time
            
            if error:
                st.session_state.results.append({
                    'query_url': url,
                    'error': error,
                    'urlkey': '-',
                    'timestamp': '-',
                    'url': '-',
                    'mime': '-',
                    'status': '-',
                    'digest': '-',
                    'length': '-'
                })
                st.warning(f"⚠️ {url}: {error} (took {elapsed:.1f}s)")
            else:
                if results:
                    for result in results:
                        result['query_url'] = url
                        # Handle both JSON and text format
                        if 'raw' in result:
                            # Parse text format (space-separated)
                            parts = result['raw'].split()
                            if len(parts) >= 7:
                                result.update({
                                    'urlkey': parts[0],
                                    'timestamp': parts[1],
                                    'url': parts[2],
                                    'mime': parts[3],
                                    'status': parts[4],
                                    'digest': parts[5],
                                    'length': parts[6]
                                })
                    
                    st.session_state.results.extend(results)
                    st.success(f"✅ {url}: Found {len(results)} results (took {elapsed:.1f}s)")
                else:
                    st.session_state.results.append({
                        'query_url': url,
                        'urlkey': '-',
                        'timestamp': '-',
                        'url': 'No results found',
                        'mime': '-',
                        'status': '-',
                        'digest': '-',
                        'length': '-'
                    })
                    st.info(f"ℹ️ {url}: No results found (took {elapsed:.1f}s)")
            
            # Update progress
            progress_bar.progress((idx + 1) / len(urls))
            
            # Small delay between requests
            time.sleep(0.3)
        
        status_text.text("✅ Query complete!")
        time.sleep(1)
        progress_bar.empty()
        status_text.empty()

# Display results
if st.session_state.query_run and st.session_state.results:
    st.header("📊 Results")
    
    # Convert to DataFrame
    df = pd.DataFrame(st.session_state.results)
    
    # Display statistics - FIXED
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Results", len(df))
    with col2:
        unique_urls = df['query_url'].nunique() if 'query_url' in df.columns else 0
        st.metric("URLs Queried", unique_urls)
    with col3:
        successful = 0
        if 'url' in df.columns:
            successful = len(df[df['url'] != 'No results found'])
            if 'error' in df.columns:
                successful -= len(df[df['error'].notna()])
        st.metric("Successful Captures", successful)
    with col4:
        errors = 0
        if 'error' in df.columns:
            errors = len(df[df['error'].notna()])
        st.metric("Errors/Timeouts", errors)
    
    # Filter controls
    col1, col2 = st.columns(2)
    with col1:
        show_errors = st.checkbox("Show errors/timeouts", value=True)
    with col2:
        show_no_results = st.checkbox("Show 'no results' entries", value=False)
    
    # Filter dataframe - FIXED
    display_df = df.copy()
    
    if not show_errors and 'error' in display_df.columns:
        display_df = display_df[display_df['error'].isna()]
    
    if not show_no_results and 'url' in display_df.columns:
        display_df = display_df[display_df['url'] != 'No results found']
    
    # Display table
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True
    )
    
    # Download options
    st.subheader("💾 Export Results")
    
    col1, col2 = st.columns(2)
    
    with col1:
        csv = df.to_csv(index=False)
        st.download_button(
            label="📥 Download as CSV",
            data=csv,
            file_name=f"cdx_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    
    with col2:
        json_data = df.to_json(orient='records', indent=2)
        st.download_button(
            label="📥 Download as JSON",
            data=json_data,
            file_name=f"cdx_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )

# Footer with information
st.markdown("---")
st.markdown("""
### ℹ️ CDX Server API Documentation

This tool uses the **CDX Server API** directly for fast, reliable queries.

**Match Types:**
- **exact**: Matches the URL exactly
- **prefix**: Matches URLs starting with the given prefix (e.g., `example.com/*`)
- **host**: Matches all URLs from the given host
- **domain**: Matches the domain and all subdomains (e.g., `*.example.com`)

**Filter Syntax:**
- `=status:200` - Exact match for HTTP 200
- `!=status:404` - Not equal to 404
- `~mime:text/.*` - Regex match for MIME type

**Example Queries:**
URL: example.com
Match Type: domain
Status Filter: 200
MIME Filter: text/html
            

**API Reference:** https://github.com/webrecorder/pywb/wiki/CDX-Server-API

**Note:** Each CDX index represents one month of Common Crawl data. Query the latest index for recent captures.
""")

import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import json
import time
from urllib.parse import urlparse, urlunparse

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

# Match type - DEFAULT TO DOMAIN (smart choice)
match_type = st.sidebar.selectbox(
    "Match Type",
    ["domain", "prefix", "host", "exact"],
    index=0,
    help="domain: domain + subdomains (RECOMMENDED) | prefix: URL prefix | host: hostname only | exact: exact URL"
)

# URL variant retry
auto_retry_variants = st.sidebar.checkbox(
    "Auto-retry URL variants",
    value=True,
    help="Automatically try http/https, www/non-www variants if no results found"
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
    placeholder="example.com\nstake.com\nhttps://commoncrawl.org",
    help="Enter one URL per line (protocol optional for domain/prefix match)"
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

# Function to generate URL variants
def generate_url_variants(url):
    """Generate common URL variants (http/https, www/non-www)"""
    variants = [url]
    
    # Parse URL
    if not url.startswith(('http://', 'https://')):
        variants.append(f'http://{url}')
        variants.append(f'https://{url}')
        url = f'http://{url}'  # Use for parsing
    
    try:
        parsed = urlparse(url)
        domain = parsed.netloc
        
        # www variant
        if domain.startswith('www.'):
            non_www = domain[4:]
            variants.append(urlunparse(parsed._replace(netloc=non_www)))
        else:
            www_version = f'www.{domain}'
            variants.append(urlunparse(parsed._replace(netloc=www_version)))
        
        # Protocol variant
        if parsed.scheme == 'http':
            variants.append(url.replace('http://', 'https://'))
        else:
            variants.append(url.replace('https://', 'http://'))
        
        # Trailing slash variants
        path = parsed.path
        if path.endswith('/'):
            variants.append(urlunparse(parsed._replace(path=path.rstrip('/'))))
        else:
            variants.append(urlunparse(parsed._replace(path=path + '/')))
    
    except:
        pass
    
    # Remove duplicates while preserving order
    seen = set()
    unique_variants = []
    for v in variants:
        if v not in seen:
            seen.add(v)
            unique_variants.append(v)
    
    return unique_variants

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
            
            return results, None, 'success'
        
        elif response.status_code == 404:
            # 404 means no captures found, not an error
            return [], None, 'no_captures'
        else:
            return [], f"HTTP {response.status_code}: {response.text[:100]}", 'error'
            
    except requests.exceptions.Timeout:
        return [], f"Timeout: Request exceeded {timeout} seconds", 'timeout'
    except requests.exceptions.ConnectionError:
        return [], "Connection error: Could not connect to CDX server", 'error'
    except Exception as e:
        return [], f"Error: {str(e)[:100]}", 'error'

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
        st.info(f"🔍 Querying **{selected_server}** with match type: **{match_type}** | Auto-retry: **{auto_retry_variants}**")
        
        # Progress tracking
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Query each URL
        for idx, url in enumerate(urls):
            status_text.text(f"⏳ Querying {idx + 1}/{len(urls)}: {url}")
            
            start_time = time.time()
            
            # Query CDX API
            results, error, status = query_cdx_api(
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
            
            # Try variants if no results and auto-retry is enabled
            tried_variants = [url]
            if status == 'no_captures' and auto_retry_variants and match_type == 'exact':
                variants = generate_url_variants(url)
                for variant in variants:
                    if variant not in tried_variants:
                        tried_variants.append(variant)
                        results, error, status = query_cdx_api(
                            cdx_server,
                            variant,
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
                        if status == 'success':
                            st.info(f"🔄 Found results using variant: {variant}")
                            break
            
            elapsed = time.time() - start_time
            
            # Handle results based on status
            if status == 'error' or status == 'timeout':
                # Real error - add to error tracking
                st.session_state.results.append({
                    'query_url': url,
                    'result_type': 'error',
                    'error_message': error,
                    'captures_found': 0,
                    'urlkey': None,
                    'timestamp': None,
                    'url': None,
                    'mime': None,
                    'status': None,
                    'digest': None,
                    'length': None
                })
                st.warning(f"⚠️ {url}: {error} (took {elapsed:.1f}s)")
            
            elif status == 'no_captures':
                # No captures found - this is normal, not an error
                st.session_state.results.append({
                    'query_url': url,
                    'result_type': 'no_captures',
                    'error_message': None,
                    'captures_found': 0,
                    'urlkey': None,
                    'timestamp': None,
                    'url': None,
                    'mime': None,
                    'status': None,
                    'digest': None,
                    'length': None
                })
                st.info(f"ℹ️ {url}: No captures found in this index (took {elapsed:.1f}s)")
            
            else:
                # Success - found captures
                if results:
                    for result in results:
                        result['query_url'] = url
                        result['result_type'] = 'capture'
                        result['error_message'] = None
                        result['captures_found'] = len(results)
                        
                        # Handle both JSON and text format
                        if 'raw' in result:
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
                    st.success(f"✅ {url}: Found {len(results)} capture(s) (took {elapsed:.1f}s)")
            
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
    
    # Calculate statistics properly
    total_queries = df['query_url'].nunique() if 'query_url' in df.columns else 0
    total_captures = len(df[df['result_type'] == 'capture']) if 'result_type' in df.columns else 0
    no_captures = len(df[df['result_type'] == 'no_captures']) if 'result_type' in df.columns else 0
    errors = len(df[df['result_type'] == 'error']) if 'result_type' in df.columns else 0
    
    # Display statistics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("URLs Queried", total_queries)
    with col2:
        st.metric("Captures Found", total_captures, help="Total capture records returned")
    with col3:
        st.metric("No Captures", no_captures, help="URLs with 0 captures (normal, not an error)")
    with col4:
        st.metric("Real Errors", errors, help="Timeouts, connection errors, server errors")
    
    # Filter controls
    col1, col2, col3 = st.columns(3)
    with col1:
        show_captures = st.checkbox("Show captures", value=True)
    with col2:
        show_no_captures = st.checkbox("Show 'no captures' entries", value=False)
    with col3:
        show_errors = st.checkbox("Show errors", value=True)
    
    # Filter dataframe
    display_df = df.copy()
    
    if 'result_type' in display_df.columns:
        mask = []
        if show_captures:
            mask.append(display_df['result_type'] == 'capture')
        if show_no_captures:
            mask.append(display_df['result_type'] == 'no_captures')
        if show_errors:
            mask.append(display_df['result_type'] == 'error')
        
        if mask:
            combined_mask = mask[0]
            for m in mask[1:]:
                combined_mask = combined_mask | m
            display_df = display_df[combined_mask]
    
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
### ℹ️ Understanding Results

**Result Types:**
- **Captures Found**: Actual archived snapshots from Common Crawl
- **No Captures**: URL not found in this index (normal, not an error)
- **Real Errors**: Connection timeouts, server errors, rate limits

**Match Types (defaults to "domain" - recommended):**
- **domain** ⭐: Matches domain + all subdomains (e.g., `*.example.com`) - BEST for existence checking
- **prefix**: Matches URLs starting with the given prefix (e.g., `example.com/*`)
- **host**: Matches only the specific hostname
- **exact**: Exact URL match only - use only for specific URL queries

**Auto-retry URL variants:**
When enabled, automatically tries http/https and www/non-www variants if the exact URL returns no results.

**Why "no captures found" is normal:**
Common Crawl doesn't archive every URL on the internet. Missing from one monthly index doesn't mean the site is broken - it just means it wasn't captured during that crawl period.

**API Reference:** https://github.com/webrecorder/pywb/wiki/CDX-Server-API
""")

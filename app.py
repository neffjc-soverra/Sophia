import streamlit as st
import pandas as pd
from io import BytesIO
import json
import logging
from verification_helper import load_config, process_dataframe_real

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(page_title="Hospital L&D Verification", page_icon="🏥", layout="wide")

st.title("🏥 Hospital Labor & Delivery Verification Tool")
st.write("Upload an Excel file and download verified results.\n\n**Required columns:** `name`, `city`, `state`, `year`")

MAX_FILE_SIZE_MB = 10
MAX_ROWS = 500

try:
    base_cfg = load_config('hospital_verification_config.json')
    base_pos = base_cfg['search_instructions']['keywords']['maternity_positive']
    base_neg = base_cfg['search_instructions']['keywords']['maternity_negative']
except Exception as e:
    st.error(f"Failed to load configuration: {e}")
    st.stop()

with st.sidebar:
    st.header("ℹ️ Information")
    st.markdown("""
    ### How it works
    1. Upload Excel file with hospital data
    2. Configure search keywords (optional)
    3. Run verification
    4. Download results
    
    ### Limitations
    - Maximum file size: 10 MB
    - Maximum rows: 500
    - Real search is rate-limited
    
    ### Tips
    - Web search is ENABLED by default
    - Processing takes 1-2 minutes per hospital
    - Review LOW confidence results manually
    - Uncheck "Use real web search" for instant testing
    """)

st.subheader("📥 Step 1: Download Template")
template_df = pd.DataFrame({
    'name': ['Example Hospital A', 'Example Medical Center B'],
    'city': ['Seattle', 'Tacoma'],
    'state': ['WA', 'WA'],
    'year': [2024, 2024]
})
buffer = BytesIO()
template_df.to_excel(buffer, index=False, engine='openpyxl')
buffer.seek(0)
st.download_button('📄 Download Input Template', buffer.getvalue(), file_name='hospital_input_template.xlsx', help="Download this template and fill in your hospital data")

st.subheader("📤 Step 2: Upload Your File")
uploaded_file = st.file_uploader("Upload .xlsx file", type=['xlsx'], help=f"Maximum file size: {MAX_FILE_SIZE_MB} MB")

def validate_columns(df):
    required = ['name', 'city', 'state', 'year']
    missing = [c for c in required if c not in df.columns]
    return missing

def validate_file_size(uploaded_file):
    if uploaded_file is None:
        return True, 0
    file_size_mb = uploaded_file.size / (1024 * 1024)
    return file_size_mb <= MAX_FILE_SIZE_MB, file_size_mb

st.subheader("⚙️ Step 3: Configure Keywords")
st.markdown("Customize the keywords used to identify maternity services:")

col1, col2 = st.columns(2)
with col1:
    pos_text = st.text_area('Positive keywords (comma-separated)', value=', '.join(base_pos), height=120, help="Keywords that indicate presence of L&D services")
with col2:
    neg_text = st.text_area('Negative keywords (comma-separated)', value=', '.join(base_neg), height=120, help="Keywords that indicate absence of L&D services")

def parse_keywords(txt):
    if not txt or not isinstance(txt, str):
        return []
    parts = [p.strip() for p in txt.split(',')]
    return [p for p in parts if len(p) > 0]

if uploaded_file is not None:
    size_valid, file_size = validate_file_size(uploaded_file)
    if not size_valid:
        st.error(f"❌ File size ({file_size:.2f} MB) exceeds maximum ({MAX_FILE_SIZE_MB} MB)")
        st.stop()
    
    try:
        df = pd.read_excel(uploaded_file, engine='openpyxl')
        
        missing = validate_columns(df)
        if len(missing) > 0:
            st.error(f'❌ Missing required columns: {", ".join(missing)}')
            st.info("Required columns: name, city, state, year")
            st.stop()
        
        if len(df) > MAX_ROWS:
            st.error(f'❌ File contains {len(df)} rows. Maximum allowed: {MAX_ROWS}')
            st.info("Please split your file into smaller batches.")
            st.stop()
        
        if df.empty:
            st.error("❌ File is empty")
            st.stop()
        
        st.success(f'✅ Loaded {len(df)} rows successfully')
        
        st.subheader('📊 Data Preview')
        st.dataframe(df.head(10), use_container_width=True)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Rows", len(df))
        with col2:
            st.metric("Unique Cities", df['city'].nunique())
        with col3:
            st.metric("Unique States", df['state'].nunique())
        
        st.subheader("🚀 Step 4: Run Verification")
        
        col1, col2 = st.columns(2)
        with col1:
            # CHANGED: value=True enables search by default
            use_real_search = st.checkbox('Use real web search', value=True, help="Enabled by default. Uncheck for instant testing (all results will be UNKNOWN).")
        with col2:
            use_async = st.checkbox('Use concurrent processing (experimental)', value=False, help="Process multiple hospitals simultaneously. Faster but may hit rate limits.", disabled=not use_real_search)
        
        if use_real_search:
            estimated_time = len(df) * 1.5 if not use_async else len(df) * 0.5
            st.warning(f"⏱️ Estimated processing time: {estimated_time:.1f} minutes")
        else:
            st.info("ℹ️ Web search is disabled. Results will be marked UNKNOWN for instant testing.")
        
        if st.button('▶️ Run Verification', type="primary"):
            pos_keywords = parse_keywords(pos_text)
            neg_keywords = parse_keywords(neg_text)
            
            if not pos_keywords:
                st.warning("⚠️ No positive keywords provided. Using defaults.")
                pos_keywords = base_pos
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            def update_progress(current, total):
                progress = current / total
                progress_bar.progress(progress)
                status_text.text(f"Processing: {current}/{total} hospitals ({progress*100:.1f}%)")
            
            try:
                with st.spinner('Processing hospitals, please wait...'):
                    cfg = load_config('hospital_verification_config.json')
                    cfg['search_instructions']['keywords']['maternity_positive'] = pos_keywords
                    cfg['search_instructions']['keywords']['maternity_negative'] = neg_keywords
                    
                    result_df, count = process_dataframe_real(df.copy(), cfg, use_real_search=use_real_search, use_async=use_async, progress_callback=update_progress)
                    
                    progress_bar.empty()
                    status_text.empty()
                    
                    st.success(f'✅ Successfully processed {count} rows')
                    
                    st.subheader('📈 Results Summary')
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        yes_count = (result_df['verified_ld_service'] == 'YES').sum()
                        st.metric("Verified YES", yes_count)
                    with col2:
                        no_count = (result_df['verified_ld_service'] == 'NO').sum()
                        st.metric("Verified NO", no_count)
                    with col3:
                        unknown_count = (result_df['verified_ld_service'] == 'UNKNOWN').sum()
                        st.metric("Unknown", unknown_count)
                    with col4:
                        high_conf = (result_df['confidence_level'] == 'HIGH').sum()
                        st.metric("High Confidence", high_conf)
                    
                    st.subheader('📋 Results Preview (First 15 Rows)')
                    
                    def highlight_decision(val):
                        if val == 'YES':
                            return 'background-color: #90EE90'
                        elif val == 'NO':
                            return 'background-color: #FFB6C6'
                        elif val == 'UNKNOWN':
                            return 'background-color: #FFE4B5'
                        elif val == 'ERROR':
                            return 'background-color: #FF6B6B'
                        return ''
                    
                    styled_df = result_df.head(15).style.applymap(highlight_decision, subset=['verified_ld_service'])
                    st.dataframe(styled_df, use_container_width=True)
                    
                    low_conf_count = (result_df['confidence_level'] == 'LOW').sum()
                    if low_conf_count > 0:
                        st.warning(f"⚠️ {low_conf_count} results have LOW confidence. Manual review recommended.")
                    
                    st.subheader('💾 Download Results')
                    out_xlsx = BytesIO()
                    result_df.to_excel(out_xlsx, index=False, engine='openpyxl')
                    out_xlsx.seek(0)
                    
                    st.download_button('⬇️ Download Complete Results', out_xlsx.getvalue(), file_name='verification_results.xlsx', type="primary", help="Download the full results as an Excel file")
                    
                    with st.expander("📖 Understanding Your Results"):
                        st.markdown("""
                        **verified_ld_service**: YES, NO, UNKNOWN, or ERROR
                        - YES: Evidence found for L&D services
                        - NO: Evidence of no L&D services
                        - UNKNOWN: Insufficient evidence
                        - ERROR: Processing error occurred
                        
                        **confidence_level**: HIGH, MEDIUM, or LOW
                        - HIGH: Multiple strong sources
                        - MEDIUM: Single source or indirect evidence
                        - LOW: Weak or conflicting evidence
                        
                        **verification_source**: Primary source used
                        
                        **notes**: Keywords matched and additional info
                        """)
                    
            except Exception as e:
                progress_bar.empty()
                status_text.empty()
                st.error(f"❌ An error occurred during processing: {str(e)}")
                logger.exception("Processing error")
                st.info("Try again with 'Use real web search' unchecked for basic validation.")
                
    except Exception as e:
        st.error(f"❌ Failed to read file: {str(e)}")
        logger.exception("File reading error")
        st.info("Make sure your file is a valid .xlsx Excel file with the required columns.")

else:
    st.info("👆 Upload an Excel file to get started")

st.markdown("---")
st.markdown('<div style="text-align: center; color: gray; font-size: 0.9em;">Hospital L&D Verification Tool | For questions or issues, contact your administrator</div>', unsafe_allow_html=True)

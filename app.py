import streamlit as st
import pandas as pd
from io import BytesIO
import json
import logging
from verification_helper import load_config, process_dataframe_detailed

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(page_title="Hospital L&D Verification", page_icon="🏥", layout="wide")

st.title("🏥 Hospital Labor & Delivery Verification Tool")
st.write("""
Upload an Excel file with hospital data for comprehensive L&D service verification.

**Required columns:** `name`, `city`, `state`, `year`, `address`

**Optional existing columns:** `observice`, `matcare`, `mattotal` (for comparison)
""")

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
    st.header("ℹ️ Verification Process")
    st.markdown("""
    ### What This Tool Does
    1. Verifies L&D services existence
    2. Finds bed counts (if available)
    3. Identifies service changes (2023-2024)
    4. Provides source URLs
    5. Flags discrepancies with original data
    
    ### Search Priority
    1. Hospital website
    2. WA Dept of Health
    3. CMS Hospital Compare
    4. News articles (closures/mergers)
    
    ### Confidence Levels
    - **HIGH**: Official hospital/state source
    - **MEDIUM**: Secondary reliable source
    - **LOW**: Unclear or conflicting info
    
    ### Processing Time
    - ~1-2 minutes per hospital
    - Separate searches for 2023 & 2024
    """)

st.subheader("📥 Step 1: Download Template")
template_df = pd.DataFrame({
    'name': ['Example Hospital', 'Example Medical Center'],
    'address': ['123 Main St', '456 Oak Ave'],
    'city': ['Seattle', 'Tacoma'],
    'state': ['WA', 'WA'],
    'zip': ['98101', '98402'],
    'year': [2023, 2024],
    'observice': ['1.by staff', '0.none'],
    'mattotal': [5, 0]
})
buffer = BytesIO()
template_df.to_excel(buffer, index=False, engine='openpyxl')
buffer.seek(0)
st.download_button(
    '📄 Download Template', 
    buffer.getvalue(), 
    file_name='hospital_verification_template.xlsx',
    help="Template with required columns"
)

st.subheader("📤 Step 2: Upload Your File")
uploaded_file = st.file_uploader(
    "Upload .xlsx file", 
    type=['xlsx'], 
    help=f"Maximum file size: {MAX_FILE_SIZE_MB} MB, Maximum rows: {MAX_ROWS}"
)

def validate_columns(df):
    required = ['name', 'city', 'state', 'year', 'address']
    missing = [c for c in required if c not in df.columns]
    return missing

def validate_file_size(uploaded_file):
    if uploaded_file is None:
        return True, 0
    file_size_mb = uploaded_file.size / (1024 * 1024)
    return file_size_mb <= MAX_FILE_SIZE_MB, file_size_mb

st.subheader("⚙️ Step 3: Verification Options")

col1, col2 = st.columns(2)
with col1:
    verify_mode = st.radio(
        "Verification Mode",
        ["Re-verify all hospitals", "Only verify if missing/empty", "Only verify discrepancies"],
        help="Choose what to verify"
    )
with col2:
    use_real_search = st.checkbox(
        'Use real web search', 
        value=True, 
        help="Enabled by default. Uncheck for testing (will use existing data if available)"
    )
    
    include_bed_count = st.checkbox(
        'Search for bed counts',
        value=True,
        help="Attempt to find L&D bed numbers (may be difficult to find)"
    )

st.subheader("🔍 Step 4: Customize Keywords (Optional)")
with st.expander("Advanced: Edit Search Keywords"):
    col1, col2 = st.columns(2)
    with col1:
        pos_text = st.text_area(
            'Positive keywords (comma-separated)', 
            value=', '.join(base_pos), 
            height=120,
            help="Keywords that indicate presence of L&D services"
        )
    with col2:
        neg_text = st.text_area(
            'Negative keywords (comma-separated)', 
            value=', '.join(base_neg), 
            height=120,
            help="Keywords that indicate absence of L&D services"
        )

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
            st.info("Required columns: name, city, state, year, address")
            st.stop()
        
        if len(df) > MAX_ROWS:
            st.error(f'❌ File contains {len(df)} rows. Maximum allowed: {MAX_ROWS}')
            st.info("Please split your file into smaller batches.")
            st.stop()
        
        if df.empty:
            st.error("❌ File is empty")
            st.stop()
        
        st.success(f'✅ Loaded {len(df)} rows successfully')
        
        # Show data overview
        st.subheader('📊 Data Overview')
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Rows", len(df))
        with col2:
            st.metric("Unique Hospitals", df['name'].nunique())
        with col3:
            years = df['year'].unique()
            st.metric("Years", f"{min(years)}-{max(years)}")
        with col4:
            st.metric("Counties", df['county_name'].nunique() if 'county_name' in df.columns else 'N/A')
        
        # Show preview
        st.subheader('🔍 Data Preview')
        preview_cols = ['year', 'name', 'city', 'address', 'observice', 'verified_ld_service']
        available_preview_cols = [col for col in preview_cols if col in df.columns]
        st.dataframe(df[available_preview_cols].head(10), use_container_width=True)
        
        st.subheader("🚀 Step 5: Run Verification")
        
        # Determine what needs verification based on mode
        if 'verified_ld_service' in df.columns:
            empty_count = df['verified_ld_service'].isna().sum()
            verified_count = df['verified_ld_service'].notna().sum()
            st.info(f"📋 Current status: {verified_count} already verified, {empty_count} need verification")
        
        if use_real_search:
            estimated_time = len(df) * 1.5
            st.warning(f"⏱️ Estimated processing time: {estimated_time:.1f} minutes ({len(df)} hospitals × ~1.5 min each)")
        else:
            st.info("ℹ️ Web search disabled. Will preserve existing verification data or mark as UNKNOWN.")
        
        if st.button('▶️ Run Verification', type="primary", use_container_width=True):
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
                with st.spinner('Verifying hospitals, please wait...'):
                    cfg = load_config('hospital_verification_config.json')
                    cfg['search_instructions']['keywords']['maternity_positive'] = pos_keywords
                    cfg['search_instructions']['keywords']['maternity_negative'] = neg_keywords
                    
                    result_df, count = process_dataframe_detailed(
                        df.copy(), 
                        cfg, 
                        use_real_search=use_real_search,
                        verify_mode=verify_mode,
                        include_bed_count=include_bed_count,
                        progress_callback=update_progress
                    )
                    
                    progress_bar.empty()
                    status_text.empty()
                    
                    st.success(f'✅ Successfully processed {count} hospitals')
                    
                    st.subheader('📈 Verification Results Summary')
                    
                    col1, col2, col3, col4, col5 = st.columns(5)
                    with col1:
                        yes_count = (result_df['verified_ld_service'] == 'YES').sum()
                        st.metric("Has L&D", yes_count, delta=None)
                    with col2:
                        no_count = (result_df['verified_ld_service'] == 'NO').sum()
                        st.metric("No L&D", no_count)
                    with col3:
                        unknown_count = (result_df['verified_ld_service'] == 'UNKNOWN').sum()
                        st.metric("Unknown", unknown_count)
                    with col4:
                        high_conf = (result_df['confidence_level'] == 'HIGH').sum()
                        st.metric("High Confidence", high_conf)
                    with col5:
                        discrepancies = (result_df['discrepancy_flag'] == 'YES').sum()
                        st.metric("Discrepancies", discrepancies, delta=None, delta_color="off")
                    
                    # Show discrepancies if any
                    if discrepancies > 0:
                        st.warning(f"⚠️ Found {discrepancies} discrepancies between original data and verification")
                        with st.expander("View Discrepancies"):
                            disc_cols = ['year', 'name', 'city', 'observice', 'verified_ld_service', 'notes']
                            disc_data = result_df[result_df['discrepancy_flag'] == 'YES'][disc_cols]
                            st.dataframe(disc_data, use_container_width=True)
                    
                    # Results preview
                    st.subheader('📋 Results Preview (First 20 Rows)')
                    
                    def highlight_decision(val):
                        if val == 'YES':
                            return 'background-color: #90EE90'
                        elif val == 'NO':
                            return 'background-color: #FFB6C6'
                        elif val == 'UNKNOWN':
                            return 'background-color: #FFE4B5'
                        return ''
                    
                    def highlight_discrepancy(val):
                        if val == 'YES':
                            return 'background-color: #FFD700'
                        return ''
                    
                    display_cols = ['year', 'name', 'city', 'verified_ld_service', 'ld_bed_count', 
                                   'confidence_level', 'discrepancy_flag']
                    available_cols = [col for col in display_cols if col in result_df.columns]
                    
                    styled_df = result_df[available_cols].head(20).style\
                        .applymap(highlight_decision, subset=['verified_ld_service'])\
                        .applymap(highlight_discrepancy, subset=['discrepancy_flag'])
                    
                    st.dataframe(styled_df, use_container_width=True)
                    
                    # Download results
                    st.subheader('💾 Download Results')
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        # Full results
                        out_xlsx = BytesIO()
                        result_df.to_excel(out_xlsx, index=False, engine='openpyxl')
                        out_xlsx.seek(0)
                        
                        st.download_button(
                            '⬇️ Download Complete Results', 
                            out_xlsx.getvalue(), 
                            file_name=f'verification_results_{pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")}.xlsx',
                            type="primary",
                            help="Download all columns with verification data"
                        )
                    
                    with col2:
                        # Discrepancies only
                        if discrepancies > 0:
                            disc_xlsx = BytesIO()
                            disc_df = result_df[result_df['discrepancy_flag'] == 'YES']
                            disc_df.to_excel(disc_xlsx, index=False, engine='openpyxl')
                            disc_xlsx.seek(0)
                            
                            st.download_button(
                                '⚠️ Download Discrepancies Only',
                                disc_xlsx.getvalue(),
                                file_name=f'discrepancies_{pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")}.xlsx',
                                help="Download only hospitals with discrepancies"
                            )
                    
                    # Summary statistics
                    with st.expander("📊 Detailed Statistics"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write("**Bed Count Analysis:**")
                            bed_found = result_df[result_df['ld_bed_count'] != 'Not Found']['ld_bed_count'].count()
                            st.write(f"- Bed counts found: {bed_found}")
                            st.write(f"- Bed counts not found: {len(result_df) - bed_found}")
                            
                            if bed_found > 0:
                                numeric_beds = pd.to_numeric(result_df['ld_bed_count'], errors='coerce')
                                avg_beds = numeric_beds.mean()
                                st.write(f"- Average beds (when found): {avg_beds:.1f}")
                        
                        with col2:
                            st.write("**Confidence Distribution:**")
                            conf_dist = result_df['confidence_level'].value_counts()
                            for conf, count in conf_dist.items():
                                st.write(f"- {conf}: {count}")
                    
                    with st.expander("📖 Understanding Your Results"):
                        st.markdown("""
                        **verified_ld_service**
                        - YES: Evidence found for L&D services
                        - NO: Clear evidence of NO L&D services
                        - UNKNOWN: Insufficient or unclear evidence
                        
                        **ld_bed_count**
                        - Number: Specific bed count found
                        - "Not Found": No bed count information available
                        
                        **confidence_level**
                        - HIGH: Official hospital website or state licensing data
                        - MEDIUM: Secondary reliable source (news, directory)
                        - LOW: Unclear, conflicting, or indirect evidence
                        
                        **discrepancy_flag**
                        - YES: Verified data differs from original classification
                        - NO: Verified data matches original classification
                        
                        **verification_source**
                        - URL(s) where information was found
                        
                        **notes**
                        - Additional context, keywords matched, service changes, closures, etc.
                        """)
                    
            except Exception as e:
                progress_bar.empty()
                status_text.empty()
                st.error(f"❌ An error occurred during processing: {str(e)}")
                logger.exception("Processing error")
                st.info("Try reducing the number of hospitals or disabling web search for testing.")
                
    except Exception as e:
        st.error(f"❌ Failed to read file: {str(e)}")
        logger.exception("File reading error")
        st.info("Make sure your file is a valid .xlsx Excel file with the required columns.")

else:
    st.info("👆 Upload an Excel file to get started")

st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray; font-size: 0.9em;'>
Hospital L&D Verification Tool - Detailed Analysis Mode<br>
Preserves original data and adds comprehensive verification columns
</div>
""", unsafe_allow_html=True)

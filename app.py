
import streamlit as st
import pandas as pd
import sys
from io import BytesIO
import json

sys.path.append('.')
from verification_helper import load_config, process_dataframe_real, export_with_timestamp

st.set_page_config(page_title="Hospital L&D Verification", page_icon="🏥", layout="wide")

st.title("🏥 Hospital Labor & Delivery Verification Tool")
st.write("Upload an Excel file and download verified results. Columns required: name, city, state, year.")

# Load base config to prefill keyword inputs
base_cfg = load_config('hospital_verification_config.json')
base_pos = base_cfg['search_instructions']['keywords']['maternity_positive']
base_neg = base_cfg['search_instructions']['keywords']['maternity_negative']

# Provide a template download
template_df = pd.DataFrame({
    'name': ['HOSPITAL A', 'HOSPITAL B'],
    'city': ['CITY', 'CITY'],
    'state': ['WA', 'WA'],
    'year': [2024, 2024]
})
buffer = BytesIO()
template_df.to_excel(buffer, index=False)
buffer.seek(0)
st.download_button('Download Input Template', buffer.getvalue(), file_name='hospital_input_template.xlsx')

uploaded_file = st.file_uploader("Upload .xlsx file", type=['xlsx'])

def validate_columns(df):
    required = ['name','city','state','year']
    missing = [c for c in required if c not in df.columns]
    return missing

st.subheader('Search keyword configuration')
col1, col2 = st.columns(2)
with col1:
    pos_text = st.text_area('Positive keywords (comma-separated)', value=', '.join(base_pos), height=120)
with col2:
    neg_text = st.text_area('Negative keywords (comma-separated)', value=', '.join(base_neg), height=120)

# Parse user-entered keywords safely
def parse_keywords(txt):
    parts = [p.strip() for p in str(txt).split(',')]
    return [p for p in parts if len(p) > 0]

if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file)
        missing = validate_columns(df)
        if len(missing) > 0:
            st.error('Missing required columns: ' + ', '.join(missing))
        else:
            st.success('Loaded ' + str(len(df)) + ' rows')
            st.subheader('Preview')
            st.dataframe(df.head(10))

            use_real_search = st.checkbox('Use real web search (slower, experimental)', value=False)

            if st.button('Run Verification'):
                with st.spinner('Processing, please wait...'):
                    cfg = load_config('hospital_verification_config.json')
                    # Inject user-configured keywords
                    cfg['search_instructions']['keywords']['maternity_positive'] = parse_keywords(pos_text)
                    cfg['search_instructions']['keywords']['maternity_negative'] = parse_keywords(neg_text)

                    result_df, count = process_dataframe_real(df.copy(), cfg, use_real_search=use_real_search)
                    st.success('Processed ' + str(count) + ' rows')
                    st.subheader('Results (first 15)')
                    st.dataframe(result_df.head(15))

                    out_xlsx = BytesIO()
                    result_df.to_excel(out_xlsx, index=False)
                    out_xlsx.seek(0)
                    st.download_button('Download Results', out_xlsx.getvalue(), file_name='verification_results.xlsx')
    except Exception as e:
        st.exception(e)


# verification_helper.py
# Utilities for hospital L&D verification with real search connectors

import json
import pandas as pd
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import time
from googlesearch import search

# Normalize strings
def norm(txt):
    if pd.isna(txt):
        return ''
    return str(txt).strip().lower()

# Load JSON configuration
def load_config(path='hospital_verification_config.json'):
    with open(path, 'r') as f:
        return json.load(f)

# Ensure output columns exist
def ensure_result_columns(df):
    result_cols = [
        'verified_ld_service',
        'ld_bed_count',
        'verification_source',
        'confidence_level',
        'notes',
        'discrepancy_flag'
    ]
    for c in result_cols:
        if c not in df.columns:
            df[c] = pd.NA
    return df

# Real search connectors
def query_hospital_website(name, city, state):
    snippets = []
    try:
        query = name + ' ' + city + ' ' + state + ' hospital maternity labor delivery'
        results = list(search(query, num_results=3, sleep_interval=2))
        for url in results[:2]:
            try:
                headers = {'User-Agent': 'Mozilla/5.0'}
                response = requests.get(url, headers=headers, timeout=10)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    text = soup.get_text(separator=' ', strip=True)
                    snippets.append({'source': 'Hospital website', 'text': text[:1000]})
                time.sleep(1)
            except:
                continue
    except:
        pass
    return snippets

def query_wa_doh(name, city):
    snippets = []
    try:
        url = 'https://fortress.wa.gov/doh/providercredentialsearch/SearchCriteria'
        search_term = name + ' ' + city
        params = {'searchTerm': search_term}
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, params=params, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            text_content = soup.get_text(separator=' ', strip=True)
            snippets.append({'source': 'WA Dept of Health', 'text': text_content[:500]})
    except:
        pass
    return snippets

def query_cms(name, city, state):
    snippets = []
    try:
        base_url = 'https://data.cms.gov/provider-data/api/1/search'
        query = name + ' ' + city
        params = {'query': query}
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(base_url, params=params, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data and 'results' in data:
                for result in data['results'][:2]:
                    snippets.append({'source': 'CMS data', 'text': str(result)[:500]})
    except:
        pass
    return snippets

def query_news(name, city, state):
    snippets = []
    try:
        query = name + ' ' + city + ' ' + state + ' hospital maternity closure news'
        results = list(search(query, num_results=2, sleep_interval=2))
        for url in results[:1]:
            try:
                headers = {'User-Agent': 'Mozilla/5.0'}
                response = requests.get(url, headers=headers, timeout=10)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    text = soup.get_text(separator=' ', strip=True)
                    snippets.append({'source': 'News articles', 'text': text[:800]})
                time.sleep(1)
            except:
                continue
    except:
        pass
    return snippets

# Build candidate snippets using real search
def build_candidate_snippets_real(row, cfg, use_real_search=True):
    name = str(row.get('name', '')).strip()
    city = str(row.get('city', '')).strip()
    state = str(row.get('state', 'WA')).strip()
    all_snippets = []
    
    if use_real_search:
        try:
            all_snippets.extend(query_hospital_website(name, city, state))
            time.sleep(2)
        except:
            pass
        try:
            all_snippets.extend(query_wa_doh(name, city))
            time.sleep(1)
        except:
            pass
        try:
            all_snippets.extend(query_cms(name, city, state))
            time.sleep(1)
        except:
            pass
        try:
            all_snippets.extend(query_news(name, city, state))
            time.sleep(1)
        except:
            pass
    
    return all_snippets

# Evaluate keyword evidence
def evaluate_evidence(snippets, cfg):
    pos_keys = [k.lower() for k in cfg['search_instructions']['keywords']['maternity_positive']]
    neg_keys = [k.lower() for k in cfg['search_instructions']['keywords']['maternity_negative']]
    exclusions = [k.lower() for k in cfg['search_instructions']['keywords']['facility_type_exclusions']]
    priorities = [p.lower() for p in cfg['search_instructions']['priority_sources']]

    best_source = None
    best_rank = 999
    matched_pos = set()
    matched_neg = set()
    exclusion_hit = False

    for s in snippets:
        src = norm(s.get('source', ''))
        text = norm(s.get('text', ''))
        for i, p in enumerate(priorities):
            if p in src and i < best_rank:
                best_rank = i
                best_source = s.get('source')
        for k in pos_keys:
            if k in text:
                matched_pos.add(k)
        for k in neg_keys:
            if k in text:
                matched_neg.add(k)
        for k in exclusions:
            if k in text:
                exclusion_hit = True

    if exclusion_hit and not matched_pos:
        decision = 'NO'
        confidence = 'HIGH'
    elif len(matched_pos) > 0 and best_rank <= 1:
        decision = 'YES'
        confidence = 'HIGH'
    elif len(matched_pos) > 0:
        decision = 'YES'
        confidence = 'MEDIUM'
    elif len(matched_neg) > 0 and best_rank <= 1:
        decision = 'NO'
        confidence = 'MEDIUM'
    else:
        decision = cfg['search_instructions']['evidence_rules']['no_clear_evidence']
        confidence = 'LOW'

    return {
        'decision': decision,
        'confidence': confidence,
        'best_source': best_source,
        'matched_positive': sorted(list(matched_pos)),
        'matched_negative': sorted(list(matched_neg))
    }

# Core processing function with real search
def process_dataframe_real(df, cfg, use_real_search=True):
    df = ensure_result_columns(df)
    count = 0
    for idx in df.index:
        row = df.loc[idx]
        snippets = build_candidate_snippets_real(row, cfg, use_real_search)
        evald = evaluate_evidence(snippets, cfg)
        df.loc[idx, 'verified_ld_service'] = evald['decision']
        df.loc[idx, 'confidence_level'] = evald['confidence']
        df.loc[idx, 'verification_source'] = evald['best_source']
        df.loc[idx, 'notes'] = 'Matched positive: ' + ', '.join(evald['matched_positive']) + ' | Matched negative: ' + ', '.join(evald['matched_negative'])
        if pd.isna(df.loc[idx, 'ld_bed_count']):
            df.loc[idx, 'ld_bed_count'] = 'Not Found'
        if pd.isna(df.loc[idx, 'discrepancy_flag']):
            df.loc[idx, 'discrepancy_flag'] = 'NO'
        count += 1
    return df, count

# Save output with timestamp
def export_with_timestamp(df, base_name='hospital_verification_output'):
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    path = base_name + '_' + stamp + '.xlsx'
    df.to_excel(path, index=False)
    return path

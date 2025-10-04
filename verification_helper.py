import json
import pandas as pd
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import time
import uuid
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def norm(txt):
    if pd.isna(txt):
        return ''
    return str(txt).strip().lower()

def load_config(path='hospital_verification_config.json'):
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"Config file not found: {path}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in config file: {e}")
        raise

def ensure_result_columns(df):
    result_cols = ['verified_ld_service', 'ld_bed_count', 'verification_source', 'confidence_level', 'notes', 'discrepancy_flag']
    for c in result_cols:
        if c not in df.columns:
            df[c] = pd.NA
    return df

def query_hospital_website(name: str, city: str, state: str) -> List[Dict[str, str]]:
    snippets = []
    try:
        from duckduckgo_search import DDGS
        query = f"{name} {city} {state} hospital maternity labor delivery"
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3))
            for result in results[:2]:
                try:
                    url = result.get('href', result.get('link', ''))
                    if not url:
                        continue
                    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                    response = requests.get(url, headers=headers, timeout=10)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        text = soup.get_text(separator=' ', strip=True)
                        snippets.append({'source': 'Hospital website', 'text': text[:1000], 'url': url})
                    time.sleep(1)
                except requests.RequestException as e:
                    logger.warning(f"Failed to fetch {url}: {e}")
                    continue
                except Exception as e:
                    logger.warning(f"Error processing search result: {e}")
                    continue
    except ImportError:
        logger.error("duckduckgo_search not installed. Install with: pip install duckduckgo-search")
    except Exception as e:
        logger.error(f"Search failed for {name}: {e}")
    return snippets

def query_wa_doh(name: str, city: str) -> List[Dict[str, str]]:
    snippets = []
    try:
        url = 'https://fortress.wa.gov/doh/providercredentialsearch/SearchCriteria'
        search_term = f"{name} {city}"
        params = {'searchTerm': search_term}
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, params=params, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            text_content = soup.get_text(separator=' ', strip=True)
            snippets.append({'source': 'WA Dept of Health', 'text': text_content[:500], 'url': url})
        else:
            logger.warning(f"WA DOH returned status {response.status_code}")
    except requests.RequestException as e:
        logger.warning(f"WA DOH query failed: {e}")
    except Exception as e:
        logger.error(f"Unexpected error in WA DOH query: {e}")
    return snippets

def query_cms(name: str, city: str, state: str) -> List[Dict[str, str]]:
    snippets = []
    try:
        base_url = 'https://data.cms.gov/provider-data/api/1/search'
        query = f"{name} {city}"
        params = {'query': query}
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(base_url, params=params, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data and 'results' in data:
                for result in data['results'][:2]:
                    snippets.append({'source': 'CMS data', 'text': str(result)[:500], 'url': base_url})
        else:
            logger.warning(f"CMS API returned status {response.status_code}")
    except requests.RequestException as e:
        logger.warning(f"CMS query failed: {e}")
    except json.JSONDecodeError as e:
        logger.warning(f"CMS returned invalid JSON: {e}")
    except Exception as e:
        logger.error(f"Unexpected error in CMS query: {e}")
    return snippets

def query_news(name: str, city: str, state: str) -> List[Dict[str, str]]:
    snippets = []
    try:
        from duckduckgo_search import DDGS
        query = f"{name} {city} {state} hospital maternity closure news"
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=2))
            for result in results[:1]:
                try:
                    url = result.get('href', result.get('link', ''))
                    if not url:
                        continue
                    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                    response = requests.get(url, headers=headers, timeout=10)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        text = soup.get_text(separator=' ', strip=True)
                        snippets.append({'source': 'News articles', 'text': text[:800], 'url': url})
                    time.sleep(1)
                except requests.RequestException as e:
                    logger.warning(f"Failed to fetch news from {url}: {e}")
                    continue
                except Exception as e:
                    logger.warning(f"Error processing news result: {e}")
                    continue
    except ImportError:
        logger.error("duckduckgo_search not installed")
    except Exception as e:
        logger.error(f"News search failed for {name}: {e}")
    return snippets

def build_candidate_snippets_real(row, cfg, use_real_search=True):
    name = str(row.get('name', '')).strip()
    city = str(row.get('city', '')).strip()
    state = str(row.get('state', 'WA')).strip()
    all_snippets = []
    if not use_real_search:
        return all_snippets
    sources = [(query_hospital_website, (name, city, state), 2), (query_wa_doh, (name, city), 1), (query_cms, (name, city, state), 1), (query_news, (name, city, state), 1)]
    for func, args, delay in sources:
        try:
            results = func(*args)
            all_snippets.extend(results)
            time.sleep(delay)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}")
            continue
    return all_snippets

def build_candidate_snippets_async(row, cfg, use_real_search=True):
    name = str(row.get('name', '')).strip()
    city = str(row.get('city', '')).strip()
    state = str(row.get('state', 'WA')).strip()
    all_snippets = []
    if not use_real_search:
        return all_snippets
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(query_hospital_website, name, city, state): 'website', executor.submit(query_wa_doh, name, city): 'doh', executor.submit(query_cms, name, city, state): 'cms', executor.submit(query_news, name, city, state): 'news'}
        for future in as_completed(futures):
            source_type = futures[future]
            try:
                results = future.result(timeout=15)
                all_snippets.extend(results)
            except Exception as e:
                logger.error(f"Error in {source_type} search: {e}")
    return all_snippets

def evaluate_evidence(snippets: List[Dict[str, str]], cfg: Dict[str, Any]) -> Dict[str, Any]:
    pos_keys = [k.lower() for k in cfg['search_instructions']['keywords']['maternity_positive']]
    neg_keys = [k.lower() for k in cfg['search_instructions']['keywords']['maternity_negative']]
    exclusions = [k.lower() for k in cfg['search_instructions']['keywords']['facility_type_exclusions']]
    priorities = [p.lower() for p in cfg['search_instructions']['priority_sources']]
    best_source = None
    best_rank = 999
    matched_pos = set()
    matched_neg = set()
    exclusion_hit = False
    urls = []
    for s in snippets:
        src = norm(s.get('source', ''))
        text = norm(s.get('text', ''))
        url = s.get('url', '')
        if url:
            urls.append(url)
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
    elif len(matched_pos) >= 2 and best_rank <= 1:
        decision = 'YES'
        confidence = 'HIGH'
    elif len(matched_pos) > 0 and best_rank <= 1:
        decision = 'YES'
        confidence = 'MEDIUM'
    elif len(matched_pos) > 0:
        decision = 'YES'
        confidence = 'LOW'
    elif len(matched_neg) > 0 and best_rank <= 1:
        decision = 'NO'
        confidence = 'MEDIUM'
    elif len(matched_neg) > 0:
        decision = 'NO'
        confidence = 'LOW'
    else:
        decision = cfg['search_instructions']['evidence_rules']['no_clear_evidence']
        confidence = 'LOW'
    return {'decision': decision, 'confidence': confidence, 'best_source': best_source, 'matched_positive': sorted(list(matched_pos)), 'matched_negative': sorted(list(matched_neg)), 'urls': urls[:3]}

def process_dataframe_real(df, cfg, use_real_search=True, use_async=False, progress_callback=None):
    df = ensure_result_columns(df)
    count = 0
    total = len(df)
    search_func = build_candidate_snippets_async if use_async else build_candidate_snippets_real
    for idx in df.index:
        row = df.loc[idx]
        try:
            snippets = search_func(row, cfg, use_real_search)
            evald = evaluate_evidence(snippets, cfg)
            df.loc[idx, 'verified_ld_service'] = evald['decision']
            df.loc[idx, 'confidence_level'] = evald['confidence']
            df.loc[idx, 'verification_source'] = evald.get('best_source', 'None')
            notes_parts = []
            if evald['matched_positive']:
                notes_parts.append(f"Positive: {', '.join(evald['matched_positive'])}")
            if evald['matched_negative']:
                notes_parts.append(f"Negative: {', '.join(evald['matched_negative'])}")
            if evald.get('urls'):
                notes_parts.append(f"URLs checked: {len(evald['urls'])}")
            df.loc[idx, 'notes'] = ' | '.join(notes_parts) if notes_parts else 'No evidence found'
            if pd.isna(df.loc[idx, 'ld_bed_count']):
                df.loc[idx, 'ld_bed_count'] = 'Not Found'
            if pd.isna(df.loc[idx, 'discrepancy_flag']):
                df.loc[idx, 'discrepancy_flag'] = 'NO'
            count += 1
            if progress_callback:
                progress_callback(count, total)
        except Exception as e:
            logger.error(f"Error processing row {idx}: {e}")
            df.loc[idx, 'verified_ld_service'] = 'ERROR'
            df.loc[idx, 'confidence_level'] = 'ERROR'
            df.loc[idx, 'notes'] = f"Processing error: {str(e)}"
            count += 1
            if progress_callback:
                progress_callback(count, total)
    return df, count

def export_with_timestamp(df, base_name='hospital_verification_output'):
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    unique_id = str(uuid.uuid4())[:8]
    path = f"{base_name}_{stamp}_{unique_id}.xlsx"
    try:
        df.to_excel(path, index=False, engine='openpyxl')
        logger.info(f"Results exported to {path}")
        return path
    except Exception as e:
        logger.error(f"Failed to export results: {e}")
        raise
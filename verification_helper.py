"""
Hospital L&D Verification Helper - Enhanced for Detailed Verification
Handles comprehensive verification with discrepancy detection
"""

import json
import pandas as pd
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import time
import uuid
import logging
import re
from typing import List, Dict, Any, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def norm(txt):
    """Normalize text to lowercase string"""
    if pd.isna(txt):
        return ''
    return str(txt).strip().lower()


def load_config(path='hospital_verification_config.json'):
    """Load JSON configuration file"""
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
    """Ensure all required output columns exist"""
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


def query_hospital_website(name: str, city: str, state: str, address: str) -> List[Dict[str, str]]:
    """Search for hospital website information using DuckDuckGo with address"""
    snippets = []
    try:
        from duckduckgo_search import DDGS
        
        # More specific query with address
        query = f"{name} {address} {city} {state} labor delivery maternity"
        
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))
            
            for result in results[:3]:
                try:
                    url = result.get('href', result.get('link', ''))
                    if not url:
                        continue
                        
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    }
                    response = requests.get(url, headers=headers, timeout=10)
                    
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        text = soup.get_text(separator=' ', strip=True)
                        snippets.append({
                            'source': 'Hospital website',
                            'text': text[:1500],
                            'url': url
                        })
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
    """Query Washington Department of Health provider database"""
    snippets = []
    try:
        url = 'https://fortress.wa.gov/doh/providercredentialsearch/SearchCriteria'
        search_term = f"{name} {city}"
        params = {'searchTerm': search_term}
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            text_content = soup.get_text(separator=' ', strip=True)
            snippets.append({
                'source': 'WA Dept of Health',
                'text': text_content[:800],
                'url': url
            })
        else:
            logger.warning(f"WA DOH returned status {response.status_code}")
            
    except requests.RequestException as e:
        logger.warning(f"WA DOH query failed: {e}")
    except Exception as e:
        logger.error(f"Unexpected error in WA DOH query: {e}")
        
    return snippets


def query_cms_hospital_compare(name: str, city: str, state: str) -> List[Dict[str, str]]:
    """Query CMS Hospital Compare data"""
    snippets = []
    try:
        from duckduckgo_search import DDGS
        search_query = f'site:medicare.gov "{name}" {city} hospital compare'
        
        with DDGS() as ddgs:
            results = list(ddgs.text(search_query, max_results=2))
            
            for result in results[:1]:
                url = result.get('href', result.get('link', ''))
                if 'medicare.gov' in url:
                    try:
                        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
                        response = requests.get(url, headers=headers, timeout=10)
                        if response.status_code == 200:
                            soup = BeautifulSoup(response.text, 'html.parser')
                            text = soup.get_text(separator=' ', strip=True)
                            snippets.append({
                                'source': 'CMS Hospital Compare',
                                'text': text[:800],
                                'url': url
                            })
                    except:
                        pass
        
    except Exception as e:
        logger.warning(f"CMS query failed: {e}")
        
    return snippets


def query_news_and_changes(name: str, city: str, state: str, year: int) -> List[Dict[str, str]]:
    """Search for news about hospital changes, closures, or maternity service changes"""
    snippets = []
    try:
        from duckduckgo_search import DDGS
        
        query = f"{name} {city} {state} maternity closure merger {year}"
        
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3))
            
            for result in results[:2]:
                try:
                    url = result.get('href', result.get('link', ''))
                    if not url:
                        continue
                        
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    }
                    response = requests.get(url, headers=headers, timeout=10)
                    
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        text = soup.get_text(separator=' ', strip=True)
                        snippets.append({
                            'source': 'News articles',
                            'text': text[:1000],
                            'url': url
                        })
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


def extract_bed_count(text: str) -> Optional[str]:
    """Extract L&D bed count from text using regex patterns"""
    text_lower = text.lower()
    
    patterns = [
        r'(\d+)\s*(?:labor|l&d|maternity|birthing|delivery)\s*bed',
        r'(?:labor|l&d|maternity|birthing)\s*(?:unit|ward|center).*?(\d+)\s*bed',
        r'(\d+)\s*bed.*?(?:labor|maternity|birthing)',
        r'(?:labor|maternity).*?capacity.*?(\d+)',
        r'(\d+)\s*(?:labor|birthing)\s*room',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text_lower)
        if match:
            bed_count = match.group(1)
            if bed_count.isdigit() and 1 <= int(bed_count) <= 100:
                return bed_count
    
    return None


def build_candidate_snippets_detailed(row, cfg, use_real_search=True):
    """Build snippets from multiple sources with enhanced detail"""
    name = str(row.get('name', '')).strip()
    city = str(row.get('city', '')).strip()
    state = str(row.get('state', 'WA')).strip()
    address = str(row.get('address', '')).strip()
    year = int(row.get('year', 2024))
    
    all_snippets = []
    
    if not use_real_search:
        return all_snippets
    
    sources = [
        (query_hospital_website, (name, city, state, address), 2),
        (query_wa_doh, (name, city), 1),
        (query_cms_hospital_compare, (name, city, state), 1),
        (query_news_and_changes, (name, city, state, year), 1)
    ]
    
    for func, args, delay in sources:
        try:
            results = func(*args)
            all_snippets.extend(results)
            time.sleep(delay)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}")
            continue
    
    return all_snippets


def evaluate_evidence_detailed(snippets: List[Dict[str, str]], cfg: Dict[str, Any], 
                               include_bed_count: bool = True) -> Dict[str, Any]:
    """Evaluate evidence from snippets with bed count extraction"""
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
    bed_count = None

    for s in snippets:
        src = norm(s.get('source', ''))
        text = norm(s.get('text', ''))
        url = s.get('url', '')
        
        if url and url not in urls:
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
        
        if include_bed_count and bed_count is None:
            bed_count = extract_bed_count(text)

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

    return {
        'decision': decision,
        'confidence': confidence,
        'best_source': best_source,
        'matched_positive': sorted(list(matched_pos)),
        'matched_negative': sorted(list(matched_neg)),
        'urls': urls[:3],
        'bed_count': bed_count
    }


def check_discrepancy(row, verified_decision):
    """Check if verification results differ from original data"""
    if 'observice' not in row or pd.isna(row['observice']):
        return 'NO'
    
    observice = str(row['observice']).lower()
    
    if '0' in observice or 'none' in observice:
        expected = 'NO'
    elif '1' in observice or 'by staff' in observice:
        expected = 'YES'
    else:
        expected = 'UNKNOWN'
    
    if verified_decision == expected:
        return 'NO'
    elif verified_decision == 'UNKNOWN':
        return 'NO'
    else:
        return 'YES'


def process_dataframe_detailed(df, cfg, use_real_search=True, verify_mode="Re-verify all hospitals", 
                               include_bed_count=True, progress_callback=None):
    """Process dataframe with detailed verification and discrepancy detection"""
    df = ensure_result_columns(df)
    count = 0
    total = len(df)
    
    for idx in df.index:
        row = df.loc[idx]
        
        skip_verification = False
        
        if verify_mode == "Only verify if missing/empty":
            if pd.notna(df.loc[idx, 'verified_ld_service']) and df.loc[idx, 'verified_ld_service'] != '':
                skip_verification = True
        elif verify_mode == "Only verify discrepancies":
            if pd.notna(df.loc[idx, 'discrepancy_flag']) and df.loc[idx, 'discrepancy_flag'] == 'NO':
                skip_verification = True
        
        try:
            if skip_verification or not use_real_search:
                if pd.isna(df.loc[idx, 'verified_ld_service']) or df.loc[idx, 'verified_ld_service'] == '':
                    df.loc[idx, 'verified_ld_service'] = 'UNKNOWN'
                    df.loc[idx, 'confidence_level'] = 'LOW'
                    df.loc[idx, 'notes'] = 'Not verified - using existing data or skipped'
                    if pd.isna(df.loc[idx, 'ld_bed_count']) or df.loc[idx, 'ld_bed_count'] == '':
                        df.loc[idx, 'ld_bed_count'] = 'Not Found'
            else:
                snippets = build_candidate_snippets_detailed(row, cfg, use_real_search)
                evald = evaluate_evidence_detailed(snippets, cfg, include_bed_count)
                
                df.loc[idx, 'verified_ld_service'] = evald['decision']
                df.loc[idx, 'confidence_level'] = evald['confidence']
                df.loc[idx, 'verification_source'] = evald.get('best_source', 'None')
                
                if evald.get('urls'):
                    url_str = ', '.join(evald['urls'][:2])
                    df.loc[idx, 'verification_source'] = url_str
                
                notes_parts = []
                if evald['matched_positive']:
                    notes_parts.append(f"Positive: {', '.join(evald['matched_positive'][:3])}")
                if evald['matched_negative']:
                    notes_parts.append(f"Negative: {', '.join(evald['matched_negative'][:3])}")
                
                for snippet in snippets:
                    if snippet['source'] == 'News articles':
                        text_lower = snippet['text'].lower()
                        if 'closure' in text_lower or 'closed' in text_lower:
                            notes_parts.append("News: Possible closure mentioned")
                        if 'merger' in text_lower or 'acquired' in text_lower:
                            notes_parts.append("News: Merger/acquisition mentioned")
                
                df.loc[idx, 'notes'] = ' | '.join(notes_parts) if notes_parts else 'No specific notes'
                
                if evald.get('bed_count'):
                    df.loc[idx, 'ld_bed_count'] = evald['bed_count']
                else:
                    df.loc[idx, 'ld_bed_count'] = 'Not Found'
                
                discrepancy = check_discrepancy(row, evald['decision'])
                df.loc[idx, 'discrepancy_flag'] = discrepancy
            
            count += 1
            
            if progress_callback:
                progress_callback(count, total)
                
        except Exception as e:
            logger.error(f"Error processing row {idx}: {e}")
            df.loc[idx, 'verified_ld_service'] = 'ERROR'
            df.loc[idx, 'confidence_level'] = 'ERROR'
            df.loc[idx, 'notes'] = f"Processing error: {str(e)}"
            df.loc[idx, 'ld_bed_count'] = 'Not Found'
            df.loc[idx, 'discrepancy_flag'] = 'NO'
            count += 1
            
            if progress_callback:
                progress_callback(count, total)
    
    return df, count


def export_with_timestamp(df, base_name='hospital_verification_output'):
    """Export results with timestamp and unique ID"""
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

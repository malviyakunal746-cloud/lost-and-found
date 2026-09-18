# matching.py
from rapidfuzz import fuzz
from db import get_items

def calculate_match_score(lost_item, found_item):
    """
    Calculate match score between lost and found item.
    Returns score 0-100, or 0 if categories don't match.
    """
    # Hard filter: category must match
    if lost_item['category'] != found_item['category']:
        return 0
    
    # Weighted scoring
    desc_score = fuzz.partial_ratio(
        lost_item['description'].lower(),
        found_item['description'].lower()
    )
    
    location_score = fuzz.ratio(
        lost_item['location'].lower(),
        found_item['location'].lower()
    )
    
    # 70% description, 30% location
    final_score = (desc_score * 0.7) + (location_score * 0.3)
    
    return round(final_score, 1)

def find_matches(item, item_type, threshold=70):
    """
    Find matching items for a given lost/found item.
    
    Args:
        item: The item dict to match against
        item_type: 'lost' or 'found' (opposite type will be searched)
        threshold: Minimum score to consider a match (default 70)
    
    Returns:
        List of matching items with scores, sorted by score descending
    """
    opposite_type = 'found' if item_type == 'lost' else 'lost'
    opposite_items = get_items(item_type=opposite_type, status='open')
    
    matches = []
    for candidate in opposite_items:
        score = calculate_match_score(item, candidate)
        if score >= threshold:
            candidate_with_score = candidate.copy()
            candidate_with_score['match_score'] = score
            matches.append(candidate_with_score)
    
    # Sort by score (highest first)
    matches.sort(key=lambda x: x['match_score'], reverse=True)
    
    return matches
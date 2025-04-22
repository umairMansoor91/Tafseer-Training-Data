import re
import json
from bs4 import BeautifulSoup

file = "001.htm"
with open(file, 'r', encoding="utf-8") as f:
    soup = BeautifulSoup(f, "html.parser")

def remove_diacritics(text):
    """Remove Arabic diacritics and invisible characters"""
    text = re.sub(r'[\u064B-\u0652]', '', text)  # diacritics
    text = text.replace('\u200c', '')  # zero-width non-joiner
    return text.strip()

def extract_number_from_text(text):
    """Extract number from the beginning of text like '1 - ...'"""
    match = re.match(r'^\s*(\d+)\s*[-–\.\)]*', text)
    if match:
        return int(match.group(1))
    return None

# Find all title elements
title_elements = soup.find_all(attrs={"data-type": "title"})

# Create data structure
document_structure = {
    "kitaabs": []
}

# Create a list to store all section elements with their hierarchy
all_sections = []

# First pass: Identify all kitaabs and baabs
for element in title_elements:
    text = remove_diacritics(element.get_text())
    
    # Check for kitaab title
    if re.match(r'^\s*(\d+\s*[-–\.\)]*\s*)*كتاب', text):
        kitaab_num = extract_number_from_text(text)
        all_sections.append({
            'type': 'kitaab',
            'element': element,
            'number': kitaab_num,
            'title': text,
            'id': element.get('id', ''),
        })
        print(f"Found Kitaab {kitaab_num}: {text}")
    
    # Check for baab title
    elif re.match(r'^\s*(\d+\s*[-–\.\)]*\s*)*باب', text):
        baab_num = extract_number_from_text(text)
        all_sections.append({
            'type': 'baab',
            'element': element,
            'number': baab_num,
            'title': text, 
            'id': element.get('id', ''),
        })
        print(f"Found Baab {baab_num}: {text[:50]}..." if len(text) > 50 else f"Found Baab {baab_num}: {text}")

# Build the structure and extract content
current_kitaab = None

for i, section in enumerate(all_sections):
    if section['type'] == 'kitaab':
        # Create new kitaab
        current_kitaab = {
            "number": section['number'],
            "title": section['title'],
            "baabs": [],
            "id": section['id']
        }
        document_structure["kitaabs"].append(current_kitaab)
    elif section['type'] == 'baab' and current_kitaab is not None:
        # Create new baab
        current_baab = {
            "number": section['number'],
            "title": section['title'],
            "context": [],
            "id": section['id']
        }
        current_kitaab["baabs"].append(current_baab)
        
        # Extract content between this baab and the next section
        content = []
        
        # Get current element and find all following elements until next section
        current_element = section['element']
        next_element = None
        
        # Find next section element if it exists
        if i < len(all_sections) - 1:
            next_element = all_sections[i + 1]['element']
        
        # Get all siblings between current and next
        next_sibling = current_element.find_next_sibling()
        while next_sibling and (next_element is None or next_sibling != next_element):
            # Skip title elements and collect content
            if next_sibling.get('data-type') != 'title' and next_sibling.get_text().strip():
                content.append(next_sibling.get_text().strip())
            next_sibling = next_sibling.find_next_sibling()
        
        # Also check for content in parent container's siblings
        if not content and current_element.parent:
            next_parent_sibling = current_element.parent.find_next_sibling()
            while next_parent_sibling and (next_element is None or next_element not in next_parent_sibling.find_all(recursive=True)):
                # Get all paragraph elements in this container
                for p in next_parent_sibling.find_all('p'):
                    if p.get_text().strip():
                        content.append(p.get_text().strip())
                next_parent_sibling = next_parent_sibling.find_next_sibling()
        
        # Add collected content to baab
        current_baab["context"] = content

# Write the structure to a JSON file
with open('hadith_structure.json', 'w', encoding='utf-8') as json_file:
    json.dump(document_structure, json_file, ensure_ascii=False, indent=2)

print("\nJSON structure has been saved to 'hadith_structure.json'")
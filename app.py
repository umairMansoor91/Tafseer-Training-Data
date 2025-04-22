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

# Function to get full HTML content between elements
def get_full_content_between(start_element, end_element=None):
    content = []
    current = start_element.next_element
    
    while current and current != end_element:
        # Check if this is a title element
        parent = current.parent
        is_title = False
        while parent:
            if parent.get('data-type') == 'title':
                is_title = True
                break
            parent = parent.parent
            
        # If not a title and has text, add it
        if not is_title and isinstance(current, str) and current.strip():
            content.append(current.strip())
        elif hasattr(current, 'get_text') and not is_title:
            text = current.get_text().strip()
            if text:
                content.append(text)
                
        current = current.next_element
    
    return content

# Find all pages to process
pages = soup.find_all('div', class_="PageText")

# Create a flat representation of the document to ensure we capture everything
document_flat = []
for page in pages:
    elements = page.find_all(['div', 'p', 'span'], recursive=True)
    for element in elements:
        # Store text content and attributes
        if element.get_text().strip():
            document_flat.append({
                'element': element,
                'text': element.get_text().strip(),
                'data_type': element.get('data-type'),
                'id': element.get('id', '')
            })

# Create data structure
document_structure = {
    "kitaabs": []
}

# Identify kitaabs and baabs
sections = []
for item in document_flat:
    text = remove_diacritics(item['text'])
    
    if item['data_type'] == 'title':
        # Check for kitaab title
        if re.match(r'^\s*(\d+\s*[-–\.\)]*\s*)*كتاب', text):
            num = extract_number_from_text(text)
            sections.append({
                'type': 'kitaab',
                'element': item['element'],
                'number': num,
                'title': text,
                'id': item['id'],
                'index': document_flat.index(item)
            })
            print(f"Found Kitaab {num}: {text}")
        
        # Check for baab title
        elif re.match(r'^\s*(\d+\s*[-–\.\)]*\s*)*باب', text):
            num = extract_number_from_text(text)
            sections.append({
                'type': 'baab',
                'element': item['element'],
                'number': num,
                'title': text,
                'id': item['id'],
                'index': document_flat.index(item)
            })
            print(f"Found Baab {num}: {text[:50]}..." if len(text) > 50 else f"Found Baab {num}: {text}")

# Build the document structure
current_kitaab = None
for i, section in enumerate(sections):
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
        
        # Get content between this baab and the next section
        current_index = section['index']
        next_section = None
        if i < len(sections) - 1:
            next_section = sections[i + 1]
            next_index = next_section['index']
        else:
            next_index = len(document_flat)
        
        # Collect all content between this baab and the next section
        raw_content = ""
        for j in range(current_index + 1, next_index):
            if j < len(document_flat):
                item = document_flat[j]
                if item['data_type'] != 'title':
                    text = item['text'].strip()
                    if text:
                        raw_content += text + "\n\n"
        
        # Clean up the content
        if raw_content:
            # Store the complete raw content
            current_baab["context"] = [raw_content.strip()]

# Write the structure to a JSON file
with open('hadith_structure.json', 'w', encoding='utf-8') as json_file:
    json.dump(document_structure, json_file, ensure_ascii=False, indent=2)

print("\nJSON structure has been saved to 'hadith_structure.json'")
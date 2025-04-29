import re
import json
from bs4 import BeautifulSoup, NavigableString, Tag

# Load HTML
file = "013.htm"
output_file= '013.json'
try:
    with open(file, 'r', encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")
except FileNotFoundError:
    print(f"Error: File '{file}' not found.")
    exit()
except Exception as e:
    print(f"Error reading file: {e}")
    exit()

# Helpers
def remove_diacritics(text):
    if not isinstance(text, str):
        return ""
    text = re.sub(r'[\u064B-\u0652]', '', text)
    text = text.replace('\u200c', '') 
    return text.strip()

def is_strict_number_line(text):
    if not isinstance(text, str):
        return False
    # Matches start, optional whitespace, digits, whitespace, one of -, –, ., ), optional whitespace, end
    # Capture the number group
    match = re.match(r'^\s*(\d+)\s*[-–\.\)]*\s*$', text)
    return match 

# Helper to check if a string contains ONLY "باب"
# Used for Sub-Baab part 2
def is_strict_baab_line(text):
     if not isinstance(text, str):
        return False
     text = remove_diacritics(text)
     # Matches start, optional whitespace, 'باب', optional whitespace, end
     return re.match(r'^\s*باب\s*$', text)


# Reuse existing helpers for general number/baab patterns if needed elsewhere
def extract_number_from_text(text):
    # Use the strict number line checker to get the number accurately if it's a strict line
    match = is_strict_number_line(text)
    if match:
        return int(match.group(1))

    # Fallback for non-strict patterns if needed, although strict is preferred for markers
    if not isinstance(text, str):
        return None
    match = re.match(r'^\s*(\d+)\s*[-–\.\)]*\s*', text)
    return int(match.group(1)) if match else None

def is_baab_pattern(text):
    if not isinstance(text, str):
        return False
    text = remove_diacritics(text)
    return re.match(r'^\s*(\d+[\s*–\-.\)]+\s*)?باب', text)


def extract_hadith_number(text):
    # This helper is currently used only during flattening, might not be needed later
    if not isinstance(text, str):
        return None
    match1 = re.match(r'^\s*(\d+)\s*[-–\.\)]', text)
    match2 = re.search(r'\[\s*الحديث\s*(\d+)\s*[-–\.]', text)
    if match1:
        return int(match1.group(1))
    elif match2:
        return int(match2.group(1))
    else:
        return None


# Flatten document - Iterate contents to preserve order, using global position
pages = soup.find_all('div', class_="PageText")
document_flat = []
position_counter = 0 # Global counter

if not pages:
    print("Warning: No div with class 'PageText' found. Check your HTML structure.")

for page_idx, page in enumerate(pages):
    for content in page.contents:
        item = None

        # Process NavigableString (direct text)
        if isinstance(content, NavigableString) and content.strip():
             item = {
                'element': None,
                'text': content.strip(),
                'type': 'direct_text',
                'data_type': None,
                'id': '',
                'html': str(content),
                'page_idx': page_idx,
                'position': position_counter
            }
        # Process Tag elements (like p, div, etc.)
        elif isinstance(content, Tag):
             cleaned_text = content.get_text().strip()
             if cleaned_text:
                 item = {
                     'element': content,
                     'text': cleaned_text,
                     'type': content.name,
                     'data_type': content.get('data-type'),
                     'id': content.get('id', ''),
                     'html': str(content),
                     'page_idx': page_idx,
                     'position': position_counter
                 }
                 if content.name == 'p':
                      # We'll extract Hadith number during structure building
                      pass # item['hadith_number'] = extract_hadith_number(cleaned_text) is now done later
                 if content.name == 'div' and 'PageHead' in content.get('class', []):
                      item['type'] = 'pagehead'

        if item:
            document_flat.append(item)
            position_counter += 1


print(f"Flattened document contains {len(document_flat)} items.")

# Initialize structure
document_structure = {"kitaabs": []}
current_kitaab = None
current_baab = None
current_baab_context = [] 
current_context_list = None 
current_sub_baab = None 
current_hadith = None 

# Process each item sequentially from the ordered document_flat using an index
print("Starting structure processing...")
i = 0
while i < len(document_flat):
    item = document_flat[i]
    text = remove_diacritics(item.get('text', ''))
   

    # --- Kitaab Detection ---
    is_kitaab = item.get('data_type') == 'title' and re.match(r'^\s*(\d+[\s*–\-.\)]+\s*)?كتاب', text)

    if is_kitaab:
        print(f"--- Detected KITAAB: {item['text'][:80]} ---")

        # Close previous hadith if active (its content is already added)
        if current_hadith:
            print(f"  Closed previous HADITH ({current_hadith.get('hadith_number', 'N/A')})")
            current_hadith = None # Reset hadith state

        # Close previous sub-baab if active (its content is already added)
        if current_sub_baab:
             print(f"  Closed previous SUB-BAAB ({current_sub_baab.get('number', 'N/A')})")
             current_sub_baab = None # Reset sub-baab state


        # Close the previous Baab if one is open within the current Kitaab
        if current_baab and current_kitaab:
            # Ensure the context list for the *main* baab is used when closing
            current_baab['context'] = current_baab_context
            current_kitaab['baabs'].append(current_baab)
            print(f"  Closed previous BAAB ({current_baab.get('number', 'N/A')}) with {len(current_baab_context)} context items.")
            current_baab_context = [] 
            current_baab = None 


        # Close the previous Kitaab if one is open
        if current_kitaab:
             document_structure['kitaabs'].append(current_kitaab)
             print(f"  Closed previous KITAAB ({current_kitaab.get('number', 'N/A')}).")

        # Start a new Kitaab
        kitaab_number = extract_number_from_text(text)
        current_kitaab = {
            "number": kitaab_number if kitaab_number is not None else len(document_structure['kitaabs']) + 1,
            "title": item['text'].strip(),
            "baabs": [],
            "id": item.get('id', f"kitaab-{item['position']}")
        }
        print(f"  Started new KITAAB: Number={current_kitaab['number']}, Title='{current_kitaab['title'][:80]}...'")

        # Reset all context/baab/sub-baab/hadith state
        current_baab = None
        current_baab_context = []
        current_context_list = None 
        current_sub_baab = None
        current_hadith = None
        i += 1 
        continue 


    # --- Baab Detection ---
    is_baab = is_baab_pattern(text)
    baab_condition = (item.get('data_type') == 'title' and is_baab) or \
                     (current_kitaab and item['type'] == 'p' and is_baab)

    if baab_condition:
         if not current_kitaab:
              print(f"Warning: Detected a potential BAAB pattern ('{item['text'][:80]}...') but no current KITAAB is active. Skipping BAAB.")
              i += 1 
              continue 
         else:
             print(f"--- Detected BAAB: {item['text'][:80]} --- (Item type: {item['type']}, data-type: {item.get('data-type')})")

             # Close previous hadith if active
             if current_hadith:
                  print(f"  Closed previous HADITH ({current_hadith.get('hadith_number', 'N/A')})")
                  current_hadith = None 

             # Close previous sub-baab if active
             if current_sub_baab:
                  print(f"  Closed previous SUB-BAAB ({current_sub_baab.get('number', 'N/A')})")
                  current_sub_baab = None 


             # Close the previous Baab if it exists within the current Kitaab
             if current_baab:
                 current_baab['context'] = current_baab_context 
                 current_kitaab['baabs'].append(current_baab)
                 print(f"  Closed previous BAAB ({current_baab.get('number', 'N/A')}) with {len(current_baab_context)} context items.")


             # Start a new Baab
             baab_number = extract_number_from_text(text)
             current_baab_context = [] 
             current_baab = {
                 "number": baab_number if baab_number is not None else len(current_kitaab['baabs']) + 1,
                 "title": item['text'].strip(),
                 "context": current_baab_context, 
                 "id": item.get('id', f"baab-{item['position']}")
             }

             # Set the context list pointer to the main baab context initially
             current_context_list = current_baab_context
             current_sub_baab = None 
             current_hadith = None 

             print(f"  Started new BAAB: Number={current_baab['number']}, Title='{current_baab['title'][:80]}...'")
             i += 1 # Consume the Baab item
             continue


    # --- Sub-Baab Detection (requires lookahead) ---
    # Check if we are in a Baab AND there is a next item
    is_sub_baab_marker = False
    if current_baab and i + 1 < len(document_flat):
        next_item = document_flat[i+1]
        # Use original text for strict matching
        item_original_text = item.get('text', '')
        next_item_original_text = next_item.get('text', '')

        # Check if current item is strict number line AND next item is strict 'باب' line
        if is_strict_number_line(item_original_text) and is_strict_baab_line(next_item_original_text):
             is_sub_baab_marker = True

    if is_sub_baab_marker:
         print(f"--- Detected SUB-BAAB marker: '{item.get('text', '')[:40]}' AND '{next_item.get('text', '')[:40]}' ---")

         # Close previous hadith if active (its content is already added)
         if current_hadith:
             print(f"  Closed previous HADITH ({current_hadith.get('hadith_number', 'N/A')})")
             current_hadith = None # Reset hadith state

         # Close the previous sub-baab if one was active
         if current_sub_baab:
             print(f"  Closed previous SUB-BAAB ({current_sub_baab.get('number', 'N/A')})")
             # The closed sub-baab dictionary is already appended to current_baab_context

         # Start a new Sub-Baab
         sub_baab_number = extract_number_from_text(item.get('text', ''))
         # Combine the two lines for the sub-baab title
         sub_baab_title = f"{item.get('text', '').strip()} {next_item.get('text', '').strip()}".strip()

         # Create the sub-baab dictionary
         new_sub_baab = {
             "number": sub_baab_number if sub_baab_number is not None else len([c for c in current_baab_context if isinstance(c, dict)]) + 1, # Count dicts in main context
             "title": sub_baab_title,
             "context": [] # Initialize context list for this sub-baab
         }
         # Append the new sub-baab dictionary DIRECTLY to the main baab's context list
         current_baab_context.append(new_sub_baab)
         # Update the context list pointer to the new sub-baab's context list
         current_context_list = new_sub_baab['context']
         # Set the current sub-baab state
         current_sub_baab = new_sub_baab
         current_hadith = None # Ensure no hadith is active within the sub-baab title marker

         print(f"  Started new SUB-BAAB: Number={current_sub_baab['number']}, Title='{current_sub_baab['title'][:80]}...'")

         i += 2 # Consume both the number line and the 'باب' line
         continue # Move to the next item


    # --- Hadith Detection ---
    # Check if we are in a Baab (or Sub-Baab) AND the current item is a strict number line
    # AND it's NOT the start of a Sub-Baab marker (checked above)
    is_hadith_marker = False
    hadith_number_match = is_strict_number_line(item.get('text', '')) # Check if it's a strict number line

    # Only proceed if it's a strict number line AND we are in a Baab/Sub-Baab context
    if current_baab and hadith_number_match:
        # Now, check if it's NOT followed by a strict 'باب' line (which would make it a Sub-Baab marker)
        # We already checked `i + 1 < len(document_flat)` in the Sub-Baab detection block.
        # If we reach here and it's a strict number line, it means it wasn't a Sub-Baab marker.
        # So, if hadith_number_match is not None, it's a Hadith marker.
        is_hadith_marker = True


    if is_hadith_marker:
         hadith_number = int(hadith_number_match.group(1)) # Extract number from the match object
         print(f"--- Detected HADITH marker: '{item.get('text', '')[:40]}' (Number: {hadith_number}) ---")

         # Close the previous hadith if one was active
         if current_hadith:
             # Its content was added via the current_context_list pointer
             print(f"  Closed previous HADITH ({current_hadith.get('hadith_number', 'N/A')})")
             # The closed hadith dictionary is already appended to the parent context list

         # Start a new Hadith block
         new_hadith = {
             "hadith_number": hadith_number,
             "context": [] # Initialize context list for this hadith
             # No "type" or "title" key needed as per desired structure
         }
         # Append the new hadith dictionary to the list currently pointed to by current_context_list
         # This list is either current_baab_context or current_sub_baab['context']
         if current_context_list is not None:
              current_context_list.append(new_hadith)
         else:
              # This should ideally not happen if current_baab is active
              print(f"Error: current_context_list is None when detecting HADITH for item {i} ({item['text'][:50]}...)")


         # Update the context list pointer to the new hadith's context list
         current_context_list = new_hadith['context']
         # Set the current hadith state
         current_hadith = new_hadith
         # current_sub_baab remains unchanged (a hadith is *inside* a baab or sub-baab)


         # Append the current item's text (the marker line) as the first line of the hadith's content
         cleaned_text = item.get('text', '').strip()
         if cleaned_text:
              # print(f"  Adding marker line to HADITH {current_hadith['hadith_number']}: '{cleaned_text[:80]}...'")
              current_context_list.append(cleaned_text) # Append just the string

         i += 1 # Consume the Hadith marker item
         continue # Move to the next item


    # --- Content Accumulation ---
    # Add text to the current context list (main baab, sub-baab context, or hadith context)
    # if we are inside a Baab AND the item is NOT a structural title AND NOT a pagehead.
    # We rely on the detection steps above to consume structural elements and markers.
    if current_baab and item.get('data_type') != 'title' and item.get('type') != 'pagehead':
         cleaned_text = item.get('text', '').strip()
         if cleaned_text:
             # Append the cleaned text (string) to the list currently pointed to by current_context_list
             if current_context_list is not None:
                  # print(f"  Adding content to context ({'HADITH' if current_hadith else ('Sub-Baab' if current_sub_baab else 'Main Baab')}): '{cleaned_text[:80]}...'")
                  current_context_list.append(cleaned_text) # Append just the string
             else:
                  # This case should ideally not happen if current_baab is active
                  print(f"Error: current_context_list is None but current_baab is active for item {i} ({item['text'][:50]}...)")
         i += 1 # Consume the content item
         continue

    # --- Handle other items (e.g., items not part of structure or content) ---
    # If the item was not consumed by any of the above conditions, just skip it
    # print(f"  Skipping item {i} (Page {item['page_idx']}, Pos {item['position']}): Type={item['type']}, Data-type={item.get('data_type')}.")
    i += 1 # Consume the skipped item


# --- Finish the last Kitaab, Baab, Sub-Baab, and Hadith ---
print("Finishing structure processing...")

# Close the very last hadith if one was open. Its content is already in its context list.
if current_hadith:
    print(f"  Closed final HADITH ({current_hadith.get('hadith_number', 'N/A')})")
    # The hadith dict is already appended to its parent context list (sub-baab or main baab)

# Close the very last sub-baab if one was open. Its content is already in its context.
if current_sub_baab:
    print(f"  Closed final SUB-BAAB ({current_sub_baab.get('number', 'N/A')})")
    # The sub-baab dict is already appended to current_baab_context


# Close the very last Baab if one was open
if current_baab and current_kitaab:
    current_baab['context'] = current_baab_context # Ensure main baab context is finalized
    current_kitaab['baabs'].append(current_baab)
    print(f"  Closed final BAAB ({current_baab.get('number', 'N/A')}) with {len(current_baab_context)} context items.")

# Close the very last Kitaab if one was open
if current_kitaab:
    document_structure['kitaabs'].append(current_kitaab)
    print(f"  Closed final KITAAB ({current_kitaab.get('number', 'N/A')}).")
else:
    print("No KITAABs were detected in the document.")


# Save output
try:
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(document_structure, f, ensure_ascii=False, indent=2)
    print(f"✅ Hadith structure saved to {output_file}")
except Exception as e:
    print(f"Error saving JSON file: {e}")
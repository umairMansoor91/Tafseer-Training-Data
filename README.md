# 📚 Tafseer Training Data Extractor

This project extracts structured data (Kitaab → Baab → Sub-Baab → Hadith) from Islamic HTML documents (like Tafseer or Hadith books) and outputs them into a structured JSON format suitable for downstream tasks such as training NLP models or building knowledge bases.

---

## 🔧 Features

- Parses HTML content using `BeautifulSoup`.
- Detects and structures:
  - **Kitaab (Book)**
  - **Baab (Chapter)**
  - **Sub-Baab (Subsection)**
  - **Hadith (Narration)** blocks.
- Outputs a clean, hierarchical **JSON** format.

---

## 🧠 How It Works

The script processes a structured HTML file (`013.htm`) with Islamic text, and:

1. Flattens the DOM structure.
2. Iteratively scans through all text and tag elements.
3. Uses regex and heuristics to detect Kitaabs, Baabs, Sub-Baabs, and Hadith markers.
4. Maintains context pointers to properly nest Hadith and related content.
5. Writes output to JSON file.

---

## 📁 Input File

Make sure a file named `0--.htm` exists in the root directory with proper HTML formatting containing your Tafseer/Hadith content. The structure should include `div` tags with class `PageText`.

---

## 🧾 Output Format

The output is a JSON file (`013.json`) with the following structure:

```json
{
  "kitaabs": [
    {
      "number": 1,
      "title": "كتاب الصلاة",
      "id": "kitaab-1",
      "baabs": [
        {
          "number": 1,
          "title": "باب فضل الصلاة",
          "id": "baab-1",
          "context": [
            "Introductory text",
            {
              "number": 1,
              "title": "1 باب",
              "context": [
                {
                  "hadith_number": 101,
                  "context": [
                    "Narration text line 1",
                    "Narration text line 2"
                  ]
                }
              ]
            }
          ]
        }
      ]
    }
  ]
}

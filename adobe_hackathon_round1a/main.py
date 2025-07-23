import os
import json
import fitz  # PyMuPDF
import re

def is_heading_candidate(text, font_size, is_bold, prev_font_size=None):
    """
    Determine if a text block is likely a heading based on multiple factors.
    """
    # Skip URLs and very short text (unless it's very large/bold)
    if re.match(r'https?://\S+|www\.\S+', text):
        return False
    if len(text.split()) < 2 and not (is_bold and font_size > 14):
        return False
    
    # Common heading characteristics
    is_all_caps = text == text.upper()
    ends_with_colon = text.strip().endswith(':')
    is_short = len(text.split()) <= 8
    
    # Heading likelihood score
    score = 0
    if is_bold: score += 2
    if is_all_caps: score += 1
    if ends_with_colon: score += 1
    if is_short: score += 1
    if font_size > 12: score += 1
    if prev_font_size and font_size > prev_font_size + 2: score += 2
    
    return score >= 3  # Minimum threshold to be considered a heading

def detect_headings(pdf_path):
    doc = fitz.open(pdf_path)
    heading_candidates = []
    prev_font_size = None

    for page_num, page in enumerate(doc, start=1):
        blocks = page.get_text("dict")["blocks"]
        for block in blocks:
            if "lines" in block:
                for line in block["lines"]:
                    text = ""
                    font_sizes = []
                    is_bold = False
                    for span in line["spans"]:
                        text += span["text"]
                        font_sizes.append(span["size"])
                        if "weight" in span and span["weight"] >= 600:
                            is_bold = True
                    
                    text = text.strip()
                    if not text:
                        continue
                    
                    avg_font_size = sum(font_sizes) / len(font_sizes)
                    
                    if is_heading_candidate(text, avg_font_size, is_bold, prev_font_size):
                        heading_candidates.append({
                            "text": text,
                            "size": avg_font_size,
                            "page": page_num,
                            "bold": is_bold
                        })
                    prev_font_size = avg_font_size

    if not heading_candidates:
        return {"title": "", "outline": []}

    # Cluster font sizes to determine heading levels
    sizes = [c["size"] for c in heading_candidates]
    unique_sizes = sorted(list(set(sizes)), reverse=True)
    
    # Assign heading levels based on size clusters
    size_to_level = {}
    for i, size in enumerate(unique_sizes[:3]):  # Only consider top 3 sizes for H1-H3
        size_to_level[size] = f"H{i+1}"
    
    # Determine title (first H1 candidate)
    title = ""
    outline = []
    
    # Find the most prominent heading as title
    if unique_sizes:
        largest_size = unique_sizes[0]
        potential_titles = [c for c in heading_candidates if c["size"] == largest_size]
        if potential_titles:
            title = potential_titles[0]["text"]
    
    # Build outline, skipping the title if it appears again
    for candidate in heading_candidates:
        level = size_to_level.get(candidate["size"], None)
        if not level:
            continue
        
        # Skip the title if it appears again in the document
        if candidate["text"] == title and level == "H1":
            continue
            
        outline.append({
            "level": level,
            "text": candidate["text"],
            "page": candidate["page"]
        })

    # Sort outline by heading level (H1 first, then H2, etc.) and then by page number
    outline.sort(key=lambda x: (x["level"], x["page"]))

    return {"title": title, "outline": outline}

def process_all_pdfs(input_dir, output_dir):
    for filename in os.listdir(input_dir):
        if filename.lower().endswith(".pdf"):
            pdf_path = os.path.join(input_dir, filename)
            try:
                result = detect_headings(pdf_path)
                output_filename = os.path.splitext(filename)[0] + ".json"
                output_path = os.path.join(output_dir, output_filename)
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)
            except Exception as e:
                print(f"Error processing {filename}: {str(e)}")

if __name__ == "__main__":
    if os.path.exists("app/input"):
        input_dir = "app/input"
        output_dir = "app/output"
    else:
        input_dir = "/app/input"
        output_dir = "/app/output"

    os.makedirs(output_dir, exist_ok=True)
    process_all_pdfs(input_dir, output_dir)
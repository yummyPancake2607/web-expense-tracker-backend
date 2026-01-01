import re
from google.cloud import vision
import os
from datetime import datetime

# Set credentials explicitly if available, otherwise relies on GOOGLE_APPLICATION_CREDENTIALS
CREDENTIALS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "service_account.json")
if os.path.exists(CREDENTIALS_PATH):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = CREDENTIALS_PATH

def extract_receipt_data(image_content: bytes) -> dict:
    """
    Analyzes an image using Google Cloud Vision API and extracts:
    - Total Amount
    - Date
    - Merchant (heuristic)
    """
    client = vision.ImageAnnotatorClient()
    image = vision.Image(content=image_content)
    
    # Perform text detection
    response = client.text_detection(image=image)
    texts = response.text_annotations
    
    if not texts:
        return {"error": "No text detected"}

    full_text = texts[0].description
    lines = full_text.split('\n')
    
    data = {
        "merchant": "Unknown",
        "date": datetime.today().strftime('%Y-%m-%d'),
        "amount": 0.0,
        "raw_text": full_text
    }

    # 1. Extract Merchant (Heuristic: First significant line)
    # Often the merchant name is at the very top.
    for line in lines:
        cleaned = line.strip()
        if len(cleaned) > 2 and not cleaned.lower().startswith("tax"):
             data["merchant"] = cleaned
             break
            
    # 2. Extract Date
    # Try multiple patterns: DD/MM/YYYY, MM/DD/YYYY, YYYY-MM-DD
    date_patterns = [
        r'(\d{1,2}[/-]\d{1,2}[/-]\d{4})',  # 13/12/2025 or 12-13-2025
        r'(\d{4}[/-]\d{1,2}[/-]\d{1,2})',  # 2025-12-13
        r'(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4})' # 13 Dec 2025
    ]
    
    for pat in date_patterns:
        match = re.search(pat, full_text, re.IGNORECASE)
        if match:
            try:
                # We won't try complex parsing without dateutil, just return the string
                # The frontend can handle it or we store it as string for now
                data["date"] = match.group(0)
                break
            except:
                pass

    # 3. Extract Total Amount
    # Strategy: Look for lines containing "Total", "Amount", "Due", "Payable"
    # and extract the last number in that line.
    # Fallback: Max number in the whole text.
    
    total_keywords = ["total", "grand total", "net amount", "payable", "amount due", "balance"]
    specific_amount = None
    
    # Reverse iterate (Totals are usually at bottom)
    for line in reversed(lines):
        lower_line = line.lower()
        if any(k in lower_line for k in total_keywords):
            # Extract numbers from this line
            line_amounts = re.findall(r'\d{1,3}(?:,\d{3})*(?:\.\d{2})?', line)
            if line_amounts:
                # Filter out empty strings
                valid_line_amounts = []
                for a in line_amounts:
                    try:
                        val = float(a.replace(',', ''))
                        if val > 0: valid_line_amounts.append(val)
                    except: pass
                
                if valid_line_amounts:
                    # Usually the last number on a "Total" line is the value
                    specific_amount = valid_line_amounts[-1]
                    break
    
    if specific_amount:
         data["amount"] = specific_amount
    else:
        # Fallback to max number found
        amount_pattern = r'\d{1,3}(?:,\d{3})*\.\d{2}'
        all_amounts = re.findall(amount_pattern, full_text)
        if all_amounts:
            try:
                valid_amounts = [float(a.replace(',', '')) for a in all_amounts]
                if valid_amounts:
                    data["amount"] = max(valid_amounts)
            except ValueError:
                pass

    return data

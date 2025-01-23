import json
import time
import random
import sys
import os
import requests
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8')
load_dotenv()
API_ENDPOINT = os.getenv("API_ENDPOINT")
API_KEY = os.getenv("API_KEY")
MODEL = os.getenv("MODEL")

def process_ocr_entry_with_api(entry):
    simplified_entry = {
        "filename": entry["filename"],
        "text": entry["data"]["text"]
    }
        
    prompt = f"""
        Input JSON:
        {json.dumps(simplified_entry, ensure_ascii=False)}
        Task: Extract and format OCR data into a Return strictly formatted JSON output only, no explanations. Follow these rules exactly:

        1. IDENTIFY TEST TYPE:
        - If contains "Test ID" or "รหัสการทดสอบ" → Ookla format
        - If no Test ID → Open Signal format

        2. STRICT OUTPUT STRUCTURE:
        FOR OOKLA:
        {{
            "ookla": {{
                "image_url": "<EXACT_URL_WITH_EXTENSION>",
                "test_id": "<10_DIGIT_ID>",
                "download": <FLOAT_NUMBER>,
                "upload": <FLOAT_NUMBER>,
                "latency": <INTEGER>,
                "latency_download": <INTEGER>,
                "latency_upload": <INTEGER>
            }}
        }}

        FOR OPEN SIGNAL:
        {{
            "open signal": {{
                "image_url": "<EXACT_URL_WITH_EXTENSION>",
                "download": <FLOAT_NUMBER>,
                "upload": <FLOAT_NUMBER>,
                "latency": <INTEGER>
            }}
        }}

        3. CRITICAL RULES:
        - image_url: Must end with .png, .jpg, or .jpeg
        - test_id: Must be exactly 10 digits (Ookla only)
        - All speeds: Must be float numbers
        - All latency: Must be integers
        - Use null for any missing values
        - No additional fields allowed
        - No comments or explanations in output

        4. LATENCY EXTRACTION:
        ENGLISH:
        - After "RESPONSIVENESS":
        * "Idle" → latency
        * "Download" → latency_download
        * "Upload" → latency_upload

        THAI:
        - After "การตอบสนอง":
        * "Idle" → latency
        * "ดาวน์โหลด" → latency_download
        * "อัพโหลด" → latency_upload
        * Ignore values next to "ต่ำ" or "สูง"

        Return strictly formatted JSON output only, no explanations.
        """

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.0
    }

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.post(
                f"{API_ENDPOINT}/chat/completions",
                headers=headers,
                json=payload,
                verify="ca.crt",
            )
            response.raise_for_status()
        
            api_response = response.json()
            if not api_response.get('choices'):
                raise ValueError("No choices in API response")
                
            content = api_response['choices'][0]['message']['content'].strip()
            
            if content.startswith('```json'):
                content = content[7:]
            if content.endswith('```'):
                content = content[:-3]
            content = content.strip()
            
            try:
                parsed_json = json.loads(content)
                if not isinstance(parsed_json, dict):
                    raise ValueError("Response is not a valid JSON object")
                
                if not ('ookla' in parsed_json or 'open signal' in parsed_json):
                    raise ValueError("Response missing required keys")
                
                return parsed_json
                
            except json.JSONDecodeError as je:
                print(f"JSON parsing error: {je}")
                print(f"Raw content: {content}")
                if attempt < max_retries - 1:
                    continue
                return None
                
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {str(e)}")
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt + random.uniform(0, 1)
                print(f"Retrying in {wait_time:.2f} seconds...")
                time.sleep(wait_time)
            else:
                print("Max retries reached. Returning None.")
                return None

    return None

def process_and_write_sequentially(input_data, output_file, start_index=0):
    total_entries = len(input_data)
    
    if start_index == 0:
        mode = 'w'
        initial_content = '[\n'
    else:
        if not os.path.exists(output_file):
            mode = 'w'
            initial_content = '[\n' + 'null,\n' * start_index
        else:
            with open(output_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if content.endswith(']'):
                    content = content[:-1].rstrip(',\n')
            mode = 'w'
            initial_content = content + ',\n'

    with open(output_file, mode, encoding='utf-8') as f:
        f.write(initial_content)

    for i in range(start_index, total_entries):
        try:
            print(f"Processing entry {i + 1}/{total_entries}...")
            result = process_ocr_entry_with_api(input_data[i])
            
            with open(output_file, 'a', encoding='utf-8') as f:
                if result is None:
                    f.write('null')
                else:
                    json_str = json.dumps(result, ensure_ascii=False, indent=4)
                    f.write(json_str)
                
                if i < total_entries - 1:
                    f.write(',\n')
                else:
                    f.write('\n]')

            wait_time = random.uniform(1.5, 3.0)
            time.sleep(wait_time)

        except Exception as e:
            print(f"Error processing entry {i + 1}: {e}")
            with open(output_file, 'a', encoding='utf-8') as f:
                f.write('null')
                if i < total_entries - 1:
                    f.write(',\n')
                else:
                    f.write('\n]')

if __name__ == "__main__":
    input_file = "23-31-dec-raw-data.json"
    output_file = "formatted_ocr.json"
    start_index = 0

    print(f"Using model: {MODEL}")
    
    try:
        with open(input_file, "r", encoding="utf-8") as infile:
            raw_data = json.load(infile)
        
        process_and_write_sequentially(raw_data, output_file, start_index)
        
    except Exception as e:
        print(f"Critical error: {e}")
        sys.exit(1)

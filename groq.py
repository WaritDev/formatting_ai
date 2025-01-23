import json
import time
import random
from groq import Groq
import sys
import os

sys.stdout.reconfigure(encoding='utf-8')

client = Groq(api_key="")

def process_ocr_entry_with_groq(entry):
    prompt = f"""
        Task: Extract and format OCR data into a strict JSON structure. Follow these rules exactly:

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

        Input JSON:
        {json.dumps(entry, ensure_ascii=False)}

        Return strictly formatted JSON output only, no explanations.
        """

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="gemma2-9b-it", #llama-3.3-70b-versatile #gemma2-9b-it
                temperature=0.0
            )
            response_text = response.choices[0].message.content.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
                
            response_text = response_text.strip()
            
            try:
                json_response = json.loads(response_text)
                return json_response
            except json.JSONDecodeError as e:
                print(f"JSON Decode Error: {e}, Response Text: {response_text}")
                return None
        except Exception as e:
            print(f"Error processing entry: {e}")
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt + random.uniform(0, 1)
                print(f"Retrying in {wait_time:.2f} seconds...")
                time.sleep(wait_time)
            else:
                print("Max retries reached. Skipping this entry.")
                return None

def process_and_write_sequentially(input_data, output_file, start_index=0):
    total_entries = len(input_data)
    file_exists = os.path.exists(output_file)

    if start_index == 0:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('[\n')
    elif file_exists:
        with open(output_file, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if content.endswith(']'):
                content = content[:-1].rstrip(',\n')
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(content)
            f.write(',\n')
    else:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('[\n')
            for i in range(start_index):
                f.write('null')
                f.write(',\n')
                
    for i in range(start_index, total_entries):
        try:
            print(f"Processing entry {i + 1}/{total_entries}...")
            result = process_ocr_entry_with_groq(input_data[i])
            if result is None:
                print(f"Error: API returned 'Not Found' or invalid response at entry {i + 1}")
                with open(output_file, 'a', encoding='utf-8') as f:
                    f.write('\n]')
                sys.exit(1) 
            
            with open(output_file, 'a', encoding='utf-8') as f:
                json_str = json.dumps(result, ensure_ascii=False, indent=4)
                f.write(json_str)
                if i < total_entries - 1:
                    f.write(',\n')
                else:
                    f.write('\n')

            wait_time = random.uniform(1.5, 3.0)
            time.sleep(wait_time)

        except Exception as e:
            print(f"Critical error at entry {i + 1}: {e}")
            with open(output_file, 'a', encoding='utf-8') as f:
                f.write('\n]')
            sys.exit(1)

    with open(output_file, 'a', encoding='utf-8') as f:
        f.write(']')

    total_entries = len(input_data)
    file_exists = os.path.exists(output_file)
    entries_processed = 0

    if file_exists and start_index == 0:
        os.remove(output_file)
        file_exists = False

    if not file_exists:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('[\n')
    else:
        with open(output_file, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if content.endswith(']'):
                content = content[:-1].rstrip(',\n')
            existing_entries = content.strip('[').split('\n')
            entries_processed = len(existing_entries)
            start_index = entries_processed
        with open(output_file, 'a', encoding='utf-8') as f:
            if entries_processed > 0:
                f.write(',\n')

    for i in range(start_index, total_entries):
        try:
            print(f"Processing entry {i + 1}/{total_entries}...")
            result = process_ocr_entry_with_groq(input_data[i])
            if result is None:
                raise ValueError("API returned 'Not Found' or invalid response")
            
            with open(output_file, 'a', encoding='utf-8') as f:
                json_str = json.dumps(result, ensure_ascii=False, indent=4)
                f.write(json_str)
                if i < total_entries - 1:
                    f.write(',\n')
                else:
                    f.write('\n')
        except ValueError as ve:
            print(f"Skipping entry {i + 1}: {ve}")
            with open(output_file, 'a', encoding='utf-8') as f:
                f.write('null')
                if i < total_entries - 1:
                    f.write(',\n')
                else:
                    f.write('\n')
        except Exception as e:
            print(f"Error processing entry {i + 1}: {e}")
            with open(output_file, 'a', encoding='utf-8') as f:
                f.write('null')
                if i < total_entries - 1:
                    f.write(',\n')
                else:
                    f.write('\n')
        finally:
            wait_time = random.uniform(1.5, 3.0)
            time.sleep(wait_time)

    with open(output_file, 'a', encoding='utf-8') as f:
        f.write(']')

if __name__ == "__main__":
    input_file = "23-31-dec-raw-data.json"
    output_file = "formatted_ocr.json"
    start_index = 0

    try:
        with open(input_file, "r", encoding="utf-8") as infile:
            raw_data = json.load(infile)

        process_and_write_sequentially(raw_data, output_file, start_index)

        print(f"Processing completed. Results saved to {output_file}")
    except Exception as e:
        print(f"An error occurred: {e}")

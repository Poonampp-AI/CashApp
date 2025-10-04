import requests
import os
import requests
import json

# pull the propmt from prompt.txt file
current_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(current_dir,"prompt_test.txt")

with open(file_path, 'r') as file:
    actual_prompt = file.read()


def asp_data_extraction(extracted_text):
    prompt = f"{actual_prompt} \n Text:{extracted_text}"

    # Configuration
    headers = {
        "Content-Type": "application/json",
        "api-key": GPT4V_KEY,
    }

    payload = {
        "model": "gpt-4",
        "messages": [
            {
                "role": "system",
                "content": [
                    {
                    "type": "text",
                    "text": "You are an AI assistant that helps people find information."
                    }],
            },
            {
          "role": "user",
          "content": [
            {
              "type": "text",
              "text": extracted_text},
            {
              "type": "text",
              "text":prompt
            } 
          ]
        }

        ],
        "temperature": 0.0,
        "top_p": 0.95,
        "max_tokens": 4000
    }


    
    # Send request
    try:
        response = requests.post(GPT4V_ENDPOINT, headers=headers, json=payload)
        response.raise_for_status()  # Will raise an HTTPError if the HTTP request returned an unsuccessful status code
    except requests.RequestException as e:
        print((f"Failed to make the request. Error: {e}"))
        return {"error": str(e)}
        # return None
        # raise SystemExit(f"Failed to make the request. Error: {e}")
    
    # # Handle the response
    # response_content = response.json()
    
    # # Extract the "content" key
    # content = response_content['choices'][0]['message']['content']
    # # Strip out the code block markers and parse the JSON

    # Handle the response
    response_content = response.json()
    print("Response Content:", response_content)  # Print the response content for debugging

    if 'choices' not in response_content:
        return {
            "error": "Unexpected response format. 'choices' key not found.",
            "response_content": response_content
        }

    # Extract the "content" key
    try:
        content = response_content['choices'][0]['message']['content']
    except KeyError as e:
        return {
            "error": f"KeyError: {e}",
            "response_content": response_content
        }

    try:
        # Remove the surrounding triple backticks and optional "json" marker
        if content.startswith("```json"):
            content = content[7:].strip()
        elif content.startswith("```"):
            content = content[3:].strip()

        if content.endswith("```"):
            content = content[:-3].strip()

        # Load and return the JSON object
        extracted_info = json.loads(content)
        # result = json.dumps(extracted_info, indent=4)
        return extracted_info
    except json.JSONDecodeError as e:
        return {
            "error": "Failed to decode JSON from the response content.",
            "details": str(e),
            "raw_content": content
        }
    

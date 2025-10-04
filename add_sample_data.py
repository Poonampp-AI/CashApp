import requests
import json
import re

from data_extraction import asp_data_extraction

def authenticate(user_key, client_id, orchestrator_url):
    url = f"{orchestrator_url}/oauth/****"
    headers = {"Content-Type": "application/json"}

    payload = {
        "grant_type": "refresh_token",
        "client_id": client_id,
        "refresh_token": user_key
    }

    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        raise ValueError(f"Failed to authenticate. Status code: {response.status_code}, Response: {response.text}")

def filter_invoice_data(extracted_data):
    # Define the valid prefixes
    valid_prefixes = ('80', '16', '14')
    
    # Access the mappings
    mappings = extracted_data['extracted_data'].get('Invoice Number and Invoice Date Mappings', {})
    
    # Filter the mappings
    filtered_mappings = {
        number: date for number, date in mappings.items()
        if len(number) == 10 and number.startswith(valid_prefixes)
    }
    
    # Check if filtered mappings is empty, if so, set it to {'': ''}
    if not filtered_mappings:
        filtered_mappings = {'': ''}
    
    # Update the sample data with the filtered mappings
    extracted_data['extracted_data']['Invoice Number and Invoice Date Mappings'] = filtered_mappings
    
    return extracted_data

def is_valid_extracted_result(extracted_result):
    required_fields = [
        "Type of Payment",
        "Credit Amount",
        "Effective Date",
        "Deposit Date",
        "Instructions type",
        "Invoice Number and Invoice Date Mappings",
    ]
    
    # Check if extracted_result is a dictionary
    if not isinstance(extracted_result, dict):
        return False

    # Check if 'extracted_data' is in extracted_result and is a dictionary
    if 'extracted_data' not in extracted_result or not isinstance(extracted_result['extracted_data'], dict):
        return False

    # # Extract the 'extracted_data' dictionary
    # extracted_data = extracted_result['extracted_data']
    
    # # Check if all required fields are present in 'extracted_data'
    # for field in required_fields:
    #     if field not in extracted_data:
    #         return False
    
    return True


def send_to_sap_queue(access_token, reference_number, extracted_result, specific_content, organization_unit_id):
    url = f"{base_url}/odata/Queues/UiPathODataSvc.****"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-UIPATH-OrganizationUnitId": str(organization_unit_id)
    }
    if is_valid_extracted_result(extracted_result):
        # Prepare payload for pass case
        payload = {
            "itemData": {
                "Name": "SAP_InputQueue",
                "Priority": "Normal",
                "Reference": reference_number,
                "SpecificContent": {
                    "ExtractedData": str(extracted_result.get("extracted_data", None)),
                    "EDI Report File Path": str(specific_content.get("EDI ReportFilePath", None)),
                    "Monthly EDI Report File Path": str(specific_content.get("Monthly EDI ReportFilePath", None)),
                    "Page No": str(specific_content.get("PageNo", None)),
                    "File Name": str(specific_content.get("File Name", None)),
                    "GEN-AI Status": "Passed",
                }
            }
        }
    else:
        # Prepare payload for failed case
        payload = {
            "itemData": {
                "Name": "****",
                "Priority": "Normal",
                "Reference": reference_number,
                "SpecificContent": {
                    "ExtractedData": None,
                    "EDI Report File Path": str(specific_content.get("EDI ReportFilePath", None)),
                    "Monthly EDI Report File Path": str(specific_content.get("Monthly EDI ReportFilePath", None)),
                    "Page No": str(specific_content.get("PageNo", None)),
                    "File Name": str(specific_content.get("File Name", None)),
                    "GEN-AI Status": "Failed",
                }
            }
        }

    json_payload = json.dumps(payload)

    response = requests.post(url, data=json_payload, headers=headers)
    response.raise_for_status()

    if response.status_code == 201:
        print(f"Data successfully sent to SAP_InputQueue for reference: {reference_number}")
        return True
    else:
        print(f"Failed to send data to SAP_InputQueue for reference: {reference_number}. Status code: {response.status_code}, Response: {response.text}")
        return False

def get_queue_items(access_token, base_url, queue_definition_id, organization_unit_id):
    
    url = f"{base_url}/orchestrator_/odata/*****"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-UIPATH-OrganizationUnitId": str(organization_unit_id)
    }

    params = {
        "$filter": f"(QueueDefinitionId eq {queue_definition_id}) and (Status eq 'New')"
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()

        if response.status_code == 200:
            queue_items = response.json()["value"]
            for item in queue_items:
                if item["SpecificContent"]["CurrentStatus"] == 'Start':
                    reference_number = item["Reference"]
                    specific_content = item["SpecificContent"]
                    print("item Reference ---",item["Reference"])
                    extracted_result_from_input_queue = json.dumps(specific_content)
                    extracted_result = asp_data_extraction(extracted_result_from_input_queue)
                    if is_valid_extracted_result(extracted_result):
                        extracted_result = filter_invoice_data(extracted_result)
                    else:
                        print("data is not extracted correctlly")
                    print("extracted_result---",extracted_result)
                    success = send_to_sap_queue(access_token, reference_number, extracted_result, specific_content, organization_unit_id)

                    if success:
                        item_id = item["Id"]
                        item["SpecificContent"]["CurrentStatus"]='End'
                        print("item_id############",item_id)
                        if update_queue_item_status(access_token, base_url, item_id, organization_unit_id,item["SpecificContent"] ):
                            print(f"Successfully updated status to 'End' for item ID: {item_id}")
                        else:
                            print(f"Failed to update status for item ID: {item_id}")
    except requests.exceptions.RequestException as e:
        print(f"Error fetching queue items: {e}")
        print(f"Response content: {response.text if 'response' in locals() else 'No response'}")
    
def get_queue_definition_id(access_token, base_url, queue_name, organization_unit_id):
    url = f"{base_url}/orchestrator_/odata/*****"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-UIPATH-OrganizationUnitId": str(organization_unit_id)
    }

    params = {
        "$filter": f"Name eq '{queue_name}'"
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()

        if response.status_code == 200:
            queue_definitions = response.json()["value"]
            if queue_definitions:
                return queue_definitions[0]["Id"]
            else:
                print(f"Queue '{queue_name}' not found.")
                return None

        else:
            print(f"Failed to retrieve queue definitions. Status code: {response.status_code}, Response: {response.text}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"Error fetching queue definitions: {e}")
        return None
  
def update_queue_item_status(access_token, base_url, item_id, organization_unit_id, new_data):
    url = f"{base_url}/odata/*****({item_id})"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-UIPATH-OrganizationUnitId": str(organization_unit_id)
    }
    payload = {
        "Name": "GenAI_Queue",  # Name of the queue, adjust as per your needs
        "Priority": "High",  # Priority of the queue item, adjust as per your needs
        "SpecificContent": new_data  # New data to be updated in SpecificContent
    }
    json_payload = json.dumps(payload)

    try:
        response = requests.put(url, data=json_payload, headers=headers)
        response.raise_for_status()

        if response.status_code == 200:
            print(f"Queue item updated successfully for item ID: {item_id}")
            return True
        else:
            print(f"Failed to update queue item. Status code: {response.status_code}, Response: {response.text}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"Error updating queue item: {e}")
        return False
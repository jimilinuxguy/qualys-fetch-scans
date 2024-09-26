import requests
import json
import boto3
from datetime import datetime
import os
from requests.auth import HTTPBasicAuth
from concurrent.futures import ThreadPoolExecutor, as_completed
from tenacity import retry, stop_after_attempt, wait_exponential
import logging

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Getting date
dateToday = datetime.today().strftime('%Y-%m-%d')

# Getting credentials from environment variables for security
qualys_username = os.getenv('QUALYS_USERNAME')
qualys_password = os.getenv('QUALYS_PASSWORD')
s3_bucket_name = os.getenv('S3_BUCKET_NAME')

# Verify environment variables are set
missing_env_vars = [var for var in ['QUALYS_USERNAME', 'QUALYS_PASSWORD', 'S3_BUCKET_NAME'] if not os.getenv(var)]
if missing_env_vars:
    logging.error(f"Missing environment variables: {', '.join(missing_env_vars)}")
    raise EnvironmentError(f"Missing one or more environment variables: {', '.join(missing_env_vars)}")

# Qualys API URL
url = "https://qualysapi.qg3.apps.qualys.com/qps/rest/3.0/search/was/wasscan"

# API payload to filter scans
payload = json.dumps({
    "ServiceRequest": {
        "preferences": {
            "limitResults": 1000
        },
        "filters": {
            "Criteria": [
                {
                    "field": "launchedDate",
                    "operator": "EQUALS",
                    "value": dateToday
                },
                {
                    "field": "status",
                    "operator": "EQUALS",
                    "value": "FINISHED"
                }
            ]
        }
    }
})

# Headers for API request
headers = {
    'Content-Type': 'application/json',
    'X-Requested-With': 'QualysPostman',
    'Accept': 'application/json'
}

# Retry decorator for network requests
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def download_and_upload_scan(scan_id):
    fileName = scan_id + ".json"
    scan_download_url = f"https://qualysapi.qg3.apps.qualys.com/qps/rest/3.0/download/was/wasscan/{scan_id}"
    
    try:
        # Fetching scan details
        logging.info(f"Downloading scan ID: {scan_id}")
        scan_response = requests.get(scan_download_url, headers=headers, auth=HTTPBasicAuth(qualys_username, qualys_password), timeout=20)
        scan_response.raise_for_status()

        # Upload to S3
        logging.info(f"Uploading {fileName} to S3 bucket: {s3_bucket_name}")
        s3.put_object(Body=json.dumps(scan_response.json()), Bucket=s3_bucket_name, Key=fileName)
        logging.info(f"Successfully uploaded {fileName} to S3.")
        return f"Uploaded {fileName} to S3."
    
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to download scan ID: {scan_id}, Error: {e}")
        return f"Failed to download scan ID: {scan_id}, Error: {e}"
    
    except boto3.exceptions.S3UploadFailedError as e:
        logging.error(f"Failed to upload {fileName} to S3: {e}")
        return f"Failed to upload {fileName} to S3, Error: {e}"

# Initializing S3 client
s3 = boto3.client('s3')

try:
    # Sending POST request to Qualys API to fetch scan data
    logging.info("Fetching scan data from Qualys API")
    response = requests.post(url, headers=headers, data=payload, auth=HTTPBasicAuth(qualys_username, qualys_password), timeout=20)
    response.raise_for_status()
    
    data = response.json()
    scan_ids = [str(entry['WasScan']['id']) for entry in data.get('ServiceResponse', {}).get('data', [])]

    if not scan_ids:
        logging.info("No finished scans found for today.")
    else:
        # Using ThreadPoolExecutor to parallelize the download and upload
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_scan = {executor.submit(download_and_upload_scan, scan_id): scan_id for scan_id in scan_ids}
            
            for future in as_completed(future_to_scan):
                scan_id = future_to_scan[future]
                try:
                    result = future.result()
                    logging.info(result)
                except Exception as e:
                    logging.error(f"Scan ID {scan_id} generated an exception: {e}")

except requests.exceptions.RequestException as e:
    logging.error(f"Failed to fetch scans: {e}")

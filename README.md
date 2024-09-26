# Qualys WAS Scan Downloader and S3 Uploader

This script fetches the results of finished web application security (WAS) scans from Qualys, downloads them, and uploads them to an AWS S3 bucket. The script utilizes environment variables for credentials and can be run in parallel for improved performance.

## Prerequisites

Before running the script, ensure you have the following:

- Python 3.7 or higher
- `boto3` for AWS SDK integration
- `requests` for API communication
- `tenacity` for retry mechanisms
- AWS S3 bucket for storing scan files
- A Qualys API account with permissions to access WAS scans

### Python Dependencies

Install the required Python packages using the following command:

```bash
pip install requests boto3 tenacity
```

## Environment Variables
To maintain security, the script uses environment variables to store sensitive credentials and settings. Before running the script, make sure the following environment variables are set:

Variable Name	Description
- QUALYS_USERNAME	Your Qualys API username
- QUALYS_PASSWORD	Your Qualys API password
- S3_BUCKET_NAME	The name of your AWS S3 bucket
- MAX_WORKERS	(Optional) Number of concurrent threads (default: 5)

## Script Workflow
- Fetch Finished Scans: The script sends a request to the Qualys API to fetch WAS scans that were finished on the current date.
- Download Scan Results: For each scan, the script downloads the scan data in JSON format.
- Upload to S3: The scan result is uploaded to a specified AWS S3 bucket.
- Concurrency: The script uses Python’s ThreadPoolExecutor to download and upload scans concurrently. The number of workers can be configured using the MAX_WORKERS environment variable.

Make sure the necessary environment variables are set beforehand.

## Logging
The script uses Python's built-in logging module to log the process, including any errors or exceptions encountered. Logs will be output to the console in real-time.

## Error Handling
The script includes automatic retries for failed network requests using the tenacity library. It will retry the download or upload of a scan file up to 3 times with exponential backoff.

## AWS IAM Permissions
Ensure your AWS IAM role or user has the following permissions for the S3 bucket:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:PutObject"
            ],
            "Resource": "arn:aws:s3:::your_s3_bucket/*"
        }
    ]
}
```

import os
import boto3
from botocore.exceptions import NoCredentialsError
from dotenv import load_dotenv

# Load environment variables from .env.local in the parent directory
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env.local')
load_dotenv(dotenv_path=dotenv_path)

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
AWS_S3_BUCKET = os.getenv("AWS_S3_BUCKET")

if not all([AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_S3_BUCKET]):
    raise Exception("AWS credentials and/or S3 bucket name not found in environment variables")

s3_client = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION
)

def download_from_s3(s3_key: str, local_path: str):
    """
    Download a file from S3
    """
    try:
        print(f"Downloading {s3_key} from S3 to {local_path}")
        s3_client.download_file(AWS_S3_BUCKET, s3_key, local_path)
        print("Download complete")
        return local_path
    except NoCredentialsError:
        print("Credentials not available")
        raise
    except Exception as e:
        print(f"Error downloading from S3: {e}")
        raise

def upload_file_to_s3(local_path: str, s3_key: str) -> str:
    """
    Upload a file to S3 and return its public URL
    """
    try:
        print(f"Uploading {local_path} to S3 with key {s3_key}")
        s3_client.upload_file(local_path, AWS_S3_BUCKET, s3_key)
        # Construct the URL
        url = f"https://{AWS_S3_BUCKET}.s3.{AWS_REGION}.amazonaws.com/{s3_key}"
        print(f"Upload complete: {url}")
        return url
    except NoCredentialsError:
        print("Credentials not available")
        raise
    except Exception as e:
        print(f"Error uploading to S3: {e}")
        raise

def generate_final_video_key(username: str, project_name: str) -> str:
    return f"users/{username}/{project_name}/final-video.mp4"

def get_s3_url(s3_key: str) -> str:
    """
    Get the public URL for an S3 object
    """
    return f"https://{AWS_S3_BUCKET}.s3.{AWS_REGION}.amazonaws.com/{s3_key}"

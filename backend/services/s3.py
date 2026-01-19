import boto3
from botocore.exceptions import ClientError
from typing import Optional
from config import get_settings

settings = get_settings()


def get_s3_client():
    """Get S3 client with configured credentials."""
    if not settings.aws_access_key_id or not settings.aws_secret_access_key:
        return None

    return boto3.client(
        "s3",
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        region_name=settings.aws_region,
    )


async def upload_file(
    file_content: bytes,
    s3_key: str,
    content_type: str = "video/mp4",
) -> Optional[str]:
    """
    Upload a file to S3.
    Returns the S3 URL if successful, None otherwise.
    """
    client = get_s3_client()
    if not client:
        return None

    try:
        client.put_object(
            Bucket=settings.aws_s3_bucket,
            Key=s3_key,
            Body=file_content,
            ContentType=content_type,
        )
        return f"https://{settings.aws_s3_bucket}.s3.{settings.aws_region}.amazonaws.com/{s3_key}"
    except ClientError as e:
        print(f"Error uploading to S3: {e}")
        return None


async def delete_file(s3_key: str) -> bool:
    """Delete a file from S3."""
    client = get_s3_client()
    if not client:
        return False

    try:
        client.delete_object(Bucket=settings.aws_s3_bucket, Key=s3_key)
        return True
    except ClientError as e:
        print(f"Error deleting from S3: {e}")
        return False


async def generate_presigned_url(
    s3_key: str,
    expiration: int = 3600,
    for_upload: bool = False,
) -> Optional[str]:
    """
    Generate a presigned URL for S3 object.
    - for_upload=False: generates download URL
    - for_upload=True: generates upload URL
    """
    client = get_s3_client()
    if not client:
        return None

    try:
        if for_upload:
            url = client.generate_presigned_url(
                "put_object",
                Params={"Bucket": settings.aws_s3_bucket, "Key": s3_key},
                ExpiresIn=expiration,
            )
        else:
            url = client.generate_presigned_url(
                "get_object",
                Params={"Bucket": settings.aws_s3_bucket, "Key": s3_key},
                ExpiresIn=expiration,
            )
        return url
    except ClientError as e:
        print(f"Error generating presigned URL: {e}")
        return None

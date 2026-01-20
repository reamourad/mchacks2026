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


async def generate_presigned_upload_url(
    s3_key: str,
    content_type: str = "video/mp4",
    expiration: int = 3600,
) -> Optional[str]:
    """Generate a presigned URL specifically for uploading."""
    client = get_s3_client()
    if not client:
        return None

    try:
        url = client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": settings.aws_s3_bucket,
                "Key": s3_key,
                "ContentType": content_type,
            },
            ExpiresIn=expiration,
        )
        return url
    except ClientError as e:
        print(f"Error generating presigned upload URL: {e}")
        return None


def get_s3_url(s3_key: str) -> str:
    """Get the public URL for an S3 object."""
    return f"https://{settings.aws_s3_bucket}.s3.{settings.aws_region}.amazonaws.com/{s3_key}"


async def download_file(s3_key: str, local_path: str) -> bool:
    """Download a file from S3 to local path."""
    client = get_s3_client()
    if not client:
        return False

    try:
        client.download_file(settings.aws_s3_bucket, s3_key, local_path)
        return True
    except ClientError as e:
        print(f"Error downloading from S3: {e}")
        return False


async def upload_local_file(local_path: str, s3_key: str, content_type: str = "video/mp4") -> bool:
    """Upload a local file to S3."""
    client = get_s3_client()
    if not client:
        return False

    try:
        client.upload_file(
            local_path,
            settings.aws_s3_bucket,
            s3_key,
            ExtraArgs={"ContentType": content_type},
        )
        return True
    except ClientError as e:
        print(f"Error uploading to S3: {e}")
        return False


class S3Service:
    """S3 service wrapper for video export pipeline."""

    async def download_file(self, s3_key: str, local_path: str) -> bool:
        return await download_file(s3_key, local_path)

    async def upload_file(self, local_path: str, s3_key: str, content_type: str = "video/mp4") -> bool:
        return await upload_local_file(local_path, s3_key, content_type)

    async def get_download_url(self, s3_key: str, expiration: int = 3600) -> Optional[str]:
        return await generate_presigned_url(s3_key, expiration, for_upload=False)

    async def delete_file(self, s3_key: str) -> bool:
        return await delete_file(s3_key)


s3_service = S3Service()

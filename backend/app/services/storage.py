"""
MinIO/S3 storage service for handling file uploads and downloads.
Supports presigned URLs, multipart uploads, and bucket management.
"""

import os
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from minio import Minio
from minio.error import S3Error

from app.core.config import get_settings

settings = get_settings()


class StorageService:
    """MinIO/S3 storage service for file operations."""
    
    # Bucket names
    BUCKETS = {
        "audio_raw": "audio-raw",
        "audio_mp3": "audio-mp3", 
        "documents": "docs",
        "exports": "exports"
    }
    
    def __init__(self):
        """Initialize MinIO client and boto3 client."""
        self.minio_client = Minio(
            endpoint=settings.MINIO_ENDPOINT.replace("http://", "").replace("https://", ""),
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE
        )
        
        # Boto3 client for presigned URLs (more compatible)
        self.s3_client = boto3.client(
            's3',
            endpoint_url=settings.MINIO_ENDPOINT,
            aws_access_key_id=settings.MINIO_ACCESS_KEY,
            aws_secret_access_key=settings.MINIO_SECRET_KEY,
            config=Config(signature_version='s3v4'),
            region_name='us-east-1'  # MinIO default
        )
    
    async def initialize_buckets(self) -> None:
        """Create all required buckets if they don't exist."""
        for bucket_key, bucket_name in self.BUCKETS.items():
            try:
                if not self.minio_client.bucket_exists(bucket_name):
                    self.minio_client.make_bucket(bucket_name)
                    print(f"✅ Created bucket: {bucket_name}")
                else:
                    print(f"✅ Bucket exists: {bucket_name}")
            except S3Error as e:
                print(f"❌ Error creating bucket {bucket_name}: {e}")
                raise
    
    def generate_object_key(self, 
                          meeting_id: str, 
                          file_type: str, 
                          part_number: Optional[int] = None,
                          file_extension: str = "bin") -> str:
        """Generate a unique object key for storage."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        
        if part_number is not None:
            return f"{meeting_id}/{file_type}/{timestamp}_{unique_id}_part{part_number:04d}.{file_extension}"
        else:
            return f"{meeting_id}/{file_type}/{timestamp}_{unique_id}.{file_extension}"
    
    async def create_multipart_upload(self, 
                                    bucket_name: str, 
                                    object_key: str,
                                    content_type: str = "application/octet-stream") -> str:
        """Initialize a multipart upload and return upload ID."""
        try:
            response = self.s3_client.create_multipart_upload(
                Bucket=bucket_name,
                Key=object_key,
                ContentType=content_type,
                Metadata={
                    'created_at': datetime.utcnow().isoformat(),
                    'service': 'meeting-ai'
                }
            )
            return response['UploadId']
        except ClientError as e:
            print(f"❌ Error creating multipart upload: {e}")
            raise
    
    async def generate_presigned_upload_urls(self,
                                           bucket_name: str,
                                           object_key: str,
                                           upload_id: str,
                                           part_count: int,
                                           expiration: int = 3600) -> List[Dict[str, str]]:
        """Generate presigned URLs for multipart upload parts."""
        urls = []
        
        for part_number in range(1, part_count + 1):
            try:
                url = self.s3_client.generate_presigned_url(
                    'upload_part',
                    Params={
                        'Bucket': bucket_name,
                        'Key': object_key,
                        'PartNumber': part_number,
                        'UploadId': upload_id
                    },
                    ExpiresIn=expiration
                )
                
                urls.append({
                    'part_number': part_number,
                    'upload_url': url,
                    'expires_at': (datetime.utcnow() + timedelta(seconds=expiration)).isoformat()
                })
            except ClientError as e:
                print(f"❌ Error generating presigned URL for part {part_number}: {e}")
                raise
        
        return urls
    
    async def complete_multipart_upload(self,
                                      bucket_name: str,
                                      object_key: str,
                                      upload_id: str,
                                      parts: List[Dict[str, any]]) -> Dict[str, str]:
        """Complete a multipart upload."""
        try:
            # Format parts for completion
            multipart_upload = {
                'Parts': [
                    {
                        'ETag': part['etag'],
                        'PartNumber': part['part_number']
                    }
                    for part in parts
                ]
            }
            
            response = self.s3_client.complete_multipart_upload(
                Bucket=bucket_name,
                Key=object_key,
                UploadId=upload_id,
                MultipartUpload=multipart_upload
            )
            
            return {
                'bucket': bucket_name,
                'key': object_key,
                'etag': response['ETag'],
                'location': response['Location'],
                'completed_at': datetime.utcnow().isoformat()
            }
        except ClientError as e:
            print(f"❌ Error completing multipart upload: {e}")
            raise
    
    async def abort_multipart_upload(self,
                                   bucket_name: str,
                                   object_key: str,
                                   upload_id: str) -> None:
        """Abort a multipart upload and clean up parts."""
        try:
            self.s3_client.abort_multipart_upload(
                Bucket=bucket_name,
                Key=object_key,
                UploadId=upload_id
            )
        except ClientError as e:
            print(f"❌ Error aborting multipart upload: {e}")
            raise
    
    async def get_object_info(self, bucket_name: str, object_key: str) -> Dict[str, any]:
        """Get information about a stored object."""
        try:
            response = self.s3_client.head_object(Bucket=bucket_name, Key=object_key)
            return {
                'size': response['ContentLength'],
                'etag': response['ETag'],
                'last_modified': response['LastModified'].isoformat(),
                'content_type': response.get('ContentType', 'application/octet-stream'),
                'metadata': response.get('Metadata', {})
            }
        except ClientError as e:
            print(f"❌ Error getting object info: {e}")
            raise
    
    async def generate_download_url(self,
                                  bucket_name: str,
                                  object_key: str,
                                  expiration: int = 3600) -> str:
        """Generate a presigned URL for downloading a file."""
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket_name, 'Key': object_key},
                ExpiresIn=expiration
            )
            return url
        except ClientError as e:
            print(f"❌ Error generating download URL: {e}")
            raise
    
    async def delete_object(self, bucket_name: str, object_key: str) -> None:
        """Delete an object from storage."""
        try:
            self.s3_client.delete_object(Bucket=bucket_name, Key=object_key)
        except ClientError as e:
            print(f"❌ Error deleting object: {e}")
            raise


# Global storage service instance
storage_service = StorageService()

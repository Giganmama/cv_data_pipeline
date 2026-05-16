#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
S3 Handler Module
Upload/download files to MinIO/S3-compatible storage
"""

import os
import logging
from pathlib import Path
from typing import List, Optional
from minio import Minio
from minio.error import S3Error

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class S3Handler:
    """Handle S3/MinIO operations for CV data storage"""
    
    def __init__(
        self,
        endpoint: str = "localhost:9000",
        access_key: str = "minioadmin",
        secret_key: str = "minioadmin",
        secure: bool = False,
        bucket_name: str = "cv-data-bucket"
    ):
        self.client = Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure
        )
        self.bucket = bucket_name
        self._ensure_bucket_exists()
    
    def _ensure_bucket_exists(self):
        """Create bucket if not exists"""
        try:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
                logger.info(f"Created bucket: {self.bucket}")
        except S3Error as e:
            logger.error(f"Bucket error: {e}")
            raise
    
    def upload_file(self, local_path: str, object_name: Optional[str] = None, 
                    content_type: Optional[str] = None) -> str:
        """Upload single file to S3"""
        local_path = Path(local_path)
        object_name = object_name or local_path.name
        
        # Auto-detect content type for images/video
        if content_type is None:
            suffix = local_path.suffix.lower()
            content_types = {
                '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
                '.png': 'image/png', '.mp4': 'video/mp4',
                '.avi': 'video/x-msvideo', '.mov': 'video/quicktime'
            }
            content_type = content_types.get(suffix, 'application/octet-stream')
        
        try:
            self.client.fput_object(
                bucket_name=self.bucket,
                object_name=object_name,
                file_path=str(local_path),
                content_type=content_type
            )
            logger.info(f"Uploaded: {local_path} → s3://{self.bucket}/{object_name}")
            return f"s3://{self.bucket}/{object_name}"
        except S3Error as e:
            logger.error(f"Upload failed: {e}")
            raise
    
    def upload_directory(self, local_dir: str, prefix: str = "") -> List[str]:
        """Upload entire directory recursively"""
        uploaded = []
        local_dir = Path(local_dir)
        
        for file_path in local_dir.rglob("*"):
            if file_path.is_file():
                relative_path = file_path.relative_to(local_dir)
                object_name = f"{prefix}/{relative_path}" if prefix else str(relative_path)
                s3_path = self.upload_file(str(file_path), object_name)
                uploaded.append(s3_path)
        
        logger.info(f"Uploaded {len(uploaded)} files from {local_dir}")
        return uploaded
    
    def download_file(self, object_name: str, local_path: Optional[str] = None) -> str:
        """Download file from S3"""
        local_path = local_path or Path(object_name).name
        
        try:
            self.client.fget_object(
                bucket_name=self.bucket,
                object_name=object_name,
                file_path=local_path
            )
            logger.info(f"Downloaded: s3://{self.bucket}/{object_name} → {local_path}")
            return local_path
        except S3Error as e:
            logger.error(f"Download failed: {e}")
            raise
    
    def list_objects(self, prefix: str = "") -> List[str]:
        """List objects in bucket with optional prefix"""
        try:
            objects = self.client.list_objects(self.bucket, prefix=prefix, recursive=True)
            return [obj.object_name for obj in objects]
        except S3Error as e:
            logger.error(f"List failed: {e}")
            return []
    
    def delete_object(self, object_name: str) -> bool:
        """Delete object from S3"""
        try:
            self.client.remove_object(self.bucket, object_name)
            logger.info(f"Deleted: s3://{self.bucket}/{object_name}")
            return True
        except S3Error as e:
            logger.error(f"Delete failed: {e}")
            return False


# CLI for manual testing
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="S3/MinIO Handler")
    parser.add_argument("--action", required=True, choices=["upload", "download", "list", "delete"])
    parser.add_argument("--path", required=True, help="Local path or S3 object name")
    parser.add_argument("--bucket", default="cv-data-bucket", help="Bucket name")
    parser.add_argument("--prefix", default="", help="S3 prefix for list/upload")
    
    args = parser.parse_args()
    
    handler = S3Handler(bucket_name=args.bucket)
    
    if args.action == "upload":
        if Path(args.path).is_dir():
            handler.upload_directory(args.path, prefix=args.prefix)
        else:
            handler.upload_file(args.path)
    elif args.action == "download":
        handler.download_file(args.path)
    elif args.action == "list":
        for obj in handler.list_objects(args.prefix):
            print(obj)
    elif args.action == "delete":
        handler.delete_object(args.path)

"""
Cloud Storage Integration Module
Provides unified interface for Google Drive, OneDrive, AWS S3, and Dropbox
"""

from .cloud_storage import CloudStorageManager, CloudProvider

__all__ = ['CloudStorageManager', 'CloudProvider']

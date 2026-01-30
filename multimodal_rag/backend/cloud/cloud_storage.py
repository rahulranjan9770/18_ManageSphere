"""
Cloud Storage Integration Service
Unified interface for Google Drive, OneDrive, AWS S3, and Dropbox
"""

import os
import io
import json
import asyncio
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, BinaryIO
from enum import Enum
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import hashlib

from backend.utils.logger import logger


class CloudProvider(Enum):
    """Supported cloud storage providers"""
    GOOGLE_DRIVE = "google_drive"
    ONEDRIVE = "onedrive"
    AWS_S3 = "aws_s3"
    DROPBOX = "dropbox"


@dataclass
class CloudFile:
    """Represents a file in cloud storage"""
    id: str
    name: str
    path: str
    size: int
    mime_type: str
    modified_at: datetime
    provider: CloudProvider
    is_folder: bool = False
    parent_id: Optional[str] = None
    download_url: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "path": self.path,
            "size": self.size,
            "mime_type": self.mime_type,
            "modified_at": self.modified_at.isoformat() if self.modified_at else None,
            "provider": self.provider.value,
            "is_folder": self.is_folder,
            "parent_id": self.parent_id,
            "download_url": self.download_url,
            "metadata": self.metadata
        }


@dataclass
class CloudCredentials:
    """Cloud provider credentials"""
    provider: CloudProvider
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    expires_at: Optional[datetime] = None
    
    # AWS specific
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_region: Optional[str] = None
    s3_bucket: Optional[str] = None
    
    def is_expired(self) -> bool:
        if not self.expires_at:
            return False
        return datetime.utcnow() >= self.expires_at - timedelta(minutes=5)


class BaseCloudProvider(ABC):
    """Base class for cloud storage providers"""
    
    def __init__(self, credentials: CloudCredentials):
        self.credentials = credentials
        self._initialized = False
    
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the provider connection"""
        pass
    
    @abstractmethod
    async def list_files(self, folder_id: Optional[str] = None, 
                         file_types: Optional[List[str]] = None) -> List[CloudFile]:
        """List files in a folder"""
        pass
    
    @abstractmethod
    async def download_file(self, file_id: str) -> bytes:
        """Download a file by ID"""
        pass
    
    @abstractmethod
    async def get_file_info(self, file_id: str) -> Optional[CloudFile]:
        """Get file metadata"""
        pass
    
    @abstractmethod
    async def search_files(self, query: str, 
                           file_types: Optional[List[str]] = None) -> List[CloudFile]:
        """Search for files"""
        pass
    
    @property
    def provider_name(self) -> str:
        return self.credentials.provider.value


class GoogleDriveProvider(BaseCloudProvider):
    """Google Drive integration"""
    
    SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
    
    async def initialize(self) -> bool:
        """Initialize Google Drive connection"""
        try:
            # Check if google libraries are available
            try:
                from google.oauth2.credentials import Credentials
                from googleapiclient.discovery import build
            except ImportError:
                logger.warning("Google API libraries not installed. Install with: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")
                return False
            
            if not self.credentials.access_token:
                logger.error("Google Drive: No access token provided")
                return False
            
            creds = Credentials(
                token=self.credentials.access_token,
                refresh_token=self.credentials.refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=self.credentials.api_key,
                client_secret=self.credentials.api_secret
            )
            
            self._service = build('drive', 'v3', credentials=creds)
            self._initialized = True
            logger.info("Google Drive provider initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Google Drive: {e}")
            return False
    
    async def list_files(self, folder_id: Optional[str] = None,
                         file_types: Optional[List[str]] = None) -> List[CloudFile]:
        """List files in Google Drive folder"""
        if not self._initialized:
            return []
        
        try:
            query_parts = ["trashed=false"]
            
            if folder_id:
                query_parts.append(f"'{folder_id}' in parents")
            else:
                query_parts.append("'root' in parents")
            
            if file_types:
                mime_conditions = []
                for ft in file_types:
                    mime_type = self._get_mime_type(ft)
                    if mime_type:
                        mime_conditions.append(f"mimeType='{mime_type}'")
                if mime_conditions:
                    query_parts.append(f"({' or '.join(mime_conditions)})")
            
            query = " and ".join(query_parts)
            
            results = self._service.files().list(
                q=query,
                pageSize=100,
                fields="files(id, name, mimeType, size, modifiedTime, parents, webContentLink)"
            ).execute()
            
            files = []
            for item in results.get('files', []):
                cloud_file = CloudFile(
                    id=item['id'],
                    name=item['name'],
                    path=f"/{item['name']}",
                    size=int(item.get('size', 0)),
                    mime_type=item['mimeType'],
                    modified_at=datetime.fromisoformat(item['modifiedTime'].replace('Z', '+00:00')),
                    provider=CloudProvider.GOOGLE_DRIVE,
                    is_folder=item['mimeType'] == 'application/vnd.google-apps.folder',
                    parent_id=item.get('parents', [None])[0] if item.get('parents') else None,
                    download_url=item.get('webContentLink')
                )
                files.append(cloud_file)
            
            return files
            
        except Exception as e:
            logger.error(f"Google Drive list files error: {e}")
            return []
    
    async def download_file(self, file_id: str) -> bytes:
        """Download a file from Google Drive"""
        if not self._initialized:
            return b''
        
        try:
            from googleapiclient.http import MediaIoBaseDownload
            
            request = self._service.files().get_media(fileId=file_id)
            file_buffer = io.BytesIO()
            downloader = MediaIoBaseDownload(file_buffer, request)
            
            done = False
            while not done:
                status, done = downloader.next_chunk()
            
            return file_buffer.getvalue()
            
        except Exception as e:
            logger.error(f"Google Drive download error: {e}")
            return b''
    
    async def get_file_info(self, file_id: str) -> Optional[CloudFile]:
        """Get file metadata from Google Drive"""
        if not self._initialized:
            return None
        
        try:
            item = self._service.files().get(
                fileId=file_id,
                fields="id, name, mimeType, size, modifiedTime, parents, webContentLink"
            ).execute()
            
            return CloudFile(
                id=item['id'],
                name=item['name'],
                path=f"/{item['name']}",
                size=int(item.get('size', 0)),
                mime_type=item['mimeType'],
                modified_at=datetime.fromisoformat(item['modifiedTime'].replace('Z', '+00:00')),
                provider=CloudProvider.GOOGLE_DRIVE,
                is_folder=item['mimeType'] == 'application/vnd.google-apps.folder',
                parent_id=item.get('parents', [None])[0] if item.get('parents') else None,
                download_url=item.get('webContentLink')
            )
            
        except Exception as e:
            logger.error(f"Google Drive get file info error: {e}")
            return None
    
    async def search_files(self, query: str,
                           file_types: Optional[List[str]] = None) -> List[CloudFile]:
        """Search files in Google Drive"""
        if not self._initialized:
            return []
        
        try:
            search_query = f"name contains '{query}' and trashed=false"
            
            if file_types:
                mime_conditions = []
                for ft in file_types:
                    mime_type = self._get_mime_type(ft)
                    if mime_type:
                        mime_conditions.append(f"mimeType='{mime_type}'")
                if mime_conditions:
                    search_query += f" and ({' or '.join(mime_conditions)})"
            
            results = self._service.files().list(
                q=search_query,
                pageSize=50,
                fields="files(id, name, mimeType, size, modifiedTime, parents)"
            ).execute()
            
            files = []
            for item in results.get('files', []):
                cloud_file = CloudFile(
                    id=item['id'],
                    name=item['name'],
                    path=f"/{item['name']}",
                    size=int(item.get('size', 0)),
                    mime_type=item['mimeType'],
                    modified_at=datetime.fromisoformat(item['modifiedTime'].replace('Z', '+00:00')),
                    provider=CloudProvider.GOOGLE_DRIVE,
                    is_folder=item['mimeType'] == 'application/vnd.google-apps.folder',
                    parent_id=item.get('parents', [None])[0] if item.get('parents') else None
                )
                files.append(cloud_file)
            
            return files
            
        except Exception as e:
            logger.error(f"Google Drive search error: {e}")
            return []
    
    def _get_mime_type(self, extension: str) -> Optional[str]:
        """Map file extension to MIME type"""
        mime_map = {
            'pdf': 'application/pdf',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'doc': 'application/msword',
            'txt': 'text/plain',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'mp3': 'audio/mpeg',
            'wav': 'audio/wav',
            'm4a': 'audio/mp4',
        }
        return mime_map.get(extension.lower())


class OneDriveProvider(BaseCloudProvider):
    """Microsoft OneDrive integration"""
    
    GRAPH_API_URL = "https://graph.microsoft.com/v1.0"
    
    async def initialize(self) -> bool:
        """Initialize OneDrive connection"""
        try:
            try:
                import aiohttp
            except ImportError:
                logger.warning("aiohttp not installed. Install with: pip install aiohttp")
                return False
            
            if not self.credentials.access_token:
                logger.error("OneDrive: No access token provided")
                return False
            
            self._headers = {
                "Authorization": f"Bearer {self.credentials.access_token}",
                "Content-Type": "application/json"
            }
            
            # Test connection
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.GRAPH_API_URL}/me/drive",
                    headers=self._headers
                ) as response:
                    if response.status == 200:
                        self._initialized = True
                        logger.info("OneDrive provider initialized successfully")
                        return True
                    else:
                        logger.error(f"OneDrive auth failed: {response.status}")
                        return False
                        
        except Exception as e:
            logger.error(f"Failed to initialize OneDrive: {e}")
            return False
    
    async def list_files(self, folder_id: Optional[str] = None,
                         file_types: Optional[List[str]] = None) -> List[CloudFile]:
        """List files in OneDrive folder"""
        if not self._initialized:
            return []
        
        try:
            import aiohttp
            
            if folder_id:
                url = f"{self.GRAPH_API_URL}/me/drive/items/{folder_id}/children"
            else:
                url = f"{self.GRAPH_API_URL}/me/drive/root/children"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self._headers) as response:
                    if response.status != 200:
                        return []
                    
                    data = await response.json()
                    files = []
                    
                    for item in data.get('value', []):
                        # Filter by file type if specified
                        if file_types and 'file' in item:
                            ext = Path(item['name']).suffix.lower().lstrip('.')
                            if ext not in file_types:
                                continue
                        
                        cloud_file = CloudFile(
                            id=item['id'],
                            name=item['name'],
                            path=item.get('parentReference', {}).get('path', '') + '/' + item['name'],
                            size=item.get('size', 0),
                            mime_type=item.get('file', {}).get('mimeType', 'application/octet-stream'),
                            modified_at=datetime.fromisoformat(item['lastModifiedDateTime'].replace('Z', '+00:00')),
                            provider=CloudProvider.ONEDRIVE,
                            is_folder='folder' in item,
                            parent_id=item.get('parentReference', {}).get('id'),
                            download_url=item.get('@microsoft.graph.downloadUrl')
                        )
                        files.append(cloud_file)
                    
                    return files
                    
        except Exception as e:
            logger.error(f"OneDrive list files error: {e}")
            return []
    
    async def download_file(self, file_id: str) -> bytes:
        """Download a file from OneDrive"""
        if not self._initialized:
            return b''
        
        try:
            import aiohttp
            
            url = f"{self.GRAPH_API_URL}/me/drive/items/{file_id}/content"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self._headers) as response:
                    if response.status == 200:
                        return await response.read()
                    return b''
                    
        except Exception as e:
            logger.error(f"OneDrive download error: {e}")
            return b''
    
    async def get_file_info(self, file_id: str) -> Optional[CloudFile]:
        """Get file metadata from OneDrive"""
        if not self._initialized:
            return None
        
        try:
            import aiohttp
            
            url = f"{self.GRAPH_API_URL}/me/drive/items/{file_id}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self._headers) as response:
                    if response.status != 200:
                        return None
                    
                    item = await response.json()
                    
                    return CloudFile(
                        id=item['id'],
                        name=item['name'],
                        path=item.get('parentReference', {}).get('path', '') + '/' + item['name'],
                        size=item.get('size', 0),
                        mime_type=item.get('file', {}).get('mimeType', 'application/octet-stream'),
                        modified_at=datetime.fromisoformat(item['lastModifiedDateTime'].replace('Z', '+00:00')),
                        provider=CloudProvider.ONEDRIVE,
                        is_folder='folder' in item,
                        parent_id=item.get('parentReference', {}).get('id'),
                        download_url=item.get('@microsoft.graph.downloadUrl')
                    )
                    
        except Exception as e:
            logger.error(f"OneDrive get file info error: {e}")
            return None
    
    async def search_files(self, query: str,
                           file_types: Optional[List[str]] = None) -> List[CloudFile]:
        """Search files in OneDrive"""
        if not self._initialized:
            return []
        
        try:
            import aiohttp
            
            url = f"{self.GRAPH_API_URL}/me/drive/root/search(q='{query}')"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self._headers) as response:
                    if response.status != 200:
                        return []
                    
                    data = await response.json()
                    files = []
                    
                    for item in data.get('value', []):
                        if file_types and 'file' in item:
                            ext = Path(item['name']).suffix.lower().lstrip('.')
                            if ext not in file_types:
                                continue
                        
                        cloud_file = CloudFile(
                            id=item['id'],
                            name=item['name'],
                            path=item.get('parentReference', {}).get('path', '') + '/' + item['name'],
                            size=item.get('size', 0),
                            mime_type=item.get('file', {}).get('mimeType', 'application/octet-stream'),
                            modified_at=datetime.fromisoformat(item['lastModifiedDateTime'].replace('Z', '+00:00')),
                            provider=CloudProvider.ONEDRIVE,
                            is_folder='folder' in item,
                            parent_id=item.get('parentReference', {}).get('id')
                        )
                        files.append(cloud_file)
                    
                    return files
                    
        except Exception as e:
            logger.error(f"OneDrive search error: {e}")
            return []


class AWSS3Provider(BaseCloudProvider):
    """AWS S3 integration"""
    
    async def initialize(self) -> bool:
        """Initialize AWS S3 connection"""
        try:
            try:
                import boto3
            except ImportError:
                logger.warning("boto3 not installed. Install with: pip install boto3")
                return False
            
            if not all([
                self.credentials.aws_access_key_id,
                self.credentials.aws_secret_access_key,
                self.credentials.s3_bucket
            ]):
                logger.error("S3: Missing required credentials")
                return False
            
            self._s3 = boto3.client(
                's3',
                aws_access_key_id=self.credentials.aws_access_key_id,
                aws_secret_access_key=self.credentials.aws_secret_access_key,
                region_name=self.credentials.aws_region or 'us-east-1'
            )
            
            self._bucket = self.credentials.s3_bucket
            
            # Test connection
            self._s3.head_bucket(Bucket=self._bucket)
            
            self._initialized = True
            logger.info("AWS S3 provider initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize AWS S3: {e}")
            return False
    
    async def list_files(self, folder_id: Optional[str] = None,
                         file_types: Optional[List[str]] = None) -> List[CloudFile]:
        """List files in S3 bucket/prefix"""
        if not self._initialized:
            return []
        
        try:
            prefix = folder_id or ""
            
            response = self._s3.list_objects_v2(
                Bucket=self._bucket,
                Prefix=prefix,
                MaxKeys=100
            )
            
            files = []
            for obj in response.get('Contents', []):
                key = obj['Key']
                name = key.split('/')[-1]
                
                if not name:  # Skip folder markers
                    continue
                
                # Filter by file type
                if file_types:
                    ext = Path(name).suffix.lower().lstrip('.')
                    if ext not in file_types:
                        continue
                
                cloud_file = CloudFile(
                    id=key,
                    name=name,
                    path=f"/{key}",
                    size=obj['Size'],
                    mime_type=self._guess_mime_type(name),
                    modified_at=obj['LastModified'].replace(tzinfo=None),
                    provider=CloudProvider.AWS_S3,
                    is_folder=key.endswith('/'),
                    parent_id=folder_id
                )
                files.append(cloud_file)
            
            return files
            
        except Exception as e:
            logger.error(f"S3 list files error: {e}")
            return []
    
    async def download_file(self, file_id: str) -> bytes:
        """Download a file from S3"""
        if not self._initialized:
            return b''
        
        try:
            response = self._s3.get_object(Bucket=self._bucket, Key=file_id)
            return response['Body'].read()
            
        except Exception as e:
            logger.error(f"S3 download error: {e}")
            return b''
    
    async def get_file_info(self, file_id: str) -> Optional[CloudFile]:
        """Get file metadata from S3"""
        if not self._initialized:
            return None
        
        try:
            response = self._s3.head_object(Bucket=self._bucket, Key=file_id)
            name = file_id.split('/')[-1]
            
            return CloudFile(
                id=file_id,
                name=name,
                path=f"/{file_id}",
                size=response['ContentLength'],
                mime_type=response.get('ContentType', 'application/octet-stream'),
                modified_at=response['LastModified'].replace(tzinfo=None),
                provider=CloudProvider.AWS_S3,
                is_folder=False,
                parent_id='/'.join(file_id.split('/')[:-1]) or None
            )
            
        except Exception as e:
            logger.error(f"S3 get file info error: {e}")
            return None
    
    async def search_files(self, query: str,
                           file_types: Optional[List[str]] = None) -> List[CloudFile]:
        """Search files in S3 (prefix-based)"""
        if not self._initialized:
            return []
        
        # S3 doesn't have true search, so we list and filter
        all_files = await self.list_files(file_types=file_types)
        
        query_lower = query.lower()
        return [f for f in all_files if query_lower in f.name.lower()]
    
    def _guess_mime_type(self, filename: str) -> str:
        """Guess MIME type from filename"""
        import mimetypes
        mime_type, _ = mimetypes.guess_type(filename)
        return mime_type or 'application/octet-stream'


class DropboxProvider(BaseCloudProvider):
    """Dropbox integration"""
    
    API_URL = "https://api.dropboxapi.com/2"
    CONTENT_URL = "https://content.dropboxapi.com/2"
    
    async def initialize(self) -> bool:
        """Initialize Dropbox connection"""
        try:
            try:
                import aiohttp
            except ImportError:
                logger.warning("aiohttp not installed. Install with: pip install aiohttp")
                return False
            
            if not self.credentials.access_token:
                logger.error("Dropbox: No access token provided")
                return False
            
            self._headers = {
                "Authorization": f"Bearer {self.credentials.access_token}",
                "Content-Type": "application/json"
            }
            
            # Test connection
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.API_URL}/users/get_current_account",
                    headers=self._headers
                ) as response:
                    if response.status == 200:
                        self._initialized = True
                        logger.info("Dropbox provider initialized successfully")
                        return True
                    else:
                        logger.error(f"Dropbox auth failed: {response.status}")
                        return False
                        
        except Exception as e:
            logger.error(f"Failed to initialize Dropbox: {e}")
            return False
    
    async def list_files(self, folder_id: Optional[str] = None,
                         file_types: Optional[List[str]] = None) -> List[CloudFile]:
        """List files in Dropbox folder"""
        if not self._initialized:
            return []
        
        try:
            import aiohttp
            
            path = folder_id or ""
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.API_URL}/files/list_folder",
                    headers=self._headers,
                    json={"path": path, "limit": 100}
                ) as response:
                    if response.status != 200:
                        return []
                    
                    data = await response.json()
                    files = []
                    
                    for entry in data.get('entries', []):
                        # Filter by file type
                        if file_types and entry['.tag'] == 'file':
                            ext = Path(entry['name']).suffix.lower().lstrip('.')
                            if ext not in file_types:
                                continue
                        
                        cloud_file = CloudFile(
                            id=entry.get('id', entry['path_lower']),
                            name=entry['name'],
                            path=entry['path_display'],
                            size=entry.get('size', 0),
                            mime_type=self._guess_mime_type(entry['name']),
                            modified_at=datetime.fromisoformat(
                                entry.get('server_modified', datetime.now().isoformat()).replace('Z', '+00:00')
                            ) if 'server_modified' in entry else datetime.now(),
                            provider=CloudProvider.DROPBOX,
                            is_folder=entry['.tag'] == 'folder',
                            parent_id=folder_id
                        )
                        files.append(cloud_file)
                    
                    return files
                    
        except Exception as e:
            logger.error(f"Dropbox list files error: {e}")
            return []
    
    async def download_file(self, file_id: str) -> bytes:
        """Download a file from Dropbox"""
        if not self._initialized:
            return b''
        
        try:
            import aiohttp
            
            headers = {
                "Authorization": f"Bearer {self.credentials.access_token}",
                "Dropbox-API-Arg": json.dumps({"path": file_id})
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.CONTENT_URL}/files/download",
                    headers=headers
                ) as response:
                    if response.status == 200:
                        return await response.read()
                    return b''
                    
        except Exception as e:
            logger.error(f"Dropbox download error: {e}")
            return b''
    
    async def get_file_info(self, file_id: str) -> Optional[CloudFile]:
        """Get file metadata from Dropbox"""
        if not self._initialized:
            return None
        
        try:
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.API_URL}/files/get_metadata",
                    headers=self._headers,
                    json={"path": file_id}
                ) as response:
                    if response.status != 200:
                        return None
                    
                    entry = await response.json()
                    
                    return CloudFile(
                        id=entry.get('id', entry['path_lower']),
                        name=entry['name'],
                        path=entry['path_display'],
                        size=entry.get('size', 0),
                        mime_type=self._guess_mime_type(entry['name']),
                        modified_at=datetime.fromisoformat(
                            entry.get('server_modified', datetime.now().isoformat()).replace('Z', '+00:00')
                        ) if 'server_modified' in entry else datetime.now(),
                        provider=CloudProvider.DROPBOX,
                        is_folder=entry['.tag'] == 'folder'
                    )
                    
        except Exception as e:
            logger.error(f"Dropbox get file info error: {e}")
            return None
    
    async def search_files(self, query: str,
                           file_types: Optional[List[str]] = None) -> List[CloudFile]:
        """Search files in Dropbox"""
        if not self._initialized:
            return []
        
        try:
            import aiohttp
            
            search_options = {
                "path": "",
                "query": query,
                "options": {
                    "max_results": 50,
                    "file_status": "active"
                }
            }
            
            if file_types:
                search_options["options"]["file_extensions"] = file_types
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.API_URL}/files/search_v2",
                    headers=self._headers,
                    json=search_options
                ) as response:
                    if response.status != 200:
                        return []
                    
                    data = await response.json()
                    files = []
                    
                    for match in data.get('matches', []):
                        entry = match.get('metadata', {}).get('metadata', {})
                        if not entry:
                            continue
                        
                        cloud_file = CloudFile(
                            id=entry.get('id', entry.get('path_lower', '')),
                            name=entry.get('name', ''),
                            path=entry.get('path_display', ''),
                            size=entry.get('size', 0),
                            mime_type=self._guess_mime_type(entry.get('name', '')),
                            modified_at=datetime.fromisoformat(
                                entry.get('server_modified', datetime.now().isoformat()).replace('Z', '+00:00')
                            ) if 'server_modified' in entry else datetime.now(),
                            provider=CloudProvider.DROPBOX,
                            is_folder=entry.get('.tag') == 'folder'
                        )
                        files.append(cloud_file)
                    
                    return files
                    
        except Exception as e:
            logger.error(f"Dropbox search error: {e}")
            return []
    
    def _guess_mime_type(self, filename: str) -> str:
        """Guess MIME type from filename"""
        import mimetypes
        mime_type, _ = mimetypes.guess_type(filename)
        return mime_type or 'application/octet-stream'


class MockCloudProvider(BaseCloudProvider):
    """Mock provider for demonstration purposes"""
    
    async def initialize(self) -> bool:
        return True
    
    async def list_files(self, folder_id: Optional[str] = None, 
                         file_types: Optional[List[str]] = None) -> List[CloudFile]:
        """Return simulated files"""
        # Simulate different folders
        if folder_id == "folder_docs":
            return [
                CloudFile(
                    id="doc_1", name="Project_Proposal.docx", 
                    path="/Documents/Project_Proposal.docx", size=1024 * 25, 
                    mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    modified_at=datetime.now(), provider=self.credentials.provider
                ),
                CloudFile(
                    id="doc_2", name="Financial_Report_Q1.pdf", 
                    path="/Documents/Financial_Report_Q1.pdf", size=1024 * 500, 
                    mime_type="application/pdf",
                    modified_at=datetime.now(), provider=self.credentials.provider
                )
            ]
        elif folder_id == "folder_imgs":
            return [
                CloudFile(
                    id="img_1", name="Architecture_Diagram.png", 
                    path="/Images/Architecture_Diagram.png", size=1024 * 1500, 
                    mime_type="image/png",
                    modified_at=datetime.now(), provider=self.credentials.provider
                ),
                CloudFile(
                    id="img_2", name="Team_Photo.jpg", 
                    path="/Images/Team_Photo.jpg", size=1024 * 2200, 
                    mime_type="image/jpeg",
                    modified_at=datetime.now(), provider=self.credentials.provider
                )
            ]
        
        # Root folder
        return [
            CloudFile(
                id="folder_docs", name="Documents", path="/Documents", 
                size=0, mime_type="application/vnd.google-apps.folder",
                modified_at=datetime.now(), provider=self.credentials.provider,
                is_folder=True
            ),
            CloudFile(
                id="folder_imgs", name="Images", path="/Images", 
                size=0, mime_type="application/vnd.google-apps.folder",
                modified_at=datetime.now(), provider=self.credentials.provider,
                is_folder=True
            ),
            CloudFile(
                id="demo_txt", name="Welcome_to_Demo.txt", 
                path="/Welcome_to_Demo.txt", size=120, 
                mime_type="text/plain",
                modified_at=datetime.now(), provider=self.credentials.provider
            ),
            CloudFile(
                id="demo_pdf", name="Multimodal_RAG_Guide.pdf", 
                path="/Multimodal_RAG_Guide.pdf", size=1024 * 1024 * 2, 
                mime_type="application/pdf",
                modified_at=datetime.now(), provider=self.credentials.provider
            )
        ]
    
    async def download_file(self, file_id: str) -> bytes:
        """Return dummy content"""
        if "pdf" in file_id:
            # Return a minimal valid PDF header/content just in case (though it won't be a real readable PDF)
            return b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/MediaBox [0 0 595 842]\n/Resources <<\n/Font <<\n/F1 4 0 R\n>>\n>>\n/Contents 5 0 R\n>>\nendobj\n4 0 obj\n<<\n/Type /Font\n/Subtype /Type1\n/Name /F1\n/BaseFont /Helvetica\n>>\nendobj\n5 0 obj\n<<\n/Length 44\n>>\nstream\nBT\n/F1 24 Tf\n100 700 Td\n(This is a demo PDF file from Cloud Storage) Tj\nET\nendstream\nendobj\nxref\n0 6\n0000000000 65535 f \n0000000010 00000 n \n0000000060 00000 n \n0000000157 00000 n \n0000000288 00000 n \n0000000375 00000 n \ntrailer\n<<\n/Size 6\n/Root 1 0 R\n>>\nstartxref\n469\n%%EOF"
        elif "png" in file_id or "jpg" in file_id:
            # Create a simple 1x1 pixel image or just dummy bytes that might fail image processing but succeed download
            # Ideally we'd return a valid tiny image bytes
            return b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
        
        return f"This is simulate content for file {file_id}.\nCloud Storage Integration Demo.".encode('utf-8')

    async def get_file_info(self, file_id: str) -> CloudFile:
        # Mock database of files
        mock_files = {
            "doc_1": ("Project_Proposal.docx", 1024 * 25, "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
            "doc_2": ("Financial_Report_Q1.pdf", 1024 * 500, "application/pdf"),
            "img_1": ("Architecture_Diagram.png", 1024 * 1500, "image/png"),
            "img_2": ("Team_Photo.jpg", 1024 * 2200, "image/jpeg"),
            "demo_txt": ("Welcome_to_Demo.txt", 120, "text/plain"),
            "demo_pdf": ("Multimodal_RAG_Guide.pdf", 1024 * 1024 * 2, "application/pdf")
        }
        
        if file_id in mock_files:
            name, size, mime = mock_files[file_id]
            return CloudFile(
                id=file_id, name=name, path=f"/{name}", 
                size=size, mime_type=mime, 
                modified_at=datetime.now(), provider=self.credentials.provider
            )
            
        return CloudFile(
            id=file_id, name="Demo_File", path=f"/{file_id}", 
            size=1000, mime_type="text/plain", 
            modified_at=datetime.now(), provider=self.credentials.provider
        )

    async def search_files(self, query: str,
                           file_types: Optional[List[str]] = None) -> List[CloudFile]:
        """Search mock files"""
        all_files = await self.list_files() + \
                   await self.list_files("folder_docs") + \
                   await self.list_files("folder_imgs")
        
        return [f for f in all_files if query.lower() in f.name.lower()]


class CloudStorageManager:
    """
    Unified manager for all cloud storage providers.
    Handles provider initialization, caching, and operations.
    """
    
    def __init__(self):
        self._providers: Dict[CloudProvider, BaseCloudProvider] = {}
        self._credentials_file = Path("./data/cloud_credentials.json")
        self._supported_file_types = [
            'pdf', 'docx', 'doc', 'txt', 
            'jpg', 'jpeg', 'png', 'bmp', 'tiff',
            'mp3', 'wav', 'm4a', 'mp4'
        ]
    
    async def connect_provider(self, credentials: CloudCredentials) -> Dict[str, Any]:
        """Connect to a cloud storage provider"""
        try:
            # CHECK FOR DEMO MODE
            is_demo = False
            # Check if any credential field is "demo"
            if (str(credentials.access_token) == "demo" or 
                str(credentials.api_key) == "demo" or 
                str(credentials.aws_access_key_id) == "demo"):
                is_demo = True
            
            provider_instance = None
            
            if is_demo:
                logger.info(f"Connecting to {credentials.provider.value} in DEMO mode")
                provider_instance = MockCloudProvider(credentials)
            else:
                provider_class = self._get_provider_class(credentials.provider)
                if not provider_class:
                    return {
                        "success": False,
                        "error": f"Unknown provider: {credentials.provider.value}"
                    }
                provider_instance = provider_class(credentials)
            
            # Initialize connection
            if await provider_instance.initialize():
                self._providers[credentials.provider] = provider_instance
                
                # Save credentials (even demo ones to persist session)
                self._save_credentials(credentials)
                
                return {
                    "success": True,
                    "provider": credentials.provider.value,
                    "message": f"Connected to {credentials.provider.value} successfully"
                }
            else:
                return {
                    "success": False,
                    "error": f"Failed to connect to {credentials.provider.value}"
                }
                
        except Exception as e:
            logger.error(f"Connect provider error: {e}")
            return {"success": False, "error": str(e)}
    
    async def disconnect_provider(self, provider: CloudProvider) -> Dict[str, Any]:
        """Disconnect from a cloud storage provider"""
        if provider in self._providers:
            del self._providers[provider]
            self._remove_credentials(provider)
            
            return {
                "success": True,
                "message": f"Disconnected from {provider.value}"
            }
        else:
            return {
                "success": False,
                "error": f"Provider {provider.value} is not connected"
            }
    
    def get_connected_providers(self) -> List[str]:
        """Get list of connected provider names"""
        return [p.value for p in self._providers.keys()]
    
    async def list_files(self, provider: CloudProvider, 
                         folder_id: Optional[str] = None) -> List[CloudFile]:
        """List files from a provider"""
        if provider not in self._providers:
            return []
        
        return await self._providers[provider].list_files(
            folder_id=folder_id,
            file_types=self._supported_file_types
        )
    
    async def download_file(self, provider: CloudProvider, file_id: str) -> bytes:
        """Download a file from a provider"""
        if provider not in self._providers:
            return b''
        
        return await self._providers[provider].download_file(file_id)
    
    async def download_and_save(self, provider: CloudProvider, file_id: str, 
                                 save_path: Path) -> Optional[Path]:
        """Download a file and save it locally"""
        file_data = await self.download_file(provider, file_id)
        
        if not file_data:
            return None
        
        try:
            save_path.parent.mkdir(parents=True, exist_ok=True)
            save_path.write_bytes(file_data)
            return save_path
        except Exception as e:
            logger.error(f"Failed to save downloaded file: {e}")
            return None
    
    async def search_files(self, provider: CloudProvider, 
                           query: str) -> List[CloudFile]:
        """Search files in a provider"""
        if provider not in self._providers:
            return []
        
        return await self._providers[provider].search_files(
            query=query,
            file_types=self._supported_file_types
        )
    
    async def search_all_providers(self, query: str) -> Dict[str, List[CloudFile]]:
        """Search files across all connected providers"""
        results = {}
        
        for provider in self._providers:
            files = await self.search_files(provider, query)
            if files:
                results[provider.value] = files
        
        return results
    
    async def import_file(self, provider: CloudProvider, file_id: str,
                          upload_dir: Path) -> Optional[Dict[str, Any]]:
        """Import a file from cloud storage to local uploads"""
        if provider not in self._providers:
            return None
        
        # Get file info - try/except for robust handling
        try:
            file_info = await self._providers[provider].get_file_info(file_id)
            filename = file_info.name if file_info else f"imported_{file_id}_{int(time.time())}.bin"
        except Exception:
            filename = f"imported_{file_id}_{int(time.time())}.bin"
        
        # Download file
        file_data = await self.download_file(provider, file_id)
        if not file_data:
            return None
        
        # Save locally
        local_path = upload_dir / filename
        
        # Avoid overwriting - add number suffix if needed
        counter = 1
        while local_path.exists():
            stem = Path(filename).stem
            suffix = Path(filename).suffix
            local_path = upload_dir / f"{stem}_{counter}{suffix}"
            counter += 1
        
        local_path.write_bytes(file_data)
        
        return {
            "success": True,
            "local_path": str(local_path),
            "file_name": local_path.name,
            "file_size": len(file_data),
            "source_provider": provider.value,
            "source_file_id": file_id
        }
    
    async def batch_import(self, provider: CloudProvider, file_ids: List[str],
                           upload_dir: Path) -> List[Dict[str, Any]]:
        """Import multiple files from cloud storage"""
        results = []
        
        for file_id in file_ids:
            result = await self.import_file(provider, file_id, upload_dir)
            if result:
                results.append(result)
            else:
                results.append({
                    "success": False,
                    "file_id": file_id,
                    "error": "Failed to import file"
                })
        
        return results
    
    def _get_provider_class(self, provider: CloudProvider):
        """Get the provider class for a given provider type"""
        provider_map = {
            CloudProvider.GOOGLE_DRIVE: GoogleDriveProvider,
            CloudProvider.ONEDRIVE: OneDriveProvider,
            CloudProvider.AWS_S3: AWSS3Provider,
            CloudProvider.DROPBOX: DropboxProvider
        }
        return provider_map.get(provider)
    
    def _save_credentials(self, credentials: CloudCredentials):
        """Save credentials to file (should be encrypted in production)"""
        try:
            self._credentials_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Load existing credentials
            existing = {}
            if self._credentials_file.exists():
                existing = json.loads(self._credentials_file.read_text())
            
            # Add/update this provider's credentials
            cred_data = {
                "access_token": credentials.access_token,
                "refresh_token": credentials.refresh_token,
                "api_key": credentials.api_key,
                "api_secret": credentials.api_secret,
                "aws_access_key_id": credentials.aws_access_key_id,
                "aws_secret_access_key": credentials.aws_secret_access_key,
                "aws_region": credentials.aws_region,
                "s3_bucket": credentials.s3_bucket
            }
            
            existing[credentials.provider.value] = cred_data
            
            self._credentials_file.write_text(json.dumps(existing, indent=2))
            
        except Exception as e:
            logger.error(f"Failed to save credentials: {e}")
    
    def _remove_credentials(self, provider: CloudProvider):
        """Remove credentials for a provider"""
        try:
            if not self._credentials_file.exists():
                return
            
            existing = json.loads(self._credentials_file.read_text())
            
            if provider.value in existing:
                del existing[provider.value]
                self._credentials_file.write_text(json.dumps(existing, indent=2))
                
        except Exception as e:
            logger.error(f"Failed to remove credentials: {e}")
    
    async def load_saved_connections(self) -> Dict[str, bool]:
        """Load and reconnect to saved providers"""
        results = {}
        
        try:
            if not self._credentials_file.exists():
                return results
            
            saved = json.loads(self._credentials_file.read_text())
            
            for provider_name, cred_data in saved.items():
                try:
                    provider = CloudProvider(provider_name)
                    credentials = CloudCredentials(
                        provider=provider,
                        access_token=cred_data.get('access_token'),
                        refresh_token=cred_data.get('refresh_token'),
                        api_key=cred_data.get('api_key'),
                        api_secret=cred_data.get('api_secret'),
                        aws_access_key_id=cred_data.get('aws_access_key_id'),
                        aws_secret_access_key=cred_data.get('aws_secret_access_key'),
                        aws_region=cred_data.get('aws_region'),
                        s3_bucket=cred_data.get('s3_bucket')
                    )
                    
                    result = await self.connect_provider(credentials)
                    results[provider_name] = result.get('success', False)
                    
                except Exception as e:
                    logger.error(f"Failed to reconnect {provider_name}: {e}")
                    results[provider_name] = False
            
        except Exception as e:
            logger.error(f"Failed to load saved connections: {e}")
        
        return results


# Global instance
cloud_storage_manager = CloudStorageManager()

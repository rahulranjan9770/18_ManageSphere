# ☁️ Cloud Storage Integration

This document explains the cloud storage integration feature for the Multimodal RAG System, supporting Google Drive, OneDrive, AWS S3, and Dropbox.

## ✨ Features

### Supported Providers

| Provider | Features | Authentication |
|----------|----------|----------------|
| **Google Drive** | Browse, search, import files | OAuth2 (Access Token) |
| **OneDrive** | Browse, search, import files | OAuth2 (Access Token) |
| **AWS S3** | Browse, import files (prefix-based search) | AWS Credentials |
| **Dropbox** | Browse, search, import files | OAuth2 (Access Token) |

### Capabilities

1. **Connect/Disconnect Providers**
   - Secure credential storage
   - Multi-provider support
   - Auto-reconnect on reload

2. **File Browser**
   - Visual file/folder navigation
   - File type icons
   - Size and date display
   - Search capability

3. **Import Files**
   - Single file import
   - Batch import multiple files
   - Auto-index on import
   - Progress tracking

4. **Search**
   - Provider-specific search
   - Cross-provider search
   - Filter by supported file types

## 🚀 Getting Started

### 1. Install Required Dependencies

```bash
pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
pip install boto3
pip install aiohttp
```

### 2. Configure Providers

#### Google Drive Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable the Google Drive API
4. Create OAuth 2.0 credentials
5. Get your access token using the OAuth flow

#### OneDrive Setup

1. Go to [Azure Portal](https://portal.azure.com/)
2. Register an application in Azure AD
3. Configure API permissions for Microsoft Graph
4. Generate access token

#### AWS S3 Setup

1. Go to [AWS IAM Console](https://console.aws.amazon.com/iam/)
2. Create a new IAM user or use existing
3. Attach `AmazonS3ReadOnlyAccess` policy
4. Generate access keys

#### Dropbox Setup

1. Go to [Dropbox App Console](https://www.dropbox.com/developers/apps)
2. Create a new app
3. Generate access token

## 💻 API Endpoints

### Provider Management

```
GET  /cloud/providers          # Get supported and connected providers
POST /cloud/connect            # Connect to a provider
POST /cloud/disconnect         # Disconnect from a provider
POST /cloud/reconnect          # Reconnect to saved providers
```

### File Operations

```
GET  /cloud/{provider}/files            # List files in folder
GET  /cloud/{provider}/search           # Search files
GET  /cloud/search-all                  # Search all providers
POST /cloud/{provider}/import           # Import single file
POST /cloud/{provider}/import-batch     # Import multiple files
```

### Example: Connect to AWS S3

```bash
curl -X POST "http://localhost:8000/cloud/connect?provider=aws_s3&aws_access_key_id=YOUR_KEY&aws_secret_access_key=YOUR_SECRET&aws_region=us-east-1&s3_bucket=your-bucket"
```

### Example: List Files from Google Drive

```bash
curl "http://localhost:8000/cloud/google_drive/files"
```

### Example: Import File with Auto-Index

```bash
curl -X POST "http://localhost:8000/cloud/google_drive/import?file_id=FILE_ID&auto_index=true"
```

## 🎨 UI Components

### Provider Cards

Each provider is displayed as a card showing:
- Provider icon and name
- Connection status (connected/disconnected)
- Connect/Disconnect button

### File Browser

When connected to a provider:
- Breadcrumb navigation
- File/folder list with icons
- Search bar
- Bulk selection
- Import buttons

### Connection Modal

A modal dialog for entering credentials:
- Provider-specific form fields
- Help links to documentation
- Connect/Cancel buttons

## 📁 Supported File Types

The following file types can be imported and indexed:

| Category | Extensions |
|----------|------------|
| Documents | PDF, DOCX, DOC, TXT |
| Images | JPG, JPEG, PNG, BMP, TIFF |
| Audio | MP3, WAV, M4A, MP4, FLAC, OGG, AAC |

## 🔐 Security

### Credential Storage

- Credentials are stored locally in `./data/cloud_credentials.json`
- **WARNING**: In production, use encrypted storage!
- Consider using environment variables or a secret manager

### Best Practices

1. Use service accounts where possible
2. Grant minimal required permissions (read-only)
3. Rotate access tokens regularly
4. Don't commit credentials to version control

## 🔧 Configuration

### Environment Variables

You can set default credentials via environment variables:

```bash
# Google Drive
export GOOGLE_DRIVE_ACCESS_TOKEN="your-token"
export GOOGLE_DRIVE_CLIENT_ID="your-client-id"
export GOOGLE_DRIVE_CLIENT_SECRET="your-client-secret"

# OneDrive
export ONEDRIVE_ACCESS_TOKEN="your-token"

# AWS S3
export AWS_ACCESS_KEY_ID="your-key"
export AWS_SECRET_ACCESS_KEY="your-secret"
export AWS_REGION="us-east-1"
export AWS_S3_BUCKET="your-bucket"

# Dropbox
export DROPBOX_ACCESS_TOKEN="your-token"
```

## 🐛 Troubleshooting

### Common Issues

#### "Failed to connect to provider"
- Check if credentials are correct
- Ensure required dependencies are installed
- Check API rate limits

#### "No files found"
- Verify the path/folder exists
- Check read permissions
- Ensure file types are supported

#### "Import failed"
- Check disk space
- Verify file size limits
- Check network connectivity

### Debug Mode

Enable debug logging:

```python
# In backend/config.py
debug: bool = True
```

## 📊 Architecture

```
┌─────────────────────────────────────────────────┐
│                  Frontend                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │ Provider │  │   File   │  │  Import  │       │
│  │  Cards   │  │ Browser  │  │ Progress │       │
│  └──────────┘  └──────────┘  └──────────┘       │
└─────────────────────┬───────────────────────────┘
                      │ HTTP API
┌─────────────────────┴───────────────────────────┐
│                 Backend API                      │
│  ┌──────────────────────────────────────────┐   │
│  │         CloudStorageManager               │   │
│  │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────┐ │   │
│  │  │ Google │ │OneDrive│ │  S3    │ │Drop│ │   │
│  │  │ Drive  │ │        │ │        │ │box │ │   │
│  │  └────────┘ └────────┘ └────────┘ └────┘ │   │
│  └──────────────────────────────────────────┘   │
└─────────────────────┬───────────────────────────┘
                      │ SDK/API
┌─────────────────────┴───────────────────────────┐
│            Cloud Provider APIs                   │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐│
│  │ Google  │ │  MS     │ │  AWS    │ │ Dropbox ││
│  │ APIs    │ │ Graph   │ │ S3 API  │ │   API   ││
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘│
└─────────────────────────────────────────────────┘
```

## 📝 Files Added

```
backend/
└── cloud/
    ├── __init__.py
    └── cloud_storage.py         # Main integration module

frontend/
└── static/
    ├── css/
    │   └── cloud.css           # Cloud storage styles
    └── js/
        └── cloud.js            # Cloud storage JavaScript

CLOUD_STORAGE_README.md         # This documentation
```

## 🔄 Future Improvements

- [ ] OAuth2 flow implementation (currently requires pre-generated tokens)
- [ ] Sync folders (two-way sync)
- [ ] Webhook support for real-time updates
- [ ] Encrypted credential storage
- [ ] More cloud providers (Box, iCloud, etc.)
- [ ] Folder-level import
- [ ] File preview before import

## ✅ Checklist

- [x] Google Drive integration
- [x] OneDrive integration
- [x] AWS S3 integration
- [x] Dropbox integration
- [x] File browsing
- [x] File search
- [x] Single file import
- [x] Batch import
- [x] Auto-indexing
- [x] Connection management
- [x] Frontend UI
- [x] API documentation

---

**Note**: All existing features remain untouched. The cloud storage integration is additive and doesn't interfere with any existing functionality.

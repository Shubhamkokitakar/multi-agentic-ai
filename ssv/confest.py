import os
import pytest
from unittest.mock import MagicMock, patch
import pandas as pd

# Set environment variables before any imports
os.environ.update({
    "TESTING": "true",
    "AZURE_BLOB_NAME": "test-storage-account",
    "AZURE_BLOB_KEY": "test-storage-key",
    "CVX_MNEMONIC": "test",
    "APP_ENV": "test",
    "service_name": "test-service",
    "cogsearch_api_key": "test-key",
    "AZURE_TENANT_ID": "test-tenant",
    "AZURE_CLIENT_ID": "test-client",
    "AZURE_CLIENT_SECRET": "test-secret"
})

@pytest.fixture(autouse=True)
def mock_blob_service():
    """Mock Azure Blob Storage"""
    with patch('azure.storage.blob.BlobServiceClient', autospec=True) as mock_blob_service:
        # Create a mock container client
        mock_container = MagicMock()
        mock_container.exists.return_value = True
        
        # Create a mock blob client
        mock_blob = MagicMock()
        mock_blob.exists.return_value = True
        mock_blob.download_blob.return_value.readall.return_value = b'[]'
        
        # Set up the container client to return our mock blob client
        mock_container.get_blob_client.return_value = mock_blob
        
        # Set up the service client to return our mock container client
        mock_instance = MagicMock()
        mock_instance.get_container_client.return_value = mock_container
        mock_blob_service.return_value = mock_instance
        
        yield mock_blob_service

def pytest_configure(config):
    """Configure pytest settings"""
    config.option.asyncio_mode = "strict"
    config.option.asyncio_default_fixture_loop_scope = "function"

    # Configure warning filters
    for warning in [
        "ignore::DeprecationWarning:opencensus.*:",
        "ignore::pytest.PytestDeprecationWarning",
        "ignore:.*'locale.getdefaultlocale' is deprecated.*:DeprecationWarning",
        "ignore:.*datetime.datetime.utcnow() is deprecated.*:DeprecationWarning",
        "ignore:Pyarrow will become a required dependency.*:DeprecationWarning",
        "ignore::DeprecationWarning:pandas.*",
    ]:
        config.addinivalue_line("filterwarnings", warning)
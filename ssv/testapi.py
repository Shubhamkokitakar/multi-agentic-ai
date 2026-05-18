from fastapi.testclient import TestClient
import json, os
from unittest.mock import patch, MagicMock
import jwt
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv

# Create SQL helper mock
mock_sql_helper = MagicMock()
mock_sql_helper.execute_sql_query.return_value = pd.DataFrame({"SupplierName": ["Test Supplier"]})

# Mock SQLAlchemy engine and connection
mock_engine = MagicMock()
mock_connection = MagicMock()
mock_engine.connect.return_value = mock_connection

# Patch both SQLAlchemy create_engine and SQLHelper
with patch('sqlalchemy.create_engine', return_value=mock_engine), \
     patch('services.data_query_processor.SQLHelper', return_value=mock_sql_helper):
    from main import app

load_dotenv()



# Set test environment
os.environ["TESTING"] = "true"

# Create a mock token for testing
def get_test_token():
    test_payload = {
        "oid": "test-user-id",
        "preferred_username": "testuser@chevron.com",
        "name": "Test User",
        "upn": "testuser@chevron.com",
        "groups": ["test-group"],
        "roles": ["test-role"],
        "tid": "test-tenant",
        "exp": 9999999999,  # Far future expiry
        "aud": f"https://ssv-test.azure.chevron.com"
    }
    return jwt.encode(test_payload, "test-key", algorithm="HS256")

# Create test client with mock authentication
client = TestClient(app)
test_token = get_test_token()

# Add auth headers to all requests
client.headers["Authorization"] = f"Bearer {test_token}"

##INFO
## Status Code 200 - Success
## Status Code 422 - BaseModel failure
## Status Code 500 - Code error

def test_app_response():
    # Additional local mock for SQLHelper.execute_sql_query with a custom return value
    mock_sql_helper.execute_sql_query.return_value = pd.DataFrame({"SupplierName": ["Test Supplier"]})
    
    response = client.get("/")
    assert response.status_code == 200
    # Validate that the response contains the expected keys
    json_data = response.json()
    assert "message" in json_data
    assert json_data["message"] == "Hello World"
    # Verify that execute_sql_query was called
    mock_sql_helper.execute_sql_query.assert_called_once()


## Submit Feedback


def test_submit_feedback():
    response = client.post(
        "/submit-feedback",
        json={
            "feedback_rating": 2,
            "feedback_text": "This is a testing feedback",
            "username": "sampleuser@samplecompany.com",
        },
    )
    assert response.status_code == 200
    assert response.json() == ["OK", 200]


def test_submit_feedback_wrong_format():
    response = client.post(
        "/submit-feedback",
        json={
            "feedback_rating": "asc",
            "feedback_text": "This is a testing feedback",
            "username": "sampleuser@samplecompany.com",
        },
    )
    assert response.status_code == 422


def test_submit_feedback_wrong_structure():
    response = client.post(
        "/submit-feedback", json={"feedback_rating": 2, "feedback_test": None}
    )
    assert response.status_code == 422


## Send AI Response Feedback


def test_ai_response_feedback():
    response = client.post(
        "/ai-response-feedback",
        json={
            "analytical_question": "someq",
            "query": "SELECT abc FROM d",
            "username": "sampleuser@samplecompany.com",
            "ai_response_feedback": "good",
        },
    )
    assert response.status_code == 200


def test_ai_response_feedback_bad_response():
    response = client.post(
        "/ai-response-feedback",
        json={
            "analytical_question": "someq",
            "query": "SELECT abc FROM d",
            "username": "sampleuser@samplecompany.com",
            "ai_response_feedback": "dome",
        },
    )
    assert response.status_code == 200


def test_ai_response_feedback_bad_structure():
    response = client.post(
        "/ai-response-feedback",
        json={
            "analytical_question": "someq",
            "query": "SELECT abc FROM d",
            "username": "sampleuser@samplecompany.com",
        },
    )
    assert response.status_code == 422


def test_ai_response_feedback_nonetype():
    response = client.post(
        "/ai-response-feedback",
        json={
            "analytical_question": "someq",
            "query": None,
            "username": "sampleuser@samplecompany.com",
            "ai_response_feedback": "good",
        },
    )
    assert response.status_code == 200

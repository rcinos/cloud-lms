# user-service/tests/test_simple.py
# Simple tests to verify basic functionality

import pytest
import json


class TestBasicFunctionality:
    """Basic tests to verify the application setup."""

    def test_app_creation(self, app):
        """Test that the Flask app is created correctly."""
        assert app is not None
        assert app.config['TESTING'] is True

    def test_database_connection(self, app):
        """Test that database connection works."""
        with app.app_context():
            from app import db
            from sqlalchemy import text
            result = db.session.execute(text("SELECT 1")).scalar()
            assert result == 1

    def test_encryption_setup(self, app):
        """Test that encryption is working."""
        with app.app_context():
            from shared.encryption import encrypt_data, decrypt_data
            test_data = "test encryption"
            encrypted = encrypt_data(test_data)
            decrypted = decrypt_data(encrypted)
            assert decrypted == test_data

    def test_ping_endpoint(self, client):
        """Test ping endpoint."""
        response = client.get('/ping')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['message'] == 'pong'

    def test_users_endpoint_empty(self, client):
        """Test users endpoint with no data."""
        response = client.get('/users')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'users' in data
        assert len(data['users']) == 0

    def test_metrics_endpoint(self, client):
        """Test metrics endpoint."""
        response = client.get('/metrics')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'total_users' in data
        assert 'service' in data
        assert data['service'] == 'user-service'
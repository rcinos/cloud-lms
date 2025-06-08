# course-service/tests/test_simple.py
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

    def test_health_endpoint(self, client):
        """Test basic health endpoint."""
        response = client.get('/health')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'healthy'

    def test_ping_endpoint(self, client):
        """Test ping endpoint."""
        response = client.get('/ping')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['message'] == 'pong'

    def test_courses_endpoint_empty(self, client):
        """Test courses endpoint with no data."""
        response = client.get('/courses')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'courses' in data
        assert len(data['courses']) == 0
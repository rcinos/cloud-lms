# progress-service/tests/test_utils.py
# Tests for utility functions, primarily authentication decorators.

import pytest
import jwt
from app.utils import token_required
from flask import jsonify
import time


class TestTokenRequired:
    """Tests for the @token_required decorator."""

    def test_token_required_valid_token(self, app):
        """Test @token_required with valid token."""
        with app.app_context():
            @token_required
            def test_route(current_user_id):
                return jsonify({'user_id': current_user_id})

            # Create valid token
            payload = {
                'user_id': 123,
                'email': 'test@example.com',
                'user_type': 'student',
                'exp': int(time.time()) + 3600
            }
            token = jwt.encode(payload, app.config['JWT_SECRET'], algorithm='HS256')

            with app.test_request_context('/', headers={'Authorization': f'Bearer {token}'}):
                result = test_route()
                if isinstance(result, tuple):
                    response, status_code = result
                    assert status_code == 200
                    assert response.get_json()['user_id'] == 123
                else:
                    assert result.status_code == 200
                    assert result.get_json()['user_id'] == 123

    def test_token_required_missing_token(self, app):
        """Test @token_required with missing token."""
        with app.app_context():
            @token_required
            def test_route(current_user_id):
                return jsonify({'user_id': current_user_id})

            with app.test_request_context('/'):
                result = test_route()
                if isinstance(result, tuple):
                    response, status_code = result
                    assert status_code == 401
                    assert response.get_json()['code'] == 'TOKEN_MISSING'
                else:
                    assert result.status_code == 401
                    assert result.get_json()['code'] == 'TOKEN_MISSING'

    def test_token_required_expired_token(self, app):
        """Test @token_required with expired token."""
        with app.app_context():
            @token_required
            def test_route(current_user_id):
                return jsonify({'user_id': current_user_id})

            # Create expired token
            payload = {
                'user_id': 123,
                'email': 'test@example.com',
                'user_type': 'student',
                'exp': int(time.time()) - 3600  # Expired 1 hour ago
            }
            token = jwt.encode(payload, app.config['JWT_SECRET'], algorithm='HS256')

            with app.test_request_context('/', headers={'Authorization': f'Bearer {token}'}):
                result = test_route()
                if isinstance(result, tuple):
                    response, status_code = result
                    assert status_code == 401
                    assert response.get_json()['code'] == 'TOKEN_EXPIRED'
                else:
                    assert result.status_code == 401
                    assert result.get_json()['code'] == 'TOKEN_EXPIRED'

    def test_token_required_invalid_token(self, app):
        """Test @token_required with invalid token."""
        with app.app_context():
            @token_required
            def test_route(current_user_id):
                return jsonify({'user_id': current_user_id})

            invalid_token = 'invalid.token.here'

            with app.test_request_context('/', headers={'Authorization': f'Bearer {invalid_token}'}):
                result = test_route()
                if isinstance(result, tuple):
                    response, status_code = result
                    assert status_code == 401
                    assert response.get_json()['code'] == 'TOKEN_INVALID'
                else:
                    assert result.status_code == 401
                    assert result.get_json()['code'] == 'TOKEN_INVALID'

    def test_token_required_no_bearer_prefix(self, app):
        """Test @token_required with token without Bearer prefix."""
        with app.app_context():
            @token_required
            def test_route(current_user_id):
                return jsonify({'user_id': current_user_id})

            # Create valid token
            payload = {
                'user_id': 123,
                'email': 'test@example.com',
                'user_type': 'student',
                'exp': int(time.time()) + 3600
            }
            token = jwt.encode(payload, app.config['JWT_SECRET'], algorithm='HS256')

            # Send token without "Bearer " prefix
            with app.test_request_context('/', headers={'Authorization': token}):
                result = test_route()
                if isinstance(result, tuple):
                    response, status_code = result
                    assert status_code == 200
                    assert response.get_json()['user_id'] == 123
                else:
                    assert result.status_code == 200
                    assert result.get_json()['user_id'] == 123


class TestDecoratorPreservation:
    """Tests to ensure decorators preserve function metadata."""

    def test_token_required_preserves_metadata(self):
        """Test that @token_required preserves function metadata."""

        @token_required
        def test_function(current_user_id):
            """Test function docstring."""
            return "test"

        assert test_function.__name__ == 'test_function'
        assert test_function.__doc__ == 'Test function docstring.'
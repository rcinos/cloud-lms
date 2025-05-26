# course-service/app/utils.py
# This file provides utility functions, primarily Flask decorators for authentication
# and authorization (JWT token validation and role-based access control).

from functools import wraps  # Used to preserve function metadata when using decorators
from flask import request, jsonify, current_app  # Flask components for request handling and config
import jwt  # Library for JSON Web Tokens


def token_required(f):
    """
    Decorator to ensure that a valid JWT token is present in the Authorization header.
    It extracts the user_id from the token and passes it as the first argument to the decorated function.
    """

    @wraps(f)  # Preserves the original function's name and docstring
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')  # Get the Authorization header

        if not token:
            # If no token is provided, return an Unauthorized error.
            return jsonify({'error': 'Token is missing', 'code': 'TOKEN_MISSING'}), 401

        try:
            # Extract the token (remove "Bearer " prefix if present)
            if token.startswith('Bearer '):
                token = token[7:]

            # Decode the JWT token using the application's secret key and algorithm.
            # The JWT_SECRET must be the same as the one used by the User Service to sign tokens.
            data = jwt.decode(token, current_app.config['JWT_SECRET'], algorithms=['HS256'])
            current_user_id = data['user_id']  # Extract user ID from token payload
        except jwt.ExpiredSignatureError:
            # Handle expired tokens.
            return jsonify({'error': 'Token has expired', 'code': 'TOKEN_EXPIRED'}), 401
        except jwt.InvalidTokenError:
            # Handle invalid tokens (e.g., wrong signature, malformed).
            return jsonify({'error': 'Token is invalid', 'code': 'TOKEN_INVALID'}), 401
        except Exception as e:
            # Catch any other unexpected errors during token processing.
            return jsonify({'error': f'Token processing error: {str(e)}', 'code': 'TOKEN_PROCESSING_ERROR'}), 401

        # If token is valid, call the original function with the user ID.
        return f(current_user_id, *args, **kwargs)

    return decorated


def instructor_required(f):
    """
    Decorator to ensure that the authenticated user has 'instructor' privileges.
    This decorator should be used AFTER @token_required if the decorated function needs user_id.
    It extracts user_id from the token and passes it to the decorated function.
    """

    @wraps(f)  # Preserves the original function's name and docstring
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')  # Get the Authorization header

        if not token:
            # If no token is provided, return an Unauthorized error.
            return jsonify({'error': 'Token is missing', 'code': 'TOKEN_MISSING'}), 401

        try:
            # Extract the token (remove "Bearer " prefix if present)
            if token.startswith('Bearer '):
                token = token[7:]

            # Decode the JWT token.
            data = jwt.decode(token, current_app.config['JWT_SECRET'], algorithms=['HS256'])

            # Check if the user_type in the token payload is 'instructor'.
            if data.get('user_type') != 'instructor':
                # If not an instructor, return a Forbidden error.
                return jsonify({'error': 'Instructor privileges required', 'code': 'FORBIDDEN_ACCESS'}), 403

            current_user_id = data['user_id']  # Pass user_id to the decorated function

        except jwt.ExpiredSignatureError:
            # Handle expired tokens.
            return jsonify({'error': 'Token has expired', 'code': 'TOKEN_EXPIRED'}), 401
        except jwt.InvalidTokenError:
            # Handle invalid tokens.
            return jsonify({'error': 'Token is invalid', 'code': 'TOKEN_INVALID'}), 401
        except Exception as e:
            # Catch any other unexpected errors.
            return jsonify({'error': f'Token processing error: {str(e)}', 'code': 'TOKEN_PROCESSING_ERROR'}), 401

        # If token is valid and user is an instructor, call the original function with user_id.
        return f(current_user_id, *args, **kwargs)

    return decorated

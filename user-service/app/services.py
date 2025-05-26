# user-service/app/services.py
# This file contains the business logic for the User Service,
# abstracting database operations and external interactions.

from app import db  # Import the SQLAlchemy instance
from app.models import User, UserProfile, Enrollment  # Import database models
from shared.encryption import encrypt_data  # Utility for data encryption
import jwt  # Library for JSON Web Tokens
import datetime
from flask import current_app  # To access Flask application configuration


class UserService:
    def create_user(self, data: dict) -> User:
        """
        Creates a new user and their profile (if data is provided).
        Raises ValueError if a user with the email already exists.
        """
        # Check if a user with the given email already exists to prevent duplicates.
        existing_user = self.get_user_by_email(data['email'])
        if existing_user:
            raise ValueError('User with this email already exists')

        # Create a new User instance and set encrypted email and hashed password.
        user = User(user_type=data['user_type'])
        user.set_email(data['email'])
        user.set_password(data['password'])

        db.session.add(user)
        db.session.commit()  # Commit to get the user.id for the profile

        # Create a UserProfile if additional profile data is provided in the request.
        if any(key in data for key in ['first_name', 'last_name', 'phone', 'bio']):
            profile = UserProfile(user_id=user.id)  # Link profile to the new user

            # Set encrypted profile fields if present in data
            if 'first_name' in data:
                profile.set_first_name(data['first_name'])
            if 'last_name' in data:
                profile.set_last_name(data['last_name'])
            if 'phone' in data:
                profile.set_phone(data['phone'])
            if 'bio' in data:
                profile.bio = data['bio']

            db.session.add(profile)
            db.session.commit()  # Commit the profile changes

        return user

    def get_user_by_email(self, email: str) -> User | None:
        """
        Retrieves a user by their email.
        The email is encrypted before querying the database to match the stored format.
        """
        encrypted_email = encrypt_data(email)  # Encrypt the input email for lookup
        return User.query.filter_by(email_encrypted=encrypted_email).first()

    def create_enrollment(self, data: dict) -> Enrollment:
        """
        Creates a new enrollment record for a user in a course.
        Raises ValueError if the user is already enrolled or if the user does not exist.
        """
        # Check if the user is already enrolled in the specific course.
        existing = Enrollment.query.filter_by(
            user_id=data['user_id'],
            course_id=data['course_id']
        ).first()

        if existing:
            raise ValueError('User already enrolled in this course')

        # Verify that the user exists before creating an enrollment.
        user = User.query.get(data['user_id'])
        if not user:
            raise ValueError('User not found')

        # Create a new Enrollment instance.
        enrollment = Enrollment(
            user_id=data['user_id'],
            course_id=data['course_id']
        )

        db.session.add(enrollment)
        db.session.commit()  # Commit the new enrollment to the database

        return enrollment


class AuthService:
    def authenticate_user(self, email: str, password: str) -> str | None:
        """
        Authenticates a user with email and password, and returns a JWT token if successful.
        Returns None if authentication fails (invalid credentials or inactive user).
        """
        user = UserService().get_user_by_email(email)  # Use UserService to find the user by email

        # Check if user exists and password is correct.
        if not user or not user.check_password(password):
            return None

        # Check if the user account is active.
        if not user.is_active:
            return None

        # Prepare the payload for the JWT token.
        # Includes user_id, email (decrypted), user_type, and expiration time.
        payload = {
            'user_id': user.id,
            'email': user.get_email(),
            'user_type': user.user_type,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(
                hours=current_app.config['JWT_EXPIRATION_HOURS']  # Token expiration from config
            )
        }

        # Encode the JWT token using the secret key and HS256 algorithm.
        token = jwt.encode(payload, current_app.config['JWT_SECRET'], algorithm='HS256')
        return token

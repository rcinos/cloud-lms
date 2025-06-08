# user-service/tests/test_services.py
# Tests for the service layer business logic in the User Service.

import pytest
from app import db
from app.services import UserService, AuthService
from app.models import User, UserProfile, Enrollment
import jwt


class TestUserService:
    """Tests for the UserService class."""

    def test_create_user_success(self, app):
        """Test creating a user successfully."""
        with app.app_context():
            service = UserService()
            user_data = {
                'email': 'newuser@example.com',
                'password': 'SecurePass123',
                'user_type': 'student',
                'first_name': 'New',
                'last_name': 'User',
                'phone': '555-0123',
                'bio': 'Test user'
            }

            user = service.create_user(user_data)

            assert user.id is not None
            assert user.get_email() == user_data['email']
            assert user.user_type == user_data['user_type']
            assert user.check_password(user_data['password']) is True

            # Verify user was saved to database
            saved_user = User.query.get(user.id)
            assert saved_user is not None
            assert saved_user.get_email() == user_data['email']

            # Verify profile was created
            assert saved_user.user_profile is not None
            assert saved_user.user_profile.get_first_name() == user_data['first_name']
            assert saved_user.user_profile.get_last_name() == user_data['last_name']
            assert saved_user.user_profile.get_phone() == user_data['phone']
            assert saved_user.user_profile.bio == user_data['bio']

    def test_create_user_minimal_data(self, app):
        """Test creating a user with minimal required data."""
        with app.app_context():
            service = UserService()
            user_data = {
                'email': 'minimal@example.com',
                'password': 'MinimalPass123',
                'user_type': 'instructor'
            }

            user = service.create_user(user_data)

            assert user.id is not None
            assert user.get_email() == user_data['email']
            assert user.user_type == user_data['user_type']

            # No profile should be created without additional data
            assert user.user_profile is None

    def test_create_user_partial_profile(self, app):
        """Test creating a user with partial profile data."""
        with app.app_context():
            service = UserService()
            user_data = {
                'email': 'partial@example.com',
                'password': 'PartialPass123',
                'user_type': 'student',
                'first_name': 'Partial',
                'bio': 'Only some profile data'
                # Missing last_name and phone
            }

            user = service.create_user(user_data)

            assert user.id is not None
            assert user.user_profile is not None
            assert user.user_profile.get_first_name() == 'Partial'
            assert user.user_profile.get_last_name() is None
            assert user.user_profile.get_phone() is None
            assert user.user_profile.bio == 'Only some profile data'

    def test_create_duplicate_user(self, app):
        """Test creating a user with duplicate email raises ValueError."""
        with app.app_context():
            service = UserService()
            user_data = {
                'email': 'duplicate@example.com',
                'password': 'DuplicatePass123',
                'user_type': 'student'
            }

            # Create first user
            first_user = service.create_user(user_data)
            assert first_user is not None

            # Try to create duplicate - should raise ValueError
            with pytest.raises(ValueError, match="User with this email already exists"):
                service.create_user(user_data)

    def test_get_user_by_email_success(self, app, sample_user):
        """Test retrieving a user by email."""
        with app.app_context():
            service = UserService()

            # The sample_user fixture already created a user, so we can find it
            found_user = service.get_user_by_email(sample_user.email)

            assert found_user is not None
            assert found_user.id == sample_user.id
            assert found_user.get_email() == sample_user.email

    def test_get_user_by_email_not_found(self, app):
        """Test retrieving a non-existent user by email."""
        with app.app_context():
            service = UserService()

            user = service.get_user_by_email('nonexistent@example.com')

            assert user is None

    def test_create_enrollment_success(self, app, sample_user):
        """Test creating an enrollment successfully."""
        with app.app_context():
            service = UserService()
            enrollment_data = {
                'user_id': sample_user.id,
                'course_id': 102
            }

            enrollment = service.create_enrollment(enrollment_data)

            assert enrollment.id is not None
            assert enrollment.user_id == sample_user.id
            assert enrollment.course_id == 102
            assert enrollment.status == 'active'

            # Verify it was saved to database
            saved_enrollment = Enrollment.query.get(enrollment.id)
            assert saved_enrollment is not None

    def test_create_enrollment_duplicate(self, app, sample_user):
        """Test creating duplicate enrollment raises ValueError."""
        with app.app_context():
            service = UserService()
            enrollment_data = {
                'user_id': sample_user.id,
                'course_id': 103
            }

            # Create first enrollment
            service.create_enrollment(enrollment_data)

            # Try to create duplicate
            with pytest.raises(ValueError, match="User already enrolled in this course"):
                service.create_enrollment(enrollment_data)

    def test_create_enrollment_user_not_found(self, app):
        """Test creating enrollment for non-existent user raises ValueError."""
        with app.app_context():
            service = UserService()
            enrollment_data = {
                'user_id': 999,  # Non-existent user
                'course_id': 104
            }

            with pytest.raises(ValueError, match="User not found"):
                service.create_enrollment(enrollment_data)


class TestAuthService:
    """Tests for the AuthService class."""

    def test_authenticate_user_success(self, app, sample_user):
        """Test successful user authentication."""
        with app.app_context():
            auth_service = AuthService()

            token = auth_service.authenticate_user(sample_user.email, sample_user.password)

            assert token is not None

            # Verify token content
            decoded = jwt.decode(token, app.config['JWT_SECRET'], algorithms=['HS256'])
            assert decoded['user_id'] == sample_user.id
            assert decoded['email'] == sample_user.email
            assert decoded['user_type'] == sample_user.user_type
            assert 'exp' in decoded

    def test_authenticate_user_wrong_password(self, app, sample_user):
        """Test authentication with wrong password."""
        with app.app_context():
            auth_service = AuthService()

            token = auth_service.authenticate_user(sample_user.email, 'WrongPassword')

            assert token is None

    def test_authenticate_user_nonexistent_email(self, app):
        """Test authentication with non-existent email."""
        with app.app_context():
            service = AuthService()

            token = service.authenticate_user('nonexistent@example.com', 'SomePassword')

            assert token is None

    def test_authenticate_inactive_user(self, app, sample_user_data):
        """Test authentication with inactive user."""
        with app.app_context():
            # Create an inactive user directly
            user = User(user_type=sample_user_data['user_type'], is_active=False)
            user.set_email('inactive@example.com')
            user.set_password(sample_user_data['password'])

            db.session.add(user)
            db.session.commit()

            service = AuthService()
            token = service.authenticate_user('inactive@example.com', sample_user_data['password'])

            assert token is None

    def test_token_expiration_time(self, app, sample_user):
        """Test that token has correct expiration time."""
        with app.app_context():
            # Set a specific expiration time for testing
            app.config['JWT_EXPIRATION_HOURS'] = 2

            auth_service = AuthService()
            token = auth_service.authenticate_user(sample_user.email, sample_user.password)

            assert token is not None

            decoded = jwt.decode(token, app.config['JWT_SECRET'], algorithms=['HS256'])

            # Check that expiration is approximately 2 hours from now
            import time
            current_time = int(time.time())
            token_exp = decoded['exp']

            # Should be between 1.9 and 2.1 hours (allowing for test execution time)
            assert 6840 <= token_exp - current_time <= 7560  # 1.9 to 2.1 hours in seconds

    def test_instructor_authentication(self, app, sample_instructor):
        """Test authentication for instructor user type."""
        with app.app_context():
            auth_service = AuthService()

            token = auth_service.authenticate_user(sample_instructor.email, sample_instructor.password)

            assert token is not None

            decoded = jwt.decode(token, app.config['JWT_SECRET'], algorithms=['HS256'])
            assert decoded['user_type'] == 'instructor'
            assert decoded['user_id'] == sample_instructor.id
# user-service/app/models.py
# This file defines the database models for the User Service using Flask-SQLAlchemy.
# It includes models for Users, User Profiles, and Enrollments, with PII data encryption.

from app import db  # Import the SQLAlchemy instance
from datetime import datetime
from shared.encryption import encrypt_data, decrypt_data  # Utilities for data encryption/decryption
import bcrypt  # Library for password hashing


class User(db.Model):
    __tablename__ = 'users'  # Name of the database table

    id = db.Column(db.Integer, primary_key=True)
    # Encrypted email stored as LargeBinary for PII protection. Must be unique.
    email_encrypted = db.Column(db.LargeBinary, nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)  # Hashed password
    user_type = db.Column(db.String(20), nullable=False)  # 'student' or 'instructor'
    is_active = db.Column(db.Boolean, default=True)  # User account status
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # Timestamp of creation
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # Timestamp of last update

    # Relationships:
    # One-to-one relationship with UserProfile. 'uselist=False' indicates one-to-one.
    # 'cascade' ensures profile is deleted if user is deleted.
    user_profile = db.relationship('UserProfile', backref='user', uselist=False, cascade='all, delete-orphan')
    # One-to-many relationship with Enrollment. 'lazy=True' means enrollments are loaded on demand.
    enrollments = db.relationship('Enrollment', backref='user', lazy=True, cascade='all, delete-orphan')

    def set_email(self, email: str):
        """Encrypts and sets the user's email."""
        self.email_encrypted = encrypt_data(email)

    def get_email(self) -> str:
        """Decrypts and returns the user's email."""
        return decrypt_data(self.email_encrypted)

    def set_password(self, password: str):
        """Hashes the plain-text password and sets the password_hash."""
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def check_password(self, password: str) -> bool:
        """Checks a plain-text password against the stored hash."""
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))

    def to_dict(self, include_email=False) -> dict:
        """Converts the User object to a dictionary for API responses."""
        result = {
            'id': self.id,
            'user_type': self.user_type,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

        if include_email:
            result['email'] = self.get_email()  # Include decrypted email if requested

        return result


class UserProfile(db.Model):
    __tablename__ = 'user_profiles'  # Name of the database table

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # Foreign key to the users table
    first_name_encrypted = db.Column(db.LargeBinary)  # Encrypted first name
    last_name_encrypted = db.Column(db.LargeBinary)  # Encrypted last name
    phone_encrypted = db.Column(db.LargeBinary)  # Encrypted phone number
    bio = db.Column(db.Text)  # User's biography (not PII, so not encrypted)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # Timestamp of creation

    def set_first_name(self, first_name: str):
        """Encrypts and sets the user's first name."""
        if first_name:
            self.first_name_encrypted = encrypt_data(first_name)

    def get_first_name(self) -> str | None:
        """Decrypts and returns the user's first name."""
        return decrypt_data(self.first_name_encrypted) if self.first_name_encrypted else None

    def set_last_name(self, last_name: str):
        """Encrypts and sets the user's last name."""
        if last_name:
            self.last_name_encrypted = encrypt_data(last_name)

    def get_last_name(self) -> str | None:
        """Decrypts and returns the user's last name."""
        return decrypt_data(self.last_name_encrypted) if self.last_name_encrypted else None

    def set_phone(self, phone: str):
        """Encrypts and sets the user's phone number."""
        if phone:
            self.phone_encrypted = encrypt_data(phone)

    def get_phone(self) -> str | None:
        """Decrypts and returns the user's phone number."""
        return decrypt_data(self.phone_encrypted) if self.phone_encrypted else None

    def to_dict(self) -> dict:
        """Converts the UserProfile object to a dictionary for API responses."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'first_name': self.get_first_name(),
            'last_name': self.get_last_name(),
            'phone': self.get_phone(),
            'bio': self.bio,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Enrollment(db.Model):
    __tablename__ = 'enrollments'  # Name of the database table

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # Foreign key to the users table
    course_id = db.Column(db.Integer, nullable=False)  # Reference to course service (logical, no direct FK)
    enrollment_date = db.Column(db.DateTime, default=datetime.utcnow)  # Date of enrollment
    status = db.Column(db.String(20), default='active')  # Enrollment status: active, completed, dropped

    def to_dict(self) -> dict:
        """Converts the Enrollment object to a dictionary for API responses."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'course_id': self.course_id,
            'enrollment_date': self.enrollment_date.isoformat() if self.enrollment_date else None,
            'status': self.status
        }

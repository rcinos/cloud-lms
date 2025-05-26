# API Documentation - Online Learning Management System

## Base URLs
- Course Service: `http://localhost:5001` (Dev) / `https://api.olms.yourdomain.com/courses` (Prod)
- User Service: `http://localhost:5002` (Dev) / `https://api.olms.yourdomain.com/users` (Prod)
- Progress Service: `http://localhost:5003` (Dev) / `https://api.olms.yourdomain.com/progress` (Prod)

## Authentication
All protected endpoints require a Bearer token in the Authorization header:
```
Authorization: Bearer <JWT_TOKEN>
```

## Course Service API

### Health and Monitoring Endpoints

#### GET /health
**Description**: Health check endpoint
**Response**: 
```json
{
  "status": "healthy",
  "service": "course-service"
}
```

#### GET /ping
**Description**: Simple ping endpoint
**Response**: 
```json
{
  "message": "pong"
}
```

#### GET /metrics
**Description**: Service metrics endpoint
**Response**: 
```json
{
  "total_courses": 150,
  "total_assessments": 300,
  "service": "course-service"
}
```

### Course Management Endpoints

#### GET /courses
**Description**: Get all courses with pagination
**Parameters**:
- `page` (optional): Page number (default: 1)
- `per_page` (optional): Items per page (default: 10, max: 100)

**Response**: 
```json
{
  "courses": [
    {
      "id": 1,
      "title": "Introduction to Python",
      "description": "Learn Python programming basics",
      "instructor_id": 5,
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-01-20T14:45:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "pages": 15,
    "per_page": 10,
    "total": 150
  }
}
```

#### GET /courses/{course_id}
**Description**: Get specific course by ID
**Parameters**:
- `course_id`: Course identifier

**Response**: 
```json
{
  "id": 1,
  "title": "Introduction to Python",
  "description": "Learn Python programming basics",
  "instructor_id": 5,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-20T14:45:00Z"
}
```

#### POST /courses
**Description**: Create new course (Instructor only)
**Request Body**: 
```json
{
  "title": "Advanced JavaScript",
  "description": "Deep dive into JavaScript concepts",
  "instructor_id": 5
}
```

**Response**: 
```json
{
  "id": 2,
  "title": "Advanced JavaScript",
  "description": "Deep dive into JavaScript concepts",
  "instructor_id": 5,
  "created_at": "2024-01-25T09:15:00Z",
  "updated_at": "2024-01-25T09:15:00Z"
}
```

#### GET /courses/{course_id}/modules
**Description**: Get all modules for a course
**Response**: 
```json
[
  {
    "id": 1,
    "course_id": 1,
    "title": "Variables and Data Types",
    "content": "Introduction to Python variables...",
    "order_index": 1,
    "created_at": "2024-01-15T11:00:00Z"
  }
]
```

#### GET /courses/{course_id}/assessments
**Description**: Get all assessments for a course
**Response**: 
```json
[
  {
    "id": 1,
    "course_id": 1,
    "title": "Python Basics Quiz",
    "description": "Test your knowledge of Python fundamentals",
    "max_score": 100,
    "created_at": "2024-01-16T10:00:00Z"
  }
]
```

## User Service API

### Health and Monitoring Endpoints

#### GET /health
**Description**: Health check endpoint
**Response**: 
```json
{
  "status": "healthy",
  "service": "user-service"
}
```

#### GET /metrics
**Description**: Service metrics endpoint
**Response**: 
```json
{
  "total_users": 1250,
  "total_students": 1100,
  "total_instructors": 150,
  "total_enrollments": 3500,
  "service": "user-service"
}
```

### Authentication Endpoints

#### POST /auth/register
**Description**: Register new user
**Request Body**: 
```json
{
  "email": "student@example.com",
  "password": "securePassword123",
  "user_type": "student",
  "first_name": "John",
  "last_name": "Doe",
  "phone": "+1234567890"
}
```

**Response**: 
```json
{
  "id": 100,
  "user_type": "student",
  "is_active": true,
  "created_at": "2024-01-25T10:30:00Z",
  "updated_at": "2024-01-25T10:30:00Z"
}
```

#### POST /auth/login
**Description**: User login
**Request Body**: 
```json
{
  "email": "student@example.com",
  "password": "securePassword123"
}
```

**Response**: 
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

### User Management Endpoints

#### GET /users
**Description**: Get all users with pagination (Admin only)
**Parameters**:
- `page` (optional): Page number
- `per_page` (optional): Items per page
- `type` (optional): Filter by user type (student/instructor)

**Response**: 
```json
{
  "users": [
    {
      "id": 100,
      "user_type": "student",
      "is_active": true,
      "created_at": "2024-01-25T10:30:00Z",
      "updated_at": "2024-01-25T10:30:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "pages": 125,
    "per_page": 10,
    "total": 1250
  }
}
```

#### GET /users/{user_id}
**Description**: Get specific user by ID
**Response**: 
```json
{
  "id": 100,
  "email": "student@example.com",
  "user_type": "student",
  "is_active": true,
  "created_at": "2024-01-25T10:30:00Z",
  "updated_at": "2024-01-25T10:30:00Z",
  "profile": {
    "id": 100,
    "user_id": 100,
    "first_name": "John",
    "last_name": "Doe",
    "phone": "+1234567890",
    "bio": null,
    "created_at": "2024-01-25T10:30:00Z"
  }
}
```

### Enrollment Endpoints

#### POST /enrollments
**Description**: Create new enrollment
**Request Body**: 
```json
{
  "user_id": 100,
  "course_id": 1
}
```

**Response**: 
```json
{
  "id": 500,
  "user_id": 100,
  "course_id": 1,
  "enrollment_date": "2024-01-25T11:00:00Z",
  "status": "active"
}
```

#### GET /users/{user_id}/enrollments
**Description**: Get all enrollments for a user
**Response**: 
```json
[
  {
    "id": 500,
    "user_id": 100,
    "course_id": 1,
    "enrollment_date": "2024-01-25T11:00:00Z",
    "status": "active"
  }
]
```

## Progress Service API

### Health and Monitoring Endpoints

#### GET /health
**Description**: Health check endpoint
**Response**: 
```json
{
  "status": "healthy",
  "service": "progress-service"
}
```

#### GET /metrics
**Description**: Service metrics endpoint
**Response**: 
```json
{
  "total_progress_records": 3500,
  "total_assessments_completed": 8750,
  "total_certificates_issued": 1200,
  "average_completion_rate": 67.5,
  "service": "progress-service"
}
```

### Progress Tracking Endpoints

#### GET /progress
**Description**: Get all progress records with pagination
**Parameters**:
- `page` (optional): Page number
- `per_page` (optional): Items per page

**Response**: 
```json
{
  "progress": [
    {
      "id": 1000,
      "user_id": 100,
      "course_id": 1,
      "completion_percentage": 75.5,
      "last_accessed": "2024-01-25T14:30:00Z",
      "total_time_spent": 450,
      "created_at": "2024-01-20T10:00:00Z",
      "updated_at": "2024-01-25T14:30:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "pages": 350,
    "per_page": 10,
    "total": 3500
  }
}
```

#### GET /progress/{user_id}/{course_id}
**Description**: Get progress for specific user and course
**Response**: 
```json
{
  "id": 1000,
  "user_id": 100,
  "course_id": 1,
  "completion_percentage": 75.5,
  "last_accessed": "2024-01-25T14:30:00Z",
  "total_time_spent": 450,
  "created_at": "2024-01-20T10:00:00Z",
  "updated_at": "2024-01-25T14:30:00Z",
  "assessment_results": [
    {
      "id": 200,
      "user_id": 100,
      "assessment_id": 1,
      "score": 85,
      "max_score": 100,
      "percentage_score": 85.0,
      "attempt_number": 1,
      "completed_at": "2024-01-23T16:45:00Z",
      "time_taken": 25,
      "progress_id": 1000
    }
  ]
}
```

#### POST /progress
**Description**: Update or create progress record
**Request Body**: 
```json
{
  "user_id": 100,
  "course_id": 1,
  "completion_percentage": 80.0,
  "time_spent": 30
}
```

**Response**: 
```json
{
  "id": 1000,
  "user_id": 100,
  "course_id": 1,
  "completion_percentage": 80.0,
  "last_accessed": "2024-01-25T15:00:00Z",
  "total_time_spent": 480,
  "created_at": "2024-01-20T10:00:00Z",
  "updated_at": "2024-01-25T15:00:00Z"
}
```

### Assessment Endpoints

#### POST /assessments/results
**Description**: Record assessment result
**Request Body**: 
```json
{
  "user_id": 100,
  "assessment_id": 1,
  "score": 92,
  "max_score": 100,
  "time_taken": 28,
  "course_id": 1
}
```

**Response**: 
```json
{
  "id": 201,
  "user_id": 100,
  "assessment_id": 1,
  "score": 92,
  "max_score": 100,
  "percentage_score": 92.0,
  "attempt_number": 2,
  "completed_at": "2024-01-25T16:00:00Z",
  "time_taken": 28,
  "progress_id": 1000
}
```

### Analytics Endpoints

#### GET /analytics/user/{user_id}
**Description**: Get comprehensive analytics for a user
**Response**: 
```json
{
  "user_id": 100,
  "total_courses_enrolled": 5,
  "completed_courses": 3,
  "average_completion_rate": 78.4,
  "total_time_spent_minutes": 2250,
  "total_assessments_taken": 12,
  "average_assessment_score": 87.5,
  "certificates_earned": 3,
  "completion_rate_percentage": 60.0
}
```

#### GET /analytics/course/{course_id}
**Description**: Get comprehensive analytics for a course
**Response**: 
```json
{
  "course_id": 1,
  "total_enrollments": 450,
  "completed_students": 280,
  "completion_rate_percentage": 62.2,
  "average_progress_percentage": 73.5,
  "total_time_spent_minutes": 112500,
  "average_time_per_student": 250.0,
  "certificates_issued": 280,
  "progress_distribution": {
    "0-25%": 45,
    "25-50%": 65,
    "50-75%": 85,
    "75-100%": 255
  }
}
```

### Certificate Endpoints

#### POST /certificates
**Description**: Issue completion certificate
**Request Body**: 
```json
{
  "user_id": 100,
  "course_id": 1,
  "certificate_url": "https://certificates.olms.com/cert_100_1.pdf"
}
```

**Response**: 
```json
{
  "id": 300,
  "user_id": 100,
  "course_id": 1,
  "certificate_url": "https://certificates.olms.com/cert_100_1.pdf",
  "issued_at": "2024-01-25T17:00:00Z",
  "final_score": 89.5,
  "is_valid": true
}
```

#### GET /certificates/user/{user_id}
**Description**: Get all certificates for a user
**Response**: 
```json
[
  {
    "id": 300,
    "user_id": 100,
    "course_id": 1,
    "certificate_url": "https://certificates.olms.com/cert_100_1.pdf",
    "issued_at": "2024-01-25T17:00:00Z",
    "final_score": 89.5,
    "is_valid": true
  }
]
```

## Error Responses

All services return consistent error responses:

```json
{
  "error": "Error message description",
  "code": "ERROR_CODE",
  "timestamp": "2024-01-25T18:00:00Z"
}
```

### HTTP Status Codes
- `200` - Success
- `201` - Created
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `500` - Internal Server Error

## Rate Limiting
All APIs implement rate limiting:
- Authenticated users: 1000 requests per hour
- Unauthenticated users: 100 requests per hour

## Data Formats
- All timestamps are in ISO 8601 format (UTC)
- All numeric IDs are integers
- Encrypted fields are returned as strings when decrypted
- Pagination follows standard format with page, per_page, total, and pages fields
# course-service/Dockerfile
# Dockerfile for building the Course Service application image.

# Use a lightweight Python base image
FROM python:3.11-slim-buster

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install Python dependencies
# Use --no-cache-dir to avoid storing cache data, reducing image size
# Use --upgrade pip to ensure pip is up-to-date
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Copy the application code into the container
# The /app directory in the container will contain:
# /app/app/ (Flask app package)
# /app/shared/ (shared utilities)
# /app/app.py (main entry point)
# /app/config.py (configuration)
# /app/requirements.txt (already copied and used)
COPY . .

# Set environment variables for Flask
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV PORT=5001

# Expose the port the app runs on
EXPOSE 5001

# Command to run the application using Gunicorn (recommended for production)
# -w: number of worker processes
# -b: bind to all interfaces on the specified port
# app: The Flask application instance (from app.py)
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5001", "app:app"]

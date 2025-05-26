# user-service/app.py
# This is the main entry point for the User Service Flask application.
# It initializes the Flask app and runs it.

import os
from app import create_app # Import the create_app function from the app package

# Create the Flask application instance
app = create_app()

if __name__ == '__main__':
    # Run the Flask development server.
    # In a production environment, a WSGI server like Gunicorn would be used.
    # The port is fetched from environment variables, defaulting to 5002.
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5002)), debug=True)

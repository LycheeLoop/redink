# Use the official Python image
FROM python:3.9-slim

# Install PostgreSQL development dependencies and build tools
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*  # Clean up to reduce image size

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements.txt to the working directory
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Set environment variables for Flask
ENV FLASK_APP=main.py
ENV FLASK_RUN_HOST=0.0.0.0

# Expose a dynamic port (Heroku assigns a port, so don't hardcode it)
EXPOSE 8000

# Use Gunicorn and bind to Heroku's dynamically assigned port
CMD ["/bin/bash", "-c", "gunicorn main:app –bind 0.0.0.0:$PORT"]
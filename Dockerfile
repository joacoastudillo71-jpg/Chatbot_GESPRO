# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working circle
WORKDIR /app

# Install system dependencies
# build-essential for compiling some python packages
# curl for health checks or debugging
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
# Assuming requirements.txt exists. If not, we might need to create it or COPY setup.py if used.
# For now, I'll copy the whole source and install from there or assume pip install.
# Let's try to copy requirements.txt if it exists, otherwise we'll install manually or copy .
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the current directory contents into the container at /app
COPY . .

# Expose port 8000 for the app
EXPOSE 8000

# Define environment variable
ENV PYTHONUNBUFFERED=1

# Run the application
CMD ["sh", "-c", "uvicorn src.voice.server:app --host 0.0.0.0 --port ${PORT}"]

# Use official Python 3.12 slim image for minimal container size
FROM python:3.12-slim

# Set system env variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

# Set the working directory in container
WORKDIR /app

# Install system dependencies if required for compiling certain libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY requirements.txt /app/

# Install the Python dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy all source files to the working directory
COPY . /app/

# Expose port 8000 for the FastAPI server
EXPOSE 8000

# Run Uvicorn server on container startup
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# Use a base image with Python and Tesseract pre-installed
FROM python:3.12-slim

# Install system dependencies for Tesseract and other tools
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    libtesseract-dev \
    libreoffice \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Expose the port (default for FastAPI is 8000, but adjust if needed)
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "app.process:app", "--host", "0.0.0.0", "--port", "8000"]
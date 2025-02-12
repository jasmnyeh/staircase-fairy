# Use Python base image
FROM python:3.9

# Set the working directory
WORKDIR /app

# Copy requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Set the environment variable for Flask
ENV FLASK_APP=app.py

# Expose the port for Flask
EXPOSE 8080

# Run the application
CMD ["python", "app.py"]

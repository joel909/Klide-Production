# syntax=docker/dockerfile:1
FROM python:3.8-slim-buster

# Set the working directory to /python-docker/api
WORKDIR /klide-production/api

# Copy the requirements file into the container
COPY requirements.txt requirements.txt

# Install the dependencies
RUN pip3 install -r requirements.txt

# Copy the rest of the application code into the container
COPY . .

# Run the application with Gunicorn
CMD ["gunicorn", "-w", "3", "-b", "0.0.0.0:5000", "api.app:app"]


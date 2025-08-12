FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY pyproject.toml ./
RUN pip install .

# Copy source code
COPY file_filter_action.py ./

# Set executable permission
RUN chmod +x file_filter_action.py

# Set the entrypoint
ENTRYPOINT ["python", "/app/file_filter_action.py"]

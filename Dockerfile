FROM python:3.11-slim

# Prevent Python from buffering outputs
ENV PYTHONUNBUFFERED=1

WORKDIR /code

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Expose port (Hugging Face Spaces expects containers to listen on port 7860)
EXPOSE 7860

# Run Streamlit, binding to port 7860
CMD ["streamlit", "run", "sandbox/app.py", "--server.port=7860", "--server.address=0.0.0.0"]

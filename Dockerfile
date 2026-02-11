FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Copy dependency files first for better caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Expose the port
EXPOSE 6000

# Run the app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "6000"]
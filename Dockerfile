# Use official Python image
FROM python:3.9

# Set the working directory inside the container
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the app
COPY . .

# Expose FastAPI port
EXPOSE 8000

# ✅ Update Uvicorn command to point to `app.main`
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

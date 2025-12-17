FROM python:3.13-slim

# Environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY Pipfile Pipfile.lock ./
RUN pip install --upgrade pip && \
    pip install pipenv && \
    pipenv install --system --deploy

# Copy project
COPY . .

# Expose port
EXPOSE 8000

# Start Django
CMD ["gunicorn", "agriculture_sys_project.wsgi:application", "--bind", "0.0.0.0:8000"]

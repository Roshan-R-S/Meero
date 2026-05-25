FROM python:3.10-slim

WORKDIR /app

# Install system deps for optional packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy lightweight test requirements (used to keep image small)
COPY requirements-test.txt ./requirements-test.txt
RUN pip install --no-cache-dir -r requirements-test.txt

# Copy app
COPY . /app

EXPOSE 8000

ENV PYTHONUNBUFFERED=1

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]

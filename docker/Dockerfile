FROM python:3.10-slim-bullseye

# Install system dependencies for pdfkit and reportlab
RUN apt-get update && apt-get install -y \
    wkhtmltopdf \
    libpango-1.0-0 \
    libharfbuzz0b \
    libpangoft2-1.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create directory for logs and documents
RUN mkdir -p logs /Czentrix/apps/wonder_homes_loan_bot/documents

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# Wonder Home Loan Bot

Wonder Home Loan Bot is a high-performance, production-grade FastAPI application designed to automate home loan processing through WhatsApp. It replaces the legacy monolithic system with a scalable, modular architecture.

## 🚀 Key Features

- **WhatsApp Integration**: Automated chat flows for lead generation and loan application.
- **Asynchronous Processing**: Background tasks using Celery and Redis for sending messages and generating reports.
- **External API Integrations**: Seamlessly connects with OTP services, Loan Management Systems (LMS), and credit bureaus (TU/CIBIL).
- **State Management**: Robust chat state tracking using MongoDB.
- **Security**: Secure handling of user data and API credentials.
- **Performance**: Low-latency responses with FastAPI and optimized database interactions.

## 📂 Project Structure

```text
wonder_home/
├── app/
│   ├── api/            # API endpoints (v1)
│   ├── core/           # Configuration and security settings
│   ├── db/             # Database connection managers (Mongo, Redis)
│   ├── services/       # Core business logic (ChatManager, LoanService)
│   ├── tasks/          # Celery background tasks (WhatsApp, PDF)
│   ├── utils/          # Logging and helper utilities
│   └── main.py         # FastAPI application entry point
├── docker/             # Dockerization files
├── docker-compose.yml  # Multi-container orchestration
├── requirements.txt    # Python dependencies
└── main.py             # Legacy monolithic entry point (for reference)
```

## 🛠️ API Documentation

The API follows a modular structure under the `/api/v1` prefix.

### 1. Chat Services
#### WhatsApp Webhook
Processes incoming messages from WhatsApp.
- **URL**: `POST /api/v1/chat/webhook`
- **Curl Example**:
  ```bash
  curl -X POST "http://localhost:8000/api/v1/chat/webhook" \
       -H "Content-Type: application/json" \
       -d '{"wa_numer": "919876543210", "message": "Hi", "extraParms": "{\"identifier\": \"user123\"}"}'
  ```

#### System Status
Check if the bot services are active.
- **URL**: `GET /api/v1/chat/status`
- **Curl Example**:
  ```bash
  curl -X GET "http://localhost:8000/api/v1/chat/status"
  ```

### 2. User Services
#### Check Existing User
Verify if a mobile number is already registered in the system.
- **URL**: `POST /api/v1/user/exist-number`
- **Curl Example**:
  ```bash
  curl -X POST "http://localhost:8000/api/v1/user/exist-number" \
       -H "Content-Type: application/json" \
       -d '{"mobile": "9876543210"}'
  ```

### 3. Payment Services
#### Payment Callback
Receive updates from payment gateways.
- **URL**: `POST /api/v1/payment/callback`
- **Curl Example**:
  ```bash
  curl -X POST "http://localhost:8000/api/v1/payment/callback" \
       -H "Content-Type: application/json" \
       -d '{"mobile": "9876543210", "message": "Payment Successful"}'
  ```

#### Get Payment Message
Retrieve the latest payment status for a user.
- **URL**: `GET /api/v1/payment/message/{mobile}`
- **Curl Example**:
  ```bash
  curl -X GET "http://localhost:8000/api/v1/payment/message/9876543210"
  ```

### 4. Download Services
#### CIBIL Report Download
Download the generated CIBIL report PDF.
- **URL**: `GET /api/v1/download/cibil?file=report.pdf`
- **Curl Example**:
  ```bash
  curl -X GET "http://localhost:8000/api/v1/download/cibil?file=report_9876543210.pdf" --output report.pdf
  ```

## ⚙️ Setup & Installation

### Prerequisites
- Docker & Docker Compose
- Python 3.9+ (for local development)
- MongoDB & Redis

### Local Setup
1. Clone the repository.
2. Create a `.env` file based on `app/core/config.py`.
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the application:
   ```bash
   python -m app.main
   ```

### Docker Deployment
The easiest way to run the entire stack (API, Workers, Redis, DB):
```bash
docker-compose up --build -d
```

## 📈 Monitoring & Logs
Logs are handled by the custom logger in `app/utils/logger.py` and can be found in the standard output or configured log files. Celery tasks can be monitored using tools like Flower.

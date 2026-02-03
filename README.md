# Zeya - WhatsApp AI Antenatal Education Chatbot

An AI-powered WhatsApp chatbot providing personalized antenatal education to pregnant women in Migori County, Kenya. Built for a research study comparing chatbot-based education against standard SMS reminders.

## Features

- **AI-Powered Responses**: Uses Google Gemini to provide accurate maternal health information based on WHO and Kenya Ministry of Health guidelines
- **Danger Sign Detection**: Automatically detects 8 categories of obstetric emergencies in both English and Swahili, triggering immediate emergency responses with local hospital contacts
- **Multilingual Support**: Responds in English or Swahili based on user preference
- **Gestational Age Tracking**: Provides trimester-specific advice based on pregnancy stage
- **Admin Dashboard**: React-based dashboard for monitoring users, conversations, and danger sign alerts
- **Data Export**: Export conversation and engagement data to CSV for research analysis

## Tech Stack

**Backend**
- Python 3.11 / FastAPI
- PostgreSQL 15 (database)
- Redis 7 (conversation history cache)
- Google Gemini AI (gemini-2.0-flash-exp)
- WhatsApp Cloud API

**Frontend**
- React 18 / Vite
- TailwindCSS
- Recharts (analytics)

**Infrastructure**
- Docker / Docker Compose
- Nginx (frontend serving)

## Quick Start

### Prerequisites

- Docker and Docker Compose
- ngrok (for WhatsApp webhook)
- WhatsApp Business API credentials
- Google Gemini API key

### Installation

1. Clone the repository:
```bash
git clone https://github.com/Stella-Achar-Oiro/zeya.git
cd zeya
```

2. Create environment file:
```bash
cp backend/.env.example backend/.env
```

3. Edit `backend/.env` with your credentials:
```
GEMINI_API_KEY=your_gemini_api_key
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id
WHATSAPP_ACCESS_TOKEN=your_access_token
WHATSAPP_VERIFY_TOKEN=your_verify_token
```

4. Start the application:
```bash
make up
make migrate
```

5. Access the services:
- Backend API: http://localhost:8001/docs
- Frontend Dashboard: http://localhost:3000

### Available Commands

Run `make help` to see all available commands:

```
make up        - Start all services
make down      - Stop all services
make restart   - Restart backend service
make logs      - View backend logs
make migrate   - Run database migrations
make test      - Run all tests
make test-cov  - Run tests with coverage
make reset     - Clean reset (removes data)
make ngrok     - Start ngrok tunnel
make shell     - Open backend shell
make db-shell  - Open PostgreSQL shell
```

## WhatsApp Integration

1. Start ngrok tunnel:
```bash
make ngrok
```

2. Configure webhook in Meta Developer Console:
   - Callback URL: `https://<ngrok-url>/api/v1/webhook`
   - Verify Token: Use the value from your `.env` file
   - Subscribe to: `messages`

See [WHATSAPP_SETUP.md](WHATSAPP_SETUP.md) for detailed configuration instructions.

## Project Structure

```
zeya/
├── backend/
│   ├── app/
│   │   ├── api/endpoints/     # API route handlers
│   │   ├── core/              # Config, database, security
│   │   ├── models/            # SQLAlchemy models
│   │   ├── schemas/           # Pydantic schemas
│   │   └── services/          # Business logic
│   │       ├── ai_engine.py           # Gemini AI integration
│   │       ├── conversation_handler.py # Message orchestration
│   │       ├── danger_signs.py        # Emergency detection
│   │       ├── whatsapp.py            # WhatsApp API client
│   │       └── ...
│   ├── alembic/               # Database migrations
│   └── tests/                 # Unit and integration tests
├── frontend/
│   └── src/
│       ├── pages/             # Dashboard pages
│       ├── components/        # React components
│       └── services/          # API client
├── docker-compose.yml
├── Makefile
└── CLAUDE.md                  # AI assistant guidance
```

## How It Works

1. **User Registration**: New users go through a 3-step registration flow:
   - Consent to participate in the study
   - Provide their name
   - Enter gestational age (weeks pregnant)

2. **Message Processing**: For registered users, each message is:
   - Scanned for danger sign keywords (8 categories, English + Swahili)
   - If danger signs detected: Immediate emergency response with hospital contacts
   - If normal: AI-generated response with gestational age context

3. **Danger Sign Categories**:
   - Bleeding
   - Severe headache / blurred vision
   - High fever / chills
   - Reduced fetal movement
   - Severe abdominal pain
   - Water breaking
   - Convulsions / fainting
   - Severe swelling

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/v1/health` | Health check |
| `GET/POST /api/v1/webhook` | WhatsApp webhook |
| `POST /api/v1/auth/login` | Admin login |
| `GET /api/v1/users` | List users (protected) |
| `GET /api/v1/conversations` | List conversations (protected) |
| `GET /api/v1/analytics/dashboard` | Dashboard stats (protected) |
| `GET /api/v1/analytics/export` | Export data (protected) |

## Testing

```bash
# Run all tests
make test

# Run with coverage report
make test-cov

# Run specific test file
docker-compose exec backend pytest tests/unit/test_danger_signs.py -v
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `GEMINI_API_KEY` | Google Gemini API key |
| `GEMINI_MODEL` | Gemini model (default: gemini-2.0-flash-exp) |
| `WHATSAPP_PHONE_NUMBER_ID` | WhatsApp Business phone number ID |
| `WHATSAPP_ACCESS_TOKEN` | WhatsApp API access token |
| `WHATSAPP_VERIFY_TOKEN` | Webhook verification token |
| `DATABASE_URL` | PostgreSQL connection string |
| `REDIS_URL` | Redis connection string |
| `JWT_SECRET_KEY` | Secret key for JWT tokens |

## License

This project is part of a research study on maternal health education in Kenya.

## Author

Stella Achar Oiro

# FastAPI Authentication System

A production-ready JWT-based authentication system with access & refresh tokens, built with FastAPI, SQLAlchemy, and bcrypt.

## Features

✅ **User Authentication**
- User registration with email validation
- Secure login with bcrypt password hashing
- JWT-based access tokens (30 min expiry)
- Long-lived refresh tokens (7 days expiry)
- Token revocation on logout

✅ **Password Management**
- Strong password requirements (8+ chars, uppercase, digit)
- Change password for authenticated users
- Forgot password with email reset links
- Password reset with token validation

✅ **Security**
- Rate limiting on login (5 attempts/minute) and password endpoints
- Secure password hashing with bcrypt
- JWT with type enforcement (access vs refresh)
- CORS protection with configurable origins
- Email case-insensitive user handling
- Invalid token detection and revocation

✅ **Production Ready**
- Comprehensive logging
- Error handling with proper HTTP status codes
- Database abstraction (SQLite for dev, PostgreSQL for production)
- Environment-based configuration
- Full test coverage with pytest
- Type hints throughout

## Quick Start

### 1. Clone & Setup

```bash
# Clone repository
git clone <repo-url>
cd auth_system

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy example configuration
cp .env.example .env

# Generate secure JWT secret
python -c "import secrets; print(secrets.token_hex(32))"

# Edit .env and add the generated secret to JWT_SECRET_KEY
```

### 3. Run Application

```bash
# Start development server (with auto-reload)
python run.py

# Or use uvicorn directly
uvicorn app.main:app --reload
```

Access API docs at: **`http://localhost:8000/docs`**

## API Usage Examples

### Register New User

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123"
  }'
```

### Login

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123"
  }'

# Response:
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer"
}
```

### Get Current User (Authenticated)

```bash
curl -X GET http://localhost:8000/auth/me \
  -H "Authorization: Bearer <access_token>"
```

### Refresh Access Token

```bash
curl -X POST http://localhost:8000/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "<refresh_token>"}'
```

### Change Password

```bash
curl -X POST http://localhost:8000/auth/change-password \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "current_password": "SecurePass123",
    "new_password": "NewPass456"
  }'
```

### Request Password Reset

```bash
curl -X POST http://localhost:8000/auth/forgot-password \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com"}'
```

### Reset Password

```bash
curl -X POST http://localhost:8000/auth/reset-password \
  -H "Content-Type: application/json" \
  -d '{
    "token": "<reset_token_from_email>",
    "new_password": "NewPass789"
  }'
```

### Logout

```bash
curl -X POST http://localhost:8000/auth/logout \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "<refresh_token>"}'
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app tests/

# Run specific test file
pytest tests/test_auth.py -v
```

## Project Structure

```
auth_system/
├── app/
│   ├── main.py           # FastAPI app & middleware setup
│   ├── models.py         # Database models (User, RefreshToken, PasswordResetToken)
│   ├── schemas.py        # Pydantic request/response schemas
│   ├── database.py       # Database connection & session management
│   ├── security.py       # Password hashing utilities
│   ├── jwt_utils.py      # JWT token creation & validation
│   ├── dependencies.py   # Authentication dependency injection
│   ├── routers.py        # API endpoints
│   ├── rate_limit.py     # Rate limiting configuration
│   └── logging_config.py # Logging setup
├── tests/
│   ├── conftest.py       # Pytest fixtures and test database setup
│   └── test_auth.py      # Comprehensive authentication tests
├── .env                  # Environment variables (DO NOT COMMIT)
├── .env.example          # Example configuration
├── requirements.txt      # Python dependencies
├── pytest.ini            # Pytest configuration
├── run.py                # Application entry point
├── README.md             # This file
└── DEVELOPMENT.md        # Developer setup guide
```

## Configuration

See `.env.example` for all available configuration options:

| Option | Default | Description |
|--------|---------|-------------|
| `JWT_SECRET_KEY` | Required | Secret for JWT signing |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 30 | Access token lifetime |
| `REFRESH_TOKEN_EXPIRE_DAYS` | 7 | Refresh token lifetime |
| `DATABASE_URL` | sqlite:///./auth.db | Database connection string |
| `ALLOWED_ORIGINS` | localhost:3000,8000 | CORS allowed origins |

For production, set `DATABASE_URL` to a PostgreSQL connection string:
```
postgresql://user:password@host:5432/database_name
```

## Security Considerations

🔒 **What's Protected:**
- Passwords hashed with bcrypt (never stored in plain text)
- JWT tokens with type enforcement
- Refresh tokens tracked in database (can be revoked)
- Rate limiting prevents brute force attacks
- Email validation prevents invalid accounts
- Case-insensitive email matching prevents duplicates

⚠️ **To Implement Before Production:**
- Email verification on registration
- Email sending for password reset links
- Two-factor authentication (2FA/TOTP)
- HTTPS/TLS encryption
- API key authentication for service-to-service
- Audit logging for compliance
- Database backups and recovery procedures

## Database

### Development (SQLite)
Default and recommended for local development:
```
DATABASE_URL=sqlite:///./auth.db
```

### Production (PostgreSQL)
For production deployments:
```
DATABASE_URL=postgresql://user:pass@localhost/auth_db
```

Install driver: `pip install psycopg2-binary`

## Deployment

### Using Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
docker build -t auth-api .
docker run -p 8000:8000 --env-file .env auth-api
```

### Using Gunicorn (Production ASGI)

```bash
pip install gunicorn
gunicorn app.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker
```

## Troubleshooting

**"JWT_SECRET_KEY not set" error:**
```bash
python -c "import secrets; print(secrets.token_hex(32))"
# Copy output and add to .env as JWT_SECRET_KEY=<value>
```

**Database locked error (SQLite):**
- Close other connections or switch to PostgreSQL for production

**Import errors:**
```bash
pip install -r requirements.txt
```

**Tests failing:**
```bash
# Ensure pytest is installed
pip install pytest pytest-asyncio
```

## Contributing

1. Create a feature branch
2. Make your changes with test coverage
3. Run `pytest` to ensure all tests pass
4. Submit a pull request

## License

MIT License - See LICENSE file for details

## Support

For issues and questions:
- Check [DEVELOPMENT.md](DEVELOPMENT.md) for detailed setup
- Review test cases in `tests/test_auth.py`
- Check API docs at `http://localhost:8000/docs`



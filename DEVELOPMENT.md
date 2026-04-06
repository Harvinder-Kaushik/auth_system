# Development Guide

## Setup Instructions

### 1. Create Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
# Copy the example file
cp .env.example .env

# Generate a secure JWT secret
python -c "import secrets; print(secrets.token_hex(32))"

# Update .env with your values
```

### 4. Run the Application

```bash
# Development mode (with auto-reload)
python run.py

# Or using uvicorn directly
uvicorn app.main:app --reload
```

The API will be available at: `http://localhost:8000`

**API Documentation:** `http://localhost:8000/docs`

---

## Database Configuration

### Development (SQLite)

By default, the app uses SQLite which is great for local development:

```env
DATABASE_URL=sqlite:///./auth.db
```

Database file will be created automatically as `auth.db` in the project root.

### Production (PostgreSQL)

For production deployment, use PostgreSQL:

```bash
# Install PostgreSQL driver
pip install psycopg2-binary
```

```env
DATABASE_URL=postgresql://username:password@localhost/auth_db
```

**Connect string format:** `postgresql://[user[:password]@][netloc][:port][/dbname][?param1=value1&...]`

---

## Running Tests

### Run All Tests

```bash
pytest
```

### Run Specific Test File

```bash
pytest tests/test_auth.py
```

### Run Specific Test Class

```bash
pytest tests/test_auth.py::TestLogin
```

### Run Specific Test Function

```bash
pytest tests/test_auth.py::TestLogin::test_login_success
```

### Run with Coverage Report

```bash
pytest --cov=app tests/
```

### Run in Verbose Mode

```bash
pytest -v
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `JWT_SECRET_KEY` | (required) | Secret key for JWT signing. Generate with `secrets.token_hex(32)` |
| `JWT_ALGORITHM` | HS256 | JWT signing algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 30 | Access token expiration in minutes |
| `REFRESH_TOKEN_EXPIRE_DAYS` | 7 | Refresh token expiration in days |
| `DATABASE_URL` | sqlite:///./auth.db | Database connection string |
| `ALLOWED_ORIGINS` | http://localhost:3000,http://localhost:8000 | CORS allowed origins (comma-separated) |
| `SMTP_SERVER` | smtp.gmail.com | Email server for password reset emails |
| `SMTP_PORT` | 587 | Email server port |
| `SMTP_USERNAME` | (optional) | Email account username |
| `SMTP_PASSWORD` | (optional) | Email account password/app-specific password |
| `SENDER_EMAIL` | (optional) | Sender email for password reset emails |
| `ENVIRONMENT` | development | deployment environment (development/production) |
| `DEBUG` | true | Enable debug mode |

---

## API Endpoints

### Authentication

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|----------------|
| POST | `/auth/register` | Register new user | No |
| POST | `/auth/login` | Login and get tokens | No |
| GET | `/auth/me` | Get current user info | Yes |
| POST | `/auth/logout` | Logout (revoke refresh token) | No |
| POST | `/auth/refresh` | Refresh access token | No |
| POST | `/auth/change-password` | Change password | Yes |
| POST | `/auth/forgot-password` | Request password reset | No |
| POST | `/auth/reset-password` | Reset password with token | No |

### Rate Limiting

- **Login:** 5 requests per minute
- **Forgot Password:** 3 requests per hour
- **Reset Password:** 5 requests per hour

---

## Project Structure

```
auth_system/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app initialization
│   ├── models.py               # SQLAlchemy models
│   ├── schemas.py              # Pydantic schemas
│   ├── database.py             # Database configuration
│   ├── security.py             # Password hashing functions
│   ├── jwt_utils.py            # JWT token operations
│   ├── dependencies.py         # Dependency injection
│   ├── routers.py              # API endpoints
│   ├── rate_limit.py           # Rate limiting setup
│   └── logging_config.py       # Logging configuration
├── tests/
│   ├── __init__.py
│   ├── conftest.py             # Pytest fixtures
│   └── test_auth.py            # Authentication tests
├── .env                        # Environment variables (not committed)
├── .env.example                # Example environment file
├── .gitignore                  # Git ignore rules
├── requirements.txt            # Python dependencies
├── pytest.ini                  # Pytest configuration
├── run.py                      # Entry point to run the app
└── README.md                   # User documentation
```

---

## Development Tips

### Debugging

Add breakpoints in your code and run with:

```bash
python -m pdb run.py
```

### Checking Logs

Logs are stored in `logs/auth.log` (created on first run):

```bash
# Follow logs in real-time
tail -f logs/auth.log

# On Windows PowerShell
Get-Content logs/auth.log -Wait
```

### Database Inspection

For SQLite, use SQLite Browser:

```bash
# macOS
brew install db-browser-for-sqlite
open auth.db

# Or use sqlite3 CLI
sqlite3 auth.db
> SELECT * FROM users;
>  .quit
```

### Making Database Migrations

When you add new models or fields, the app automatically creates tables on startup. 

For tracked migrations in production, set up Alembic:

```bash
alembic init alembic
alembic revision --autogenerate -m "Add new table"
alembic upgrade head
```

---

## Testing Best Practices

1. **Test isolation:** Each test should be independent
2. **Use fixtures:** Reuse common setup with pytest fixtures
3. **Clear names:** Test function names should describe what they test
4. **Edge cases:** Test valid inputs, invalid inputs, and edge cases
5. **Mock external services:** Mock SMTP/email in tests

---

## Performance Considerations

- Bcrypt password hashing is intentionally slow (security over speed)
- JWT tokens are validated on-the-fly (no database lookup for valid tokens)
- Refresh tokens are tracked in DB to support revocation
- Use database indexes on frequently queried fields (email, token fields)

---

## Common Issues

### Issue: `ImportError: No module named 'app'`

**Solution:** Ensure you're running from the project root directory:

```bash
cd auth_system
python run.py
```

### Issue: `ModuleNotFoundError: No module named 'dotenv'`

**Solution:** Install requirements:

```bash
pip install -r requirements.txt
```

### Issue: Database locked (SQLite)

**Solution:** Close other connections to the database. For production, use PostgreSQL instead.

### Issue: JWT secret not set error

**Solution:** Generate and add to `.env`:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Copy the output and set `JWT_SECRET_KEY` in your `.env` file.

---

## Next Steps / TODOs

- [ ] Implement email sending for password reset links
- [ ] Add email verification on registration
- [ ] Implement two-factor authentication (2FA/TOTP)
- [ ] Add user profile endpoints
- [ ] Implement role-based access control (RBAC)
- [ ] Add API key authentication for service-to-service calls
- [ ] Implement device/session management
- [ ] Add audit logging for compliance
- [ ] Set up CI/CD pipeline (GitHub Actions, GitLab CI)
- [ ] Configure Docker for deployment

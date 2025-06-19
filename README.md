# Monochrome Authentication Backend

A secure, microservice-based authentication and authorization system built with Django and Django REST Framework, featuring comprehensive MFA support and role-based access control.

---

## 🚀 Features

- **🔐 JWT Authentication** - Secure token-based authentication with access/refresh tokens
- **📧 Email Verification** - Mandatory email verification before login
- **🔒 Multi-Factor Authentication (MFA)** 
  - TOTP-based MFA (Google Authenticator compatible)
  - Backup codes for account recovery
  - Mandatory MFA setup after registration
- **👥 Role-Based Access Control (RBAC)** - Three user types: Admin, Staff, User
- **🛡️ Security Features**
  - Account lockout after failed attempts
  - Login history tracking
  - Password strength validation
  - Rate limiting support
- **📊 Comprehensive Admin Interface** - Full user management dashboard
- **📚 API Documentation** - Interactive Swagger/ReDoc documentation
- **🧩 Modular Architecture** - Organized into `users` and `common` apps

---

## 🛠️ Tech Stack

- **Python 3.10+** (tested with 3.13)
- **Django 5.1.2** - High-level Python web framework
- **Django REST Framework 3.15.2** - Powerful API toolkit
- **PostgreSQL** - Primary database (SQLite supported for development)
- **Key Libraries:**
  - `djangorestframework-simplejwt` - JWT authentication
  - `django-allauth` - Email authentication & verification
  - `django-otp` - TOTP/MFA implementation
  - `django-cors-headers` - CORS support
  - `drf-yasg` - API documentation
  - `python-dotenv` - Environment management

---

## 📋 Prerequisites

- Python 3.10 or higher
- PostgreSQL (optional, SQLite works for development)
- Virtual environment tool (venv, virtualenv, etc.)
- Git

---

## 🚀 Quick Start

### 1. Clone Repository
```bash
git clone https://github.com/BLKamau/monochrome_backend.git
cd monochrome_backend
```

### 2. Run Quick Setup Script
```bash
# For automated setup
bash scripts/quick_setup.sh
```

Or manually:

### 3. Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Configure Environment
```bash
cp .env.example .env
# Edit .env with your configuration
```

### 6. Setup Database
```bash
# For PostgreSQL setup
python scripts/setup_database.py

# Or use SQLite (default)
python manage.py migrate
```

### 7. Create Superuser
```bash
python manage.py createsuperuser
```

### 8. Load Test Data (Optional)
```bash
python scripts/setup_test_data.py
```

### 9. Run Development Server
```bash
python scripts/dev_server.py
# Or standard Django:
python manage.py runserver
```

---

## 🔧 Development Scripts

The project includes helpful development scripts in the `scripts/` directory:

```bash
# Central script manager
python scripts/manage.py

# Individual scripts
python scripts/dev_server.py      # Run with pre-flight checks
python scripts/setup_database.py  # Configure PostgreSQL
python scripts/reset_db.py        # Reset database
python scripts/setup_test_data.py # Create test users
python scripts/check_security.py  # Security audit
python scripts/run_tests.py       # Run tests with coverage
```

---

## 📡 API Endpoints

### Authentication
| Endpoint | Method | Description | Auth Required |
|----------|--------|-------------|---------------|
| `/api/auth/register/` | POST | User registration | No |
| `/api/auth/login/` | POST | Login (returns JWT) | No |
| `/api/auth/logout/` | POST | Logout (blacklist token) | Yes |
| `/api/auth/token/refresh/` | POST | Refresh access token | No |
| `/api/auth/verify-email/` | POST | Verify email address | No |

### MFA Management
| Endpoint | Method | Description | Auth Required |
|----------|--------|-------------|---------------|
| `/api/auth/mfa/setup/` | POST | Initialize MFA setup | Yes |
| `/api/auth/mfa/verify/` | POST | Verify MFA token | Yes |
| `/api/auth/mfa/login/` | POST | MFA login verification | No |
| `/api/auth/mfa/disable/` | POST | Disable MFA | Yes + MFA |
| `/api/auth/mfa/backup-codes/` | POST | Generate new backup codes | Yes + MFA |

### User Profile
| Endpoint | Method | Description | Auth Required |
|----------|--------|-------------|---------------|
| `/api/auth/profile/` | GET/PATCH | Get/update profile | Yes |
| `/api/auth/change-password/` | POST | Change password | Yes + MFA |
| `/api/auth/login-history/` | GET | View login history | Yes + MFA |

### Documentation
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/docs/` | GET | Swagger UI documentation |
| `/api/redoc/` | GET | ReDoc documentation |
| `/admin/` | GET | Django admin interface |

---

## 🗂️ Project Structure

```
monochrome_backend/
├── monochrome_backend/    # Main Django project
│   ├── settings.py        # Django configuration
│   ├── urls.py            # Main URL routing
│   └── wsgi.py            # WSGI configuration
├── users/                 # Authentication app
│   ├── models.py          # User, MFA, LoginHistory models
│   ├── serializers.py     # DRF serializers
│   ├── views.py           # API views
│   ├── services.py        # Business logic
│   ├── permissions.py     # Custom permissions
│   ├── urls.py            # App URL routing
│   └── admin.py           # Admin customization
├── common/                # Shared utilities
│   ├── middleware.py      # MFA & security middleware
│   ├── exceptions.py      # Custom exceptions
│   ├── utils.py           # Helper functions
│   └── views.py           # Common views
├── scripts/               # Development tools
│   ├── dev_server.py      # Enhanced dev server
│   ├── setup_database.py  # Database setup
│   ├── setup_test_data.py # Test data generator
│   └── manage.py          # Script manager
├── templates/             # Email templates
├── static/                # Static files
├── media/                 # User uploads
├── .env.example           # Environment template
├── requirements.txt       # Python dependencies
└── manage.py              # Django management
```

---

## 🧪 Testing

### Run Tests
```bash
# With coverage
python scripts/run_tests.py

# Standard Django
python manage.py test

# Specific app
python manage.py test users
```

### Test Credentials
After running `setup_test_data.py`:
- **Admin**: `admin` / `Admin123!@#`
- **Staff**: `staff1` / `Staff123!@#`
- **User**: `user1` / `User123!@#`

---

## 🔒 Security Features

- **Password Policy**: Minimum 8 characters, complexity requirements
- **Account Lockout**: After 5 failed attempts (30 minutes)
- **MFA Enforcement**: Required for all users
- **Session Security**: Secure cookies, CSRF protection
- **Rate Limiting**: Configurable per endpoint
- **Audit Trail**: Complete login history

---

## 🌐 Environment Variables

Key configuration in `.env`:

```ini
# Core Settings
DJANGO_SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
USE_SQLITE=True  # Set False for PostgreSQL
DATABASE_URL=postgresql://user:pass@localhost:5432/monochrome_db

# Email
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# Security
JWT_ACCESS_TOKEN_LIFETIME=15  # minutes
JWT_REFRESH_TOKEN_LIFETIME=7  # days

# Frontend
FRONTEND_URL=http://localhost:3000
```

See `.env.example` for complete configuration options.

---

## 🚀 Deployment

### Production Checklist
- [ ] Set `DEBUG=False`
- [ ] Configure proper `ALLOWED_HOSTS`
- [ ] Use PostgreSQL database
- [ ] Set strong `SECRET_KEY`
- [ ] Configure email backend
- [ ] Enable HTTPS
- [ ] Set secure cookie settings
- [ ] Configure proper CORS origins

### Docker Support
```bash
# Build and run with Docker Compose
docker-compose up --build
```

---

## 📊 Management Commands

```bash
# List all users
python manage.py list_users

# Create test data
python manage.py setup_test_data

# Export API schema
python scripts/export_api_docs.py
```

---

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📬 Contact & Support

**Developer:** Thabo Mantsima

- **Email:** [mantsimat@gmail.com](mailto:mantsimat@gmail.com)
- **GitHub:** [https://github.com/BLKamau](https://github.com/BLKamau)
- **LinkedIn:** [linkedin.com/in/thabo-mantsima-74b826212/](https://linkedin.com/in/thabo-mantsima-74b826212/)

For issues and feature requests, please use the [GitHub Issues](https://github.com/BLKamau/monochrome_backend/issues) page.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- Django & Django REST Framework communities
- Contributors to all the amazing Python packages used
- Everyone who provides feedback and suggestions

---

**Built with ❤️ by Thabo Mantsima**
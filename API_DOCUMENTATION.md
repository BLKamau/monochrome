# Monochrome API Documentation

## Overview

The Monochrome API provides secure authentication and authorization services with JWT tokens and mandatory MFA support.

**Base URL**: `http://localhost:8000/api`  
**API Version**: `v1`  
**Authentication**: JWT Bearer Token (except where noted)

---

## Table of Contents

1. [Authentication](#authentication)
2. [Response Format](#response-format)
3. [Error Codes](#error-codes)
4. [Endpoints](#endpoints)
   - [Authentication Endpoints](#authentication-endpoints)
   - [MFA Endpoints](#mfa-endpoints)
   - [User Profile Endpoints](#user-profile-endpoints)
   - [Security Endpoints](#security-endpoints)

---

## Authentication

Most endpoints require authentication using JWT Bearer tokens:

```http
Authorization: Bearer <access_token>
```

Tokens are obtained through the login endpoint and must be refreshed periodically.

---

## Response Format

All API responses follow a consistent format:

### Success Response
```json
{
  "success": true,
  "message": "Operation successful",
  "data": { ... }
}
```

### Error Response
```json
{
  "success": false,
  "message": "Error description",
  "errors": {
    "field_name": ["Error message"]
  }
}
```

---

## Error Codes

| Status Code | Description |
|-------------|-------------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 429 | Too Many Requests |
| 500 | Internal Server Error |

---

## Endpoints

### Authentication Endpoints

#### 1. Register User

Create a new user account.

- **URL**: `/auth/register/`
- **Method**: `POST`
- **Auth Required**: No
- **Rate Limit**: 3 per hour

**Request Body:**
```json
{
  "username": "johndoe",
  "email": "john@example.com",
  "password": "SecurePass123!",
  "password_confirm": "SecurePass123!",
  "user_type": "USER",
  "first_name": "John",
  "last_name": "Doe"
}
```

**User Types:**
- `USER` - Regular user (default)
- `STAFF` - Staff member
- `ADMIN` - Administrator

**Success Response (201):**
```json
{
  "success": true,
  "message": "Registration successful. Please check your email to verify your account.",
  "data": {
    "id": 1,
    "username": "johndoe",
    "email": "john@example.com",
    "user_type": "USER",
    "is_active": false,
    "is_email_verified": false,
    "is_mfa_enabled": false,
    "requires_mfa_setup": true
  }
}
```

**Error Response (400):**
```json
{
  "success": false,
  "message": "Validation error",
  "errors": {
    "username": ["A user with this username already exists."],
    "password": ["This password is too common."]
  }
}
```

---

#### 2. Login

Authenticate user and receive JWT tokens.

- **URL**: `/auth/login/`
- **Method**: `POST`
- **Auth Required**: No
- **Rate Limit**: 5 per minute

**Request Body:**
```json
{
  "username": "johndoe",
  "password": "SecurePass123!"
}
```

**Success Response (200):**
```json
{
  "success": true,
  "message": "Login successful.",
  "data": {
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "user": {
      "id": 1,
      "username": "johndoe",
      "email": "john@example.com",
      "user_type": "USER",
      "is_mfa_enabled": true,
      "is_mfa_verified": false
    }
  }
}
```

**Error Responses:**

*Invalid Credentials (401):*
```json
{
  "success": false,
  "message": "Invalid credentials."
}
```

*Email Not Verified (403):*
```json
{
  "success": false,
  "message": "Please verify your email before logging in."
}
```

*MFA Setup Required (403):*
```json
{
  "success": false,
  "message": "MFA setup required. Please complete MFA setup first.",
  "errors": {
    "requires_mfa_setup": true,
    "user_id": 1
  }
}
```

*Account Locked (403):*
```json
{
  "success": false,
  "message": "Account is locked due to multiple failed attempts. Please try again later."
}
```

---

#### 3. Logout

Blacklist refresh token to logout user.

- **URL**: `/auth/logout/`
- **Method**: `POST`
- **Auth Required**: Yes

**Request Body:**
```json
{
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Success Response (200):**
```json
{
  "success": true,
  "message": "Logout successful."
}
```

---

#### 4. Token Refresh

Get new access token using refresh token.

- **URL**: `/auth/token/refresh/`
- **Method**: `POST`
- **Auth Required**: No

**Request Body:**
```json
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Success Response (200):**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

---

#### 5. Email Verification

Verify email address using token from email.

- **URL**: `/auth/verify-email/`
- **Method**: `POST`
- **Auth Required**: No

**Request Body:**
```json
{
  "token": "Mw/crn2ae-df337c4ad85ece9fc999b87d0f2608dc"
}
```

**Success Response (200):**
```json
{
  "success": true,
  "message": "Email verified successfully.",
  "data": {
    "user_id": 1
  }
}
```

---

### MFA Endpoints

#### 1. MFA Setup

Initialize MFA setup and get QR code.

- **URL**: `/auth/mfa/setup/`
- **Method**: `POST`
- **Auth Required**: Yes

**Request Body:**
```json
{
  "device_name": "My Phone"
}
```

**Success Response (200):**
```json
{
  "success": true,
  "message": "MFA setup initiated. Please scan the QR code with your authenticator app.",
  "data": {
    "device_id": 1,
    "secret": "JBSWY3DPEHPK3PXP",
    "qr_code": "data:image/png;base64,iVBORw0KGgoAAAANS...",
    "backup_codes": [
      "A1B2C3D4",
      "E5F6G7H8",
      "I9J0K1L2",
      "M3N4O5P6",
      "Q7R8S9T0"
    ]
  }
}
```

---

#### 2. MFA Verify

Verify TOTP token to complete MFA setup.

- **URL**: `/auth/mfa/verify/`
- **Method**: `POST`
- **Auth Required**: Yes

**Request Body:**
```json
{
  "device_id": 1,
  "token": "123456"
}
```

**Success Response (200):**
```json
{
  "success": true,
  "message": "MFA successfully enabled.",
  "data": {
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "user": {
      "id": 1,
      "username": "johndoe",
      "is_mfa_enabled": true,
      "is_mfa_verified": true
    }
  }
}
```

---

#### 3. MFA Login

Verify MFA token during login.

- **URL**: `/auth/mfa/login/`
- **Method**: `POST`
- **Auth Required**: No

**Request Body (TOTP):**
```json
{
  "user_id": 1,
  "token": "123456"
}
```

**Request Body (Backup Code):**
```json
{
  "user_id": 1,
  "token": "A1B2C3D4"
}
```

**Success Response (200):**
```json
{
  "success": true,
  "message": "MFA verification successful.",
  "data": {
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "user": { ... }
  }
}
```

---

#### 4. Disable MFA

Disable MFA (requires password confirmation).

- **URL**: `/auth/mfa/disable/`
- **Method**: `POST`
- **Auth Required**: Yes (+ MFA verified)

**Request Body:**
```json
{
  "password": "SecurePass123!"
}
```

**Success Response (200):**
```json
{
  "success": true,
  "message": "MFA has been disabled successfully."
}
```

---

#### 5. Regenerate Backup Codes

Generate new set of backup codes.

- **URL**: `/auth/mfa/backup-codes/`
- **Method**: `POST`
- **Auth Required**: Yes (+ MFA verified)

**Success Response (200):**
```json
{
  "success": true,
  "message": "New backup codes generated successfully. Please save them securely.",
  "data": {
    "backup_codes": [
      "U1V2W3X4",
      "Y5Z6A7B8",
      "C9D0E1F2",
      "G3H4I5J6",
      "K7L8M9N0"
    ]
  }
}
```

---

### User Profile Endpoints

#### 1. Get Profile

Retrieve current user's profile.

- **URL**: `/auth/profile/`
- **Method**: `GET`
- **Auth Required**: Yes

**Success Response (200):**
```json
{
  "success": true,
  "message": "Profile retrieved successfully.",
  "data": {
    "id": 1,
    "username": "johndoe",
    "email": "john@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "user_type": "USER",
    "is_active": true,
    "is_email_verified": true,
    "is_mfa_enabled": true,
    "is_mfa_verified": true,
    "requires_mfa_setup": false,
    "created_at": "2025-06-19T10:00:00Z",
    "updated_at": "2025-06-19T10:30:00Z",
    "last_login": "2025-06-19T10:30:00Z"
  }
}
```

---

#### 2. Update Profile

Update user profile information.

- **URL**: `/auth/profile/`
- **Method**: `PATCH`
- **Auth Required**: Yes

**Request Body:**
```json
{
  "first_name": "John",
  "last_name": "Smith",
  "phone_number": "+1234567890"
}
```

**Success Response (200):**
```json
{
  "success": true,
  "message": "Profile updated successfully.",
  "data": { ... }
}
```

---

### Security Endpoints

#### 1. Change Password

Change user password.

- **URL**: `/auth/change-password/`
- **Method**: `POST`
- **Auth Required**: Yes (+ MFA verified)

**Request Body:**
```json
{
  "old_password": "OldPass123!",
  "new_password": "NewPass456!",
  "new_password_confirm": "NewPass456!"
}
```

**Success Response (200):**
```json
{
  "success": true,
  "message": "Password changed successfully."
}
```

**Note:** All tokens are invalidated after password change.

---

#### 2. Login History

Get user's login history.

- **URL**: `/auth/login-history/`
- **Method**: `GET`
- **Auth Required**: Yes (+ MFA verified)
- **Query Parameters**:
  - `page` (optional): Page number
  - `page_size` (optional): Items per page (max: 100)

**Success Response (200):**
```json
{
  "success": true,
  "message": "Login history retrieved successfully.",
  "data": [
    {
      "id": 1,
      "ip_address": "192.168.1.1",
      "user_agent": "Mozilla/5.0...",
      "login_time": "2025-06-19T10:30:00Z",
      "success": true,
      "failure_reason": null,
      "location": "New York, USA"
    }
  ],
  "count": 50,
  "next": "http://localhost:8000/api/auth/login-history/?page=2",
  "previous": null
}
```

---

#### 3. Password Reset Request

Request password reset email.

- **URL**: `/auth/password-reset/`
- **Method**: `POST`
- **Auth Required**: No
- **Rate Limit**: 3 per hour

**Request Body:**
```json
{
  "email": "john@example.com"
}
```

**Success Response (200):**
```json
{
  "success": true,
  "message": "If an account exists with this email, a password reset link has been sent."
}
```

---

#### 4. Password Reset Confirm

Reset password using token from email.

- **URL**: `/auth/password-reset/confirm/`
- **Method**: `POST`
- **Auth Required**: No

**Request Body:**
```json
{
  "token": "Mw/abc123-...",
  "new_password": "NewSecurePass789!",
  "new_password_confirm": "NewSecurePass789!"
}
```

**Success Response (200):**
```json
{
  "success": true,
  "message": "Password reset successfully."
}
```

---

## Rate Limiting

API endpoints are rate-limited to prevent abuse:

| Endpoint Type | Rate Limit |
|---------------|------------|
| Registration | 3 per hour |
| Login | 5 per minute |
| Password Reset | 3 per hour |
| General API | 100 per hour |

Exceeded rate limits return `429 Too Many Requests`.

---

## Testing

For testing, use the provided test credentials after running `setup_test_data.py`:

| User Type | Username | Password | MFA |
|-----------|----------|----------|-----|
| Admin | admin | Admin123!@# | ✓ |
| Staff | staff1 | Staff123!@# | ✓ |
| User | user1 | User123!@# | ✓ |
| No MFA | staff2 | Staff123!@# | ✗ |
| Unverified | unverified | User123!@# | ✗ |

---

## Postman Collection

Import the API collection for easy testing:

[Download Postman Collection](https://api.postman.com/collections/...)

---

## Need Help?

- **API Status**: `/api/health/`
- **Interactive Docs**: `/api/docs/`
- **Support**: mantsimat@gmail.com

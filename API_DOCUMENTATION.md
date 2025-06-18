# Monochrome API Documentation

## Authentication Endpoints

### Register User
- **POST** `/api/auth/register/`
- Body: `{ "username": "string", "email": "string", "password": "string", "password_confirm": "string", "user_type": "USER|STAFF|ADMIN" }`

### Login
- **POST** `/api/auth/login/`
- Body: `{ "username": "string", "password": "string" }`

### MFA Setup
- **POST** `/api/auth/mfa/setup/`
- Headers: `Authorization: Bearer <token>`
- Body: `{ "device_name": "string" }`

### MFA Verify
- **POST** `/api/auth/mfa/verify/`
- Headers: `Authorization: Bearer <token>`
- Body: `{ "device_id": 1, "token": "123456" }`

## User Profile Endpoints

### Get Profile
- **GET** `/api/auth/profile/`
- Headers: `Authorization: Bearer <token>`

### Update Profile
- **PATCH** `/api/auth/profile/`
- Headers: `Authorization: Bearer <token>`
- Body: `{ "first_name": "string", "last_name": "string" }`

## Security Endpoints

### Login History
- **GET** `/api/auth/login-history/`
- Headers: `Authorization: Bearer <token>`

### Change Password
- **POST** `/api/auth/change-password/`
- Headers: `Authorization: Bearer <token>`
- Body: `{ "old_password": "string", "new_password": "string", "new_password_confirm": "string" }`

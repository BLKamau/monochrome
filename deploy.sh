#!/bin/bash

# Simple deployment script for Monochrome Backend

echo "🚀 Deploying Monochrome Backend..."

# Activate virtual environment
source venv/bin/activate

# Github setup
git init
git add .
git commit -m "first commit and project structure setup"
git branch -M main
git remote add origin git@github.com:BLKamau/monochrome.git
git push -u origin main

# Install/update dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Run tests
python manage.py test

# Restart application (adjust based on your server setup)
# For systemd:
# sudo systemctl restart monochrome

# For supervisor:
# sudo supervisorctl restart monochrome

echo "✅ Deployment complete!"

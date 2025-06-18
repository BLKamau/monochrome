#!/bin/bash

# Script to create the scripts directory with all development tools

echo "🚀 Setting up Monochrome scripts directory..."

# Create scripts directory
mkdir -p scripts

# Create __init__.py
cat > scripts/__init__.py << 'EOF'
"""
Monochrome development scripts package.
"""
EOF

# Make all Python scripts executable
chmod +x scripts/*.py

# Create a quick setup script
cat > scripts/quick_setup.sh << 'EOF'
#!/bin/bash

# Quick setup for new developers

echo "🚀 Monochrome Quick Setup"
echo "========================"

# Check Python version
python_version=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+')
if (( $(echo "$python_version < 3.10" | bc -l) )); then
    echo "❌ Python 3.10+ required. Current version: $python_version"
    exit 1
fi

echo "✓ Python $python_version"

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate || source venv/Scripts/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Setup environment
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    cp .env.example .env
    echo "⚠️  Please edit .env with your configuration"
fi

# Run initial setup
echo "Running database setup..."
python scripts/manage.py setup-db

echo ""
echo "✅ Quick setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your configuration"
echo "2. Run: python scripts/manage.py"
echo "3. Choose 'all' to complete setup"
EOF

chmod +x scripts/quick_setup.sh

# Create a development checklist
cat > scripts/DEVELOPMENT_CHECKLIST.md << 'EOF'
# Monochrome Development Checklist

## Before Starting Development

- [ ] Run `python scripts/manage.py status` to check system
- [ ] Ensure database is running
- [ ] Activate virtual environment
- [ ] Pull latest changes from repository

## Daily Development Tasks

- [ ] Start development server: `python scripts/dev_server.py`
- [ ] Check for pending migrations
- [ ] Run tests before committing: `python scripts/run_tests.py`
- [ ] Check security: `python scripts/check_security.py`

## Before Committing

- [ ] Run all tests
- [ ] Check code formatting (black, isort)
- [ ] Update documentation if needed
- [ ] Check for security issues
- [ ] Ensure no sensitive data in commits

EOF
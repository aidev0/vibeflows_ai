#!/bin/bash

# Exit on error
set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting Alpha build process...${NC}"

# Check if Python 3.8+ is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Python 3 is required but not installed. Please install Python 3.8 or higher.${NC}"
    exit 1
fi

# Create and activate virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo -e "${GREEN}Creating virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
echo -e "${GREEN}Activating virtual environment...${NC}"
source venv/bin/activate

# Upgrade pip
echo -e "${GREEN}Upgrading pip...${NC}"
pip install --upgrade pip

# Install dependencies
echo -e "${GREEN}Installing dependencies...${NC}"
pip install -r requirements.txt

# Check for .env file
if [ ! -f ".env" ]; then
    echo -e "${RED}Warning: .env file not found. Please create one with necessary environment variables.${NC}"
    echo -e "${GREEN}Creating template .env file...${NC}"
    cat > .env << EOL
# API Keys
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
GOOGLE_CLOUD_PROJECT=


# Application Settings
ENVIRONMENT=development
LOG_LEVEL=INFO
EOL
    echo -e "${RED}Please fill in the .env file with your actual credentials.${NC}"
fi

# Run linting
echo -e "${GREEN}Running linting...${NC}"
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics

# Run type checking
echo -e "${GREEN}Running type checking...${NC}"
mypy .

# Run tests
echo -e "${GREEN}Running tests...${NC}"
pytest

# Format code
echo -e "${GREEN}Formatting code...${NC}"
black .

echo -e "${GREEN}Build completed successfully!${NC}"
echo -e "${GREEN}To activate the environment, run: source venv/bin/activate${NC}" 
# VibeFlows AI

VibeFlows AI is a comprehensive workflow automation platform that integrates multiple AI models, APIs, and automation tools to create dynamic, intelligent workflows. The platform combines LLM-powered agents with external integrations like Apollo.io and n8n to process user queries and execute complex automation tasks.

## 🚀 Features

- **Multi-Modal AI Integration**: Support for Claude, GPT, and Gemini models
- **Dynamic Workflow Execution**: AI-powered flow creation and execution with conditional logic
- **Apollo.io Integration**: Lead generation and enrichment capabilities
- **n8n Workflow Automation**: Execute n8n workflows programmatically
- **Real-time Processing**: WebSocket support for streaming responses
- **MongoDB Storage**: Persistent storage for flows, runs, and user data
- **RESTful API**: Comprehensive API for workflow management

## 🏗️ Architecture

The platform is built with a modular architecture:

- **API Layer** (`api.py`): FastAPI-based REST API with WebSocket support
- **Flow Engine** (`flow_runner.py`): Executes workflows with conditional branching
- **AI Agents** (`agent_runner.py`): Manages AI model interactions and responses
- **External Integrations**:
  - Apollo API (`apollo_api.py`): Lead generation and data enrichment
  - n8n Runner (`n8n_runner.py`): Workflow automation execution
- **Database Layer**: MongoDB for persistent storage
- **Utilities**: Query analysis, response generation, and edge condition checking

## 📋 Prerequisites

- Python 3.11.7
- MongoDB instance
- Environment variables configured (see Configuration section)

## 🛠️ Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd vibeflows_ai
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables (see Configuration section)

5. Start the application:
```bash
uvicorn api:app --host=0.0.0.0 --port=8000
```

## ⚙️ Configuration

Create a `.env` file in the root directory with the following variables:

```env
# Database
MONGODB_URI=mongodb://localhost:27017

# AI Model API Keys
ANTHROPIC_API_KEY=your_claude_api_key
OPENAI_API_KEY=your_openai_api_key
GOOGLE_API_KEY=your_gemini_api_key

# External Services
APOLLO_API_KEY=your_apollo_api_key
N8N_BASE_URL=your_n8n_instance_url
N8N_API_KEY=your_n8n_api_key

# Application Settings
ENVIRONMENT=production
DEBUG=false
```

## 🌐 API Endpoints

### Core Endpoints

- `GET /` - Health check
- `POST /api/ai/stream` - Process AI requests with streaming response
- `WebSocket /ws/{client_id}` - WebSocket connection for real-time communication

### Flow Management

- Flow execution through the main AI endpoint
- Dynamic flow creation based on user queries
- Conditional branching and edge evaluation

## 🔄 Workflow System

### Flow Structure

Workflows consist of:
- **Nodes**: Individual processing units (AI agents, API calls, conditions)
- **Edges**: Connections between nodes with conditional logic
- **Variables**: Shared data across the workflow execution

### Flow Execution

1. **Query Analysis**: User input is analyzed to determine intent
2. **Flow Selection/Creation**: Appropriate workflow is selected or created
3. **Node Execution**: Sequential processing through workflow nodes
4. **Condition Evaluation**: Edge conditions determine next steps
5. **Response Generation**: Final output is formatted and returned

## 🤖 AI Agents

The platform includes specialized AI agents for different tasks:

- **Query Understanding**: Analyzes user intent and requirements
- **Workflow Design**: Creates and modifies workflow structures
- **Response Generation**: Formats and presents results to users

## 🔗 External Integrations

### Apollo.io
- Lead generation and enrichment
- Company and contact data retrieval
- Campaign management support

### n8n Workflows
- Execute pre-built automation workflows
- Pass data between workflow steps
- Handle complex automation scenarios

## 📊 Database Schema

### Collections

- **flows**: Workflow definitions and metadata
- **runs**: Execution history and results
- **users**: User accounts and preferences
- **credentials**: Encrypted API keys and authentication data

## 🧪 Testing

The project includes comprehensive test files:

```bash
# Run specific test modules
python test_flow_runner.py
python test_apollo_api.py
python test_n8n_runner.py

# Run all tests
python -m pytest
```

Test files cover:
- Flow execution and conditional logic
- API integrations (Apollo, n8n)
- Agent functionality
- Database operations
- Error handling scenarios

## 📁 Project Structure

```
vibeflows_ai/
├── api.py                    # Main FastAPI application
├── flow_runner.py           # Workflow execution engine
├── agent_runner.py          # AI agent management
├── apollo_api.py            # Apollo.io integration
├── n8n_runner.py           # n8n workflow runner
├── query_analyzer.py       # User query processing
├── response_generator.py   # Output formatting
├── edge_condition_checker.py # Flow conditional logic
├── tools.py                # Utility functions
├── user_interface.py       # UI interaction handlers
├── requirements.txt        # Python dependencies
├── runtime.txt            # Python version specification
├── Procfile              # Heroku deployment configuration
├── test_*.py            # Test files
└── leads/              # Sample lead generation data
```

## 🚀 Deployment

The application is configured for Heroku deployment:

1. **Procfile**: Specifies the web process command
2. **runtime.txt**: Python version specification
3. **Environment Variables**: Configure through Heroku dashboard or CLI

### Heroku Deployment

```bash
heroku create your-app-name
heroku config:set MONGODB_URI=your_mongodb_uri
heroku config:set ANTHROPIC_API_KEY=your_key
# ... set other environment variables
git push heroku main
```

## 🔒 Security

- Environment variables for sensitive data
- CORS configuration for web access
- MongoDB connection security
- API key encryption and storage

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📝 License

[Add your license information here]

## 🆘 Support

For support and questions:
- Create an issue in the repository
- Check the test files for usage examples
- Review the API documentation in the code

## 🔄 Recent Updates

- Enhanced error handling for Claude AI streaming
- Improved environment variable loading
- Fixed credential management issues
- Better datetime serialization
- Resolved agent ID assignment problems

---

**Note**: The `agents/` and `flows/` directories contain legacy code from previous versions and are not part of the current implementation.
import os
import subprocess
import asyncio
import json
from typing import Dict, List, Any, Optional
from pymongo import MongoClient
from datetime import datetime

REAL_MCP_CLIENTS = [
    # Official Anthropic MCP servers (Node.js - use npx)
    {
        "name": "filesystem",
        "description": "Secure file operations with configurable access controls",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
        "env": {},
        "credentials": [],
        "type": "mcp_client",
        "language": "nodejs",
        "required_packages": ["@modelcontextprotocol/server-filesystem"]
    },
    {
        "name": "github",
        "description": "Tools to read, search, and manipulate Git repositories and GitHub",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-github"],
        "env": {
            "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_PERSONAL_ACCESS_TOKEN}"
        },
        "credentials": ["GITHUB_PERSONAL_ACCESS_TOKEN"],
        "type": "mcp_client",
        "language": "nodejs",
        "required_packages": ["@modelcontextprotocol/server-github"]
    },
    {
        "name": "postgres",
        "description": "PostgreSQL database integration with configurable access controls",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-postgres", "${DATABASE_URL}"],
        "env": {},
        "credentials": ["DATABASE_URL"],
        "type": "mcp_client",
        "language": "nodejs",
        "required_packages": ["@modelcontextprotocol/server-postgres"]
    },
    {
        "name": "puppeteer",
        "description": "Web scraping and browser automation using Puppeteer",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-puppeteer"],
        "env": {},
        "credentials": [],
        "type": "mcp_client",
        "language": "nodejs",
        "required_packages": ["@modelcontextprotocol/server-puppeteer"]
    },
    {
        "name": "memory",
        "description": "Knowledge graph memory system for LLM conversations",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-memory"],
        "env": {},
        "credentials": [],
        "type": "mcp_client",
        "language": "nodejs",
        "required_packages": ["@modelcontextprotocol/server-memory"]
    },
    {
        "name": "everything",
        "description": "Test server that exercises all MCP protocol features",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-everything"],
        "env": {},
        "credentials": [],
        "type": "mcp_client",
        "language": "nodejs",
        "required_packages": ["@modelcontextprotocol/server-everything"]
    },
    
    # Community MCP servers (Python - use uvx)
    {
        "name": "sqlite",
        "description": "SQLite database operations with schema inspection",
        "command": "uvx",
        "args": ["mcp-server-sqlite"],
        "env": {},
        "credentials": [],
        "type": "mcp_client",
        "language": "python",
        "required_packages": ["mcp-server-sqlite"]
    },
    {
        "name": "git",
        "description": "Git repository operations and management",
        "command": "uvx",
        "args": ["mcp-server-git", "--repository", "/path/to/repo"],
        "env": {},
        "credentials": [],
        "type": "mcp_client",
        "language": "python",
        "required_packages": ["mcp-server-git"]
    },
    {
        "name": "brave_search",
        "description": "Web search using Brave Search API",
        "command": "uvx",
        "args": ["mcp-server-brave-search"],
        "env": {
            "BRAVE_API_KEY": "${BRAVE_API_KEY}"
        },
        "credentials": ["BRAVE_API_KEY"],
        "type": "mcp_client",
        "language": "python",
        "required_packages": ["mcp-server-brave-search"]
    },
    {
        "name": "fetch",
        "description": "Web content fetching and conversion",
        "command": "uvx",
        "args": ["mcp-server-fetch"],
        "env": {},
        "credentials": [],
        "type": "mcp_client",
        "language": "python",
        "required_packages": ["mcp-server-fetch"]
    },
    {
        "name": "gmail",
        "description": "Gmail API integration for email management",
        "command": "uvx",
        "args": ["mcp-server-gmail"],
        "env": {
            "GOOGLE_APPLICATION_CREDENTIALS": "${GOOGLE_APPLICATION_CREDENTIALS}"
        },
        "credentials": ["GOOGLE_APPLICATION_CREDENTIALS"],
        "type": "mcp_client",
        "language": "python",
        "required_packages": ["mcp-server-gmail"]
    },
    {
        "name": "google_drive",
        "description": "Google Drive file operations and management",
        "command": "uvx",
        "args": ["mcp-server-gdrive"],
        "env": {
            "GOOGLE_APPLICATION_CREDENTIALS": "${GOOGLE_APPLICATION_CREDENTIALS}"
        },
        "credentials": ["GOOGLE_APPLICATION_CREDENTIALS"],
        "type": "mcp_client",
        "language": "python",
        "required_packages": ["mcp-server-gdrive"]
    },
    {
        "name": "calendar",
        "description": "Google Calendar integration",
        "command": "uvx",
        "args": ["mcp-server-gcal"],
        "env": {
            "GOOGLE_APPLICATION_CREDENTIALS": "${GOOGLE_APPLICATION_CREDENTIALS}"
        },
        "credentials": ["GOOGLE_APPLICATION_CREDENTIALS"],
        "type": "mcp_client",
        "language": "python",
        "required_packages": ["mcp-server-gcal"]
    },
    {
        "name": "slack",
        "description": "Send messages and interact with Slack workspace",
        "command": "uvx",
        "args": ["mcp-server-slack"],
        "env": {
            "SLACK_BOT_TOKEN": "${SLACK_BOT_TOKEN}"
        },
        "credentials": ["SLACK_BOT_TOKEN"],
        "type": "mcp_client",
        "language": "python",
        "required_packages": ["mcp-server-slack"]
    },
    {
        "name": "discord",
        "description": "Discord bot integration",
        "command": "uvx",
        "args": ["mcp-server-discord"],
        "env": {
            "DISCORD_BOT_TOKEN": "${DISCORD_BOT_TOKEN}"
        },
        "credentials": ["DISCORD_BOT_TOKEN"],
        "type": "mcp_client",
        "language": "python",
        "required_packages": ["mcp-server-discord"]
    },
    {
        "name": "telegram",
        "description": "Telegram bot integration",
        "command": "uvx",
        "args": ["mcp-server-telegram"],
        "env": {
            "TELEGRAM_BOT_TOKEN": "${TELEGRAM_BOT_TOKEN}"
        },
        "credentials": ["TELEGRAM_BOT_TOKEN"],
        "type": "mcp_client",
        "language": "python",
        "required_packages": ["mcp-server-telegram"]
    },
    {
        "name": "notion",
        "description": "Notion workspace integration",
        "command": "uvx",
        "args": ["mcp-server-notion"],
        "env": {
            "NOTION_API_KEY": "${NOTION_API_KEY}"
        },
        "credentials": ["NOTION_API_KEY"],
        "type": "mcp_client",
        "language": "python",
        "required_packages": ["mcp-server-notion"]
    },
    {
        "name": "airtable",
        "description": "Airtable database integration",
        "command": "uvx",
        "args": ["mcp-server-airtable"],
        "env": {
            "AIRTABLE_API_KEY": "${AIRTABLE_API_KEY}"
        },
        "credentials": ["AIRTABLE_API_KEY"],
        "type": "mcp_client",
        "language": "python",
        "required_packages": ["mcp-server-airtable"]
    },
    {
        "name": "linear",
        "description": "Linear issue tracking integration",
        "command": "uvx",
        "args": ["mcp-server-linear"],
        "env": {
            "LINEAR_API_KEY": "${LINEAR_API_KEY}"
        },
        "credentials": ["LINEAR_API_KEY"],
        "type": "mcp_client",
        "language": "python",
        "required_packages": ["mcp-server-linear"]
    },
    {
        "name": "jira",
        "description": "Atlassian Jira integration",
        "command": "uvx",
        "args": ["mcp-server-jira"],
        "env": {
            "JIRA_URL": "${JIRA_URL}",
            "JIRA_USERNAME": "${JIRA_USERNAME}",
            "JIRA_API_TOKEN": "${JIRA_API_TOKEN}"
        },
        "credentials": ["JIRA_URL", "JIRA_USERNAME", "JIRA_API_TOKEN"],
        "type": "mcp_client",
        "language": "python",
        "required_packages": ["mcp-server-jira"]
    },
    {
        "name": "trello",
        "description": "Trello project management integration",
        "command": "uvx",
        "args": ["mcp-server-trello"],
        "env": {
            "TRELLO_API_KEY": "${TRELLO_API_KEY}",
            "TRELLO_TOKEN": "${TRELLO_TOKEN}"
        },
        "credentials": ["TRELLO_API_KEY", "TRELLO_TOKEN"],
        "type": "mcp_client",
        "language": "python",
        "required_packages": ["mcp-server-trello"]
    },
    {
        "name": "hubspot",
        "description": "HubSpot CRM integration",
        "command": "uvx",
        "args": ["mcp-server-hubspot"],
        "env": {
            "HUBSPOT_API_KEY": "${HUBSPOT_API_KEY}"
        },
        "credentials": ["HUBSPOT_API_KEY"],
        "type": "mcp_client",
        "language": "python",
        "required_packages": ["mcp-server-hubspot"]
    },
    {
        "name": "salesforce",
        "description": "Salesforce CRM integration",
        "command": "uvx",
        "args": ["mcp-server-salesforce"],
        "env": {
            "SALESFORCE_INSTANCE_URL": "${SALESFORCE_INSTANCE_URL}",
            "SALESFORCE_CLIENT_ID": "${SALESFORCE_CLIENT_ID}",
            "SALESFORCE_CLIENT_SECRET": "${SALESFORCE_CLIENT_SECRET}"
        },
        "credentials": ["SALESFORCE_INSTANCE_URL", "SALESFORCE_CLIENT_ID", "SALESFORCE_CLIENT_SECRET"],
        "type": "mcp_client",
        "language": "python",
        "required_packages": ["mcp-server-salesforce"]
    },
    {
        "name": "shopify",
        "description": "Shopify e-commerce integration",
        "command": "uvx",
        "args": ["mcp-server-shopify"],
        "env": {
            "SHOPIFY_SHOP_URL": "${SHOPIFY_SHOP_URL}",
            "SHOPIFY_ACCESS_TOKEN": "${SHOPIFY_ACCESS_TOKEN}"
        },
        "credentials": ["SHOPIFY_SHOP_URL", "SHOPIFY_ACCESS_TOKEN"],
        "type": "mcp_client",
        "language": "python",
        "required_packages": ["mcp-server-shopify"]
    },
    {
        "name": "stripe",
        "description": "Stripe payment processing integration",
        "command": "uvx",
        "args": ["mcp-server-stripe"],
        "env": {
            "STRIPE_SECRET_KEY": "${STRIPE_SECRET_KEY}"
        },
        "credentials": ["STRIPE_SECRET_KEY"],
        "type": "mcp_client",
        "language": "python",
        "required_packages": ["mcp-server-stripe"]
    },
    {
        "name": "aws",
        "description": "AWS services integration",
        "command": "uvx",
        "args": ["mcp-server-aws"],
        "env": {
            "AWS_ACCESS_KEY_ID": "${AWS_ACCESS_KEY_ID}",
            "AWS_SECRET_ACCESS_KEY": "${AWS_SECRET_ACCESS_KEY}",
            "AWS_REGION": "${AWS_REGION}"
        },
        "credentials": ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_REGION"],
        "type": "mcp_client",
        "language": "python",
        "required_packages": ["mcp-server-aws"]
    },
    {
        "name": "docker",
        "description": "Docker container management",
        "command": "uvx",
        "args": ["mcp-server-docker"],
        "env": {},
        "credentials": [],
        "type": "mcp_client",
        "language": "python",
        "required_packages": ["mcp-server-docker"]
    },
    {
        "name": "kubernetes",
        "description": "Kubernetes cluster management",
        "command": "uvx",
        "args": ["mcp-server-kubernetes"],
        "env": {
            "KUBECONFIG": "${KUBECONFIG}"
        },
        "credentials": ["KUBECONFIG"],
        "type": "mcp_client",
        "language": "python",
        "required_packages": ["mcp-server-kubernetes"]
    },
    {
        "name": "mongodb",
        "description": "MongoDB database integration",
        "command": "uvx",
        "args": ["mcp-server-mongodb"],
        "env": {
            "MONGODB_URI": "${MONGODB_URI}"
        },
        "credentials": ["MONGODB_URI"],
        "type": "mcp_client",
        "language": "python",
        "required_packages": ["mcp-server-mongodb"]
    },
    {
        "name": "redis",
        "description": "Redis cache and pub/sub integration",
        "command": "uvx",
        "args": ["mcp-server-redis"],
        "env": {
            "REDIS_URL": "${REDIS_URL}"
        },
        "credentials": ["REDIS_URL"],
        "type": "mcp_client",
        "language": "python",
        "required_packages": ["mcp-server-redis"]
    },
    {
        "name": "elasticsearch",
        "description": "Elasticsearch search engine integration",
        "command": "uvx",
        "args": ["mcp-server-elasticsearch"],
        "env": {
            "ELASTICSEARCH_URL": "${ELASTICSEARCH_URL}",
            "ELASTICSEARCH_USERNAME": "${ELASTICSEARCH_USERNAME}",
            "ELASTICSEARCH_PASSWORD": "${ELASTICSEARCH_PASSWORD}"
        },
        "credentials": ["ELASTICSEARCH_URL", "ELASTICSEARCH_USERNAME", "ELASTICSEARCH_PASSWORD"],
        "type": "mcp_client",
        "language": "python",
        "required_packages": ["mcp-server-elasticsearch"]
    },
    {
        "name": "youtube",
        "description": "YouTube API integration for video management",
        "command": "uvx",
        "args": ["mcp-server-youtube"],
        "env": {
            "YOUTUBE_API_KEY": "${YOUTUBE_API_KEY}"
        },
        "credentials": ["YOUTUBE_API_KEY"],
        "type": "mcp_client",
        "language": "python",
        "required_packages": ["mcp-server-youtube"]
    },
    {
        "name": "twitter",
        "description": "Twitter/X API integration",
        "command": "uvx",
        "args": ["mcp-server-twitter"],
        "env": {
            "TWITTER_BEARER_TOKEN": "${TWITTER_BEARER_TOKEN}"
        },
        "credentials": ["TWITTER_BEARER_TOKEN"],
        "type": "mcp_client",
        "language": "python",
        "required_packages": ["mcp-server-twitter"]
    },
    {
        "name": "sendgrid",
        "description": "SendGrid email delivery integration",
        "command": "uvx",
        "args": ["mcp-server-sendgrid"],
        "env": {
            "SENDGRID_API_KEY": "${SENDGRID_API_KEY}"
        },
        "credentials": ["SENDGRID_API_KEY"],
        "type": "mcp_client",
        "language": "python",
        "required_packages": ["mcp-server-sendgrid"]
    },
    {
        "name": "twilio",
        "description": "Twilio SMS and voice integration",
        "command": "uvx",
        "args": ["mcp-server-twilio"],
        "env": {
            "TWILIO_ACCOUNT_SID": "${TWILIO_ACCOUNT_SID}",
            "TWILIO_AUTH_TOKEN": "${TWILIO_AUTH_TOKEN}"
        },
        "credentials": ["TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN"],
        "type": "mcp_client",
        "language": "python",
        "required_packages": ["mcp-server-twilio"]
    },
    {
        "name": "wordpress",
        "description": "WordPress CMS integration",
        "command": "uvx",
        "args": ["mcp-server-wordpress"],
        "env": {
            "WORDPRESS_SITE_URL": "${WORDPRESS_SITE_URL}",
            "WORDPRESS_USERNAME": "${WORDPRESS_USERNAME}",
            "WORDPRESS_APP_PASSWORD": "${WORDPRESS_APP_PASSWORD}"
        },
        "credentials": ["WORDPRESS_SITE_URL", "WORDPRESS_USERNAME", "WORDPRESS_APP_PASSWORD"],
        "type": "mcp_client",
        "language": "python",
        "required_packages": ["mcp-server-wordpress"]
    },
    {
        "name": "home_assistant",
        "description": "Home Assistant smart home integration",
        "command": "uvx",
        "args": ["mcp-server-homeassistant"],
        "env": {
            "HOMEASSISTANT_URL": "${HOMEASSISTANT_URL}",
            "HOMEASSISTANT_TOKEN": "${HOMEASSISTANT_TOKEN}"
        },
        "credentials": ["HOMEASSISTANT_URL", "HOMEASSISTANT_TOKEN"],
        "type": "mcp_client",
        "language": "python",
        "required_packages": ["mcp-server-homeassistant"]
    },
    {
        "name": "leetcode",
        "description": "LeetCode practice problems integration",
        "command": "uvx",
        "args": ["mcp-server-leetcode"],
        "env": {},
        "credentials": [],
        "type": "mcp_client",
        "language": "python",
        "required_packages": ["mcp-server-leetcode"]
    }
]

# Global store for active MCP processes
ACTIVE_MCP_CLIENTS = {}

async def start_mcp_client(client_config: Dict) -> Optional[subprocess.Popen]:
    """Start an MCP client process and return the process handle"""
    try:
        command = client_config["command"]
        args = []
        
        # Substitute environment variables in args
        for arg in client_config["args"]:
            if arg.startswith("${") and arg.endswith("}"):
                env_var = arg[2:-1]
                args.append(os.getenv(env_var, arg))
            else:
                args.append(arg)
        
        # Build environment
        env = os.environ.copy()
        for key, value in client_config.get("env", {}).items():
            if value.startswith("${") and value.endswith("}"):
                env_var = value[2:-1]
                env[key] = os.getenv(env_var, "")
            else:
                env[key] = value
        
        # Start the MCP server process
        process = subprocess.Popen(
            [command] + args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            text=True
        )
        
        ACTIVE_MCP_CLIENTS[client_config["name"]] = {
            "process": process,
            "config": client_config
        }
        
        # Update status in database
        db = MongoClient(os.getenv("MONGODB_URI")).vibeflows
        db.mcp_clients.update_one(
            {"name": client_config["name"]},
            {"$set": {"status": "connected", "process_id": process.pid}}
        )
        
        print(f"Started MCP client: {client_config['name']} ({client_config['language']})")
        return process
        
    except Exception as e:
        print(f"Failed to start MCP client {client_config['name']}: {e}")
        return None

async def stop_mcp_client(client_name: str):
    """Stop an MCP client process"""
    if client_name in ACTIVE_MCP_CLIENTS:
        process = ACTIVE_MCP_CLIENTS[client_name]["process"]
        process.terminate()
        
        # Wait for process to terminate
        try:
            await asyncio.wait_for(asyncio.create_subprocess_exec("sleep", "0"), timeout=5.0)
            process.wait()
        except:
            process.kill()
        
        # Update database
        db = MongoClient(os.getenv("MONGODB_URI")).vibeflows
        db.mcp_clients.update_one(
            {"name": client_name},
            {"$set": {"status": "disconnected", "process_id": None}}
        )
        
        del ACTIVE_MCP_CLIENTS[client_name]

def generate_claude_desktop_config(mcp_clients, environment_vars):
    """Generate claude_desktop_config.json from MCP clients data"""
    config = {"mcpServers": {}}
    
    for client in mcp_clients:
        if client.get("status") == "enabled":
            # Substitute environment variables in args
            args = []
            for arg in client["args"]:
                if arg.startswith("${") and arg.endswith("}"):
                    env_var = arg[2:-1]
                    args.append(environment_vars.get(env_var, arg))
                else:
                    args.append(arg)
            
            # Build env object with actual values
            env = {}
            for key, value in client["env"].items():
                if value.startswith("${") and value.endswith("}"):
                    env_var = value[2:-1]
                    env[key] = environment_vars.get(env_var, "")
                else:
                    env[key] = value
            
            config["mcpServers"][client["name"]] = {
                "command": client["command"],
                "args": args
            }
            
            # Only add env if not empty
            if env:
                config["mcpServers"][client["name"]]["env"] = env
    
    return config

def insert_real_mcp_clients_into_db():
    """Insert real MCP clients into MongoDB"""
    db = MongoClient(os.getenv("MONGODB_URI")).vibeflows

    responses = []

    for client in REAL_MCP_CLIENTS:
        client["created_at"] = datetime.utcnow()
        client["status"] = "disconnected"
        response = db.mcp_clients.insert_one(client)
        responses.append(response)

    print(f"Created {len(REAL_MCP_CLIENTS)} real MCP clients")
    return responses

if __name__ == "__main__":
    insert_real_mcp_clients_into_db()
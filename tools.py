import os
from pymongo import MongoClient
from datetime import datetime

TOOLS = [
    {
        "name": "write_file",
        "description": "Write content to a file on disk",
        "type": "function",
        "function": "def write_file(data):\n    with open(data['file_path'], 'w') as f:\n        f.write(data['content'])\n    return {'status': 'success', 'file_path': data['file_path'], 'bytes_written': len(data['content'])}",
        "input_schema": {
            "type": "object", 
            "properties": {
                "file_path": {"type": "string"}, 
                "content": {"type": "string"}
            }
        },
        "output_schema": {
            "type": "object", 
            "properties": {
                "status": {"type": "string"}, 
                "file_path": {"type": "string"}, 
                "bytes_written": {"type": "number"}
            }
        },
        "credentials": [],
        "command": ["python", "write_file"],
        "language": "python",
        "required_packages": []
    },
    {
        "name": "read_file",
        "description": "Read content from a file on disk",
        "type": "function",
        "function": "def read_file(data):\n    with open(data['file_path'], 'r') as f:\n        content = f.read()\n    return {'status': 'success', 'content': content, 'file_size': len(content)}",
        "input_schema": {
            "type": "object", 
            "properties": {
                "file_path": {"type": "string"}
            }
        },
        "output_schema": {
            "type": "object", 
            "properties": {
                "status": {"type": "string"}, 
                "content": {"type": "string"}, 
                "file_size": {"type": "number"}
            }
        },
        "credentials": [],
        "command": ["python", "read_file"],
        "language": "python",
        "required_packages": []
    },
    {
        "name": "store_db",
        "description": "Store data in database collection",
        "type": "function",
        "function": "def store_db(data):\n    from pymongo import MongoClient\n    import os\n    db = MongoClient(os.getenv('MONGODB_URI')).get_database(data['database'])\n    collection = db[data['collection']]\n    result = collection.insert_one(data['document'])\n    return {'status': 'success', 'inserted_id': str(result.inserted_id)}",
        "input_schema": {
            "type": "object", 
            "properties": {
                "database": {"type": "string"}, 
                "collection": {"type": "string"}, 
                "document": {"type": "object"}
            }
        },
        "output_schema": {
            "type": "object", 
            "properties": {
                "status": {"type": "string"}, 
                "inserted_id": {"type": "string"}
            }
        },
        "credentials": ["MONGODB_URI"],
        "command": ["python", "store_db"],
        "language": "python",
        "required_packages": ["pymongo"]
    },
    {
        "name": "query_db",
        "description": "Query data from database collection",
        "type": "function",
        "function": "def query_db(data):\n    from pymongo import MongoClient\n    import os\n    db = MongoClient(os.getenv('MONGODB_URI')).get_database(data['database'])\n    collection = db[data['collection']]\n    results = list(collection.find(data.get('filter', {})))\n    # Convert ObjectId to string for JSON serialization\n    for result in results:\n        if '_id' in result:\n            result['_id'] = str(result['_id'])\n    return {'status': 'success', 'results': results, 'count': len(results)}",
        "input_schema": {
            "type": "object", 
            "properties": {
                "database": {"type": "string"}, 
                "collection": {"type": "string"}, 
                "filter": {"type": "object"}
            }
        },
        "output_schema": {
            "type": "object", 
            "properties": {
                "status": {"type": "string"}, 
                "results": {"type": "array"}, 
                "count": {"type": "number"}
            }
        },
        "credentials": ["MONGODB_URI"],
        "command": ["python", "query_db"],
        "language": "python",
        "required_packages": ["pymongo"]
    },
    {
        "name": "delete_file",
        "description": "Delete a file from disk",
        "type": "function",
        "function": "def delete_file(data):\n    import os\n    if os.path.exists(data['file_path']):\n        os.remove(data['file_path'])\n        return {'status': 'success', 'deleted_file': data['file_path']}\n    else:\n        return {'status': 'error', 'message': 'File not found', 'file_path': data['file_path']}",
        "input_schema": {
            "type": "object", 
            "properties": {
                "file_path": {"type": "string"}
            }
        },
        "output_schema": {
            "type": "object", 
            "properties": {
                "status": {"type": "string"}, 
                "deleted_file": {"type": "string"},
                "message": {"type": "string"}
            }
        },
        "credentials": [],
        "command": ["python", "delete_file"],
        "language": "python",
        "required_packages": []
    },
    {
        "name": "list_files",
        "description": "List files in a directory",
        "type": "function",
        "function": "def list_files(data):\n    import os\n    try:\n        files = os.listdir(data['directory'])\n        return {'status': 'success', 'files': files, 'count': len(files)}\n    except FileNotFoundError:\n        return {'status': 'error', 'message': 'Directory not found', 'directory': data['directory']}",
        "input_schema": {
            "type": "object", 
            "properties": {
                "directory": {"type": "string"}
            }
        },
        "output_schema": {
            "type": "object", 
            "properties": {
                "status": {"type": "string"}, 
                "files": {"type": "array"}, 
                "count": {"type": "number"},
                "message": {"type": "string"},
                "directory": {"type": "string"}
            }
        },
        "credentials": [],
        "command": ["python", "list_files"],
        "language": "python",
        "required_packages": []
    },
    {
        "name": "update_db",
        "description": "Update documents in database collection",
        "type": "function",
        "function": "def update_db(data):\n    from pymongo import MongoClient\n    import os\n    db = MongoClient(os.getenv('MONGODB_URI')).get_database(data['database'])\n    collection = db[data['collection']]\n    result = collection.update_many(data['filter'], {'$set': data['update']})\n    return {'status': 'success', 'modified_count': result.modified_count, 'matched_count': result.matched_count}",
        "input_schema": {
            "type": "object", 
            "properties": {
                "database": {"type": "string"}, 
                "collection": {"type": "string"}, 
                "filter": {"type": "object"}, 
                "update": {"type": "object"}
            }
        },
        "output_schema": {
            "type": "object", 
            "properties": {
                "status": {"type": "string"}, 
                "modified_count": {"type": "number"},
                "matched_count": {"type": "number"}
            }
        },
        "credentials": ["MONGODB_URI"],
        "command": ["python", "update_db"],
        "language": "python",
        "required_packages": ["pymongo"]
    },
    {
        "name": "copy_file",
        "description": "Copy a file from source to destination",
        "type": "function",
        "function": "def copy_file(data):\n    import shutil\n    import os\n    try:\n        shutil.copy2(data['source'], data['destination'])\n        return {'status': 'success', 'source': data['source'], 'destination': data['destination']}\n    except FileNotFoundError as e:\n        return {'status': 'error', 'message': str(e), 'source': data['source'], 'destination': data['destination']}",
        "input_schema": {
            "type": "object", 
            "properties": {
                "source": {"type": "string"}, 
                "destination": {"type": "string"}
            }
        },
        "output_schema": {
            "type": "object", 
            "properties": {
                "status": {"type": "string"}, 
                "source": {"type": "string"}, 
                "destination": {"type": "string"},
                "message": {"type": "string"}
            }
        },
        "credentials": [],
        "command": ["python", "copy_file"],
        "language": "python",
        "required_packages": []
    },
    {
        "name": "create_directory",
        "description": "Create a new directory",
        "type": "function",
        "function": "def create_directory(data):\n    import os\n    try:\n        os.makedirs(data['directory_path'], exist_ok=True)\n        return {'status': 'success', 'directory': data['directory_path']}\n    except PermissionError as e:\n        return {'status': 'error', 'message': 'Permission denied', 'directory': data['directory_path']}",
        "input_schema": {
            "type": "object", 
            "properties": {
                "directory_path": {"type": "string"}
            }
        },
        "output_schema": {
            "type": "object", 
            "properties": {
                "status": {"type": "string"}, 
                "directory": {"type": "string"},
                "message": {"type": "string"}
            }
        },
        "credentials": [],
        "command": ["python", "create_directory"],
        "language": "python",
        "required_packages": []
    },
    {
        "name": "log_message",
        "description": "Log a message with timestamp and level",
        "type": "function",
        "function": "def log_message(data):\n    import datetime\n    import logging\n    timestamp = datetime.datetime.now().isoformat()\n    level = data.get('level', 'info').upper()\n    log_entry = f\"[{timestamp}] {level}: {data['message']}\"\n    \n    # Also write to a log file if specified\n    if data.get('log_file'):\n        with open(data['log_file'], 'a') as f:\n            f.write(log_entry + '\\n')\n    \n    return {'status': 'success', 'log_entry': log_entry, 'timestamp': timestamp, 'level': level}",
        "input_schema": {
            "type": "object", 
            "properties": {
                "message": {"type": "string"}, 
                "level": {"type": "string", "default": "info"},
                "log_file": {"type": "string"}
            }
        },
        "output_schema": {
            "type": "object", 
            "properties": {
                "status": {"type": "string"}, 
                "log_entry": {"type": "string"}, 
                "timestamp": {"type": "string"},
                "level": {"type": "string"}
            }
        },
        "credentials": [],
        "command": ["python", "log_message"],
        "language": "python",
        "required_packages": []
    }
]

def insert_tools_into_db():
    """Insert tools into MongoDB with unified schema"""
    db = MongoClient(os.getenv("MONGODB_URI")).vibeflows

    responses = []

    for tool in TOOLS:
        tool["created_at"] = datetime.utcnow()
        response = db.tools.insert_one(tool)
        responses.append(response)

    print(f"Created {len(TOOLS)} tools with unified schema")
    return responses

if __name__ == "__main__":
    insert_tools_into_db()
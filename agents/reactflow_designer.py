#!/usr/bin/env python3
"""
Create React Workflow
====================
Converts design graph to React Flow format and saves to database
"""

from typing import Dict, Any, List
import json
from datetime import datetime
from pymongo import MongoClient
import os

def get_db_connection():
    """Get database connection"""
    mongo_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    database_name = os.getenv("MONGODB_DATABASE", "vibeflows")
    client = MongoClient(mongo_uri)
    db = client[database_name]
    return db

def save_react_flow_to_db(design_graph: Dict[str, Any], react_flow: Dict[str, Any]) -> None:
    """
    Save React Flow design to database collection 'react_flows'
    
    Args:
        design_graph: Original design graph
        react_flow: React Flow design dictionary
    """
    db = get_db_connection()
    react_flows_collection = db.react_flows
    
    # Remove _id from design_graph before copying
    if "_id" in design_graph:
        design_graph.pop("_id")
    
    # Start with design_graph and remove nodes/connections
    react_flow_document = design_graph.copy()
    
    # Remove original nodes and connections
    react_flow_document.pop("nodes", None)
    react_flow_document.pop("connections", None)
    
    # Add React Flow format
    react_flow_document["nodes"] = react_flow.get("nodes", [])
    react_flow_document["edges"] = react_flow.get("edges", [])
    react_flow_document["viewport"] = react_flow.get("viewport", {"x": 0, "y": 0, "zoom": 1})
    
    # Update timestamps
    react_flow_document["updated_at"] = datetime.now()
    react_flow_document["version"] = react_flow_document.get("version", 1) + 1
    
    # Add validation info if present
    if "validation_warnings" in react_flow:
        react_flow_document["validation_warnings"] = react_flow["validation_warnings"]
    
    if "retry_info" in react_flow:
        react_flow_document["retry_info"] = react_flow["retry_info"]
    
    try:
        # Insert document
        react_flows_collection.insert_one(react_flow_document)
        print("React Flow saved successfully")
    except Exception as e:
        print(f"Error saving React Flow to database: {e}")
        raise

def convert_design_to_react_flow(design_graph: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert design graph to React Flow format.
    
    Args:
        design_graph: Design graph dictionary with nodes and connections
        
    Returns:
        Dictionary with React Flow format (nodes, edges, viewport)
    """
    if not design_graph or "nodes" not in design_graph:
        return {
            "nodes": [],
            "edges": [],
            "viewport": {"x": 0, "y": 0, "zoom": 1},
            "error": "Invalid design graph - missing nodes"
        }
    
    nodes = design_graph.get("nodes", [])
    connections = design_graph.get("connections", [])
    
    # Convert nodes to React Flow format
    react_flow_nodes = []
    for node in nodes:
        node_id = node["id"]
        node_type = node.get("type", "default")
        
        # Determine React Flow node type
        rf_type = "input" if node_type == "trigger" else "output" if node_type == "end" else "default"
        if node_type == "condition":
            rf_type = "condition"  # Custom type for condition nodes
        
        # Create node data
        node_data = {
            "label": node.get("name", ""),
            "description": node.get("description", ""),
            "nodeType": node_type
        }
        
        # Add conditions for condition nodes
        if node_type == "condition" and "conditions" in node:
            node_data["conditions"] = node["conditions"]
        
        # Node styling based on type
        node_styles = {
            "trigger": {"background": "#22c55e", "color": "white", "border": "2px solid #22c55e"},
            "process": {"background": "#3b82f6", "color": "white", "border": "2px solid #3b82f6"},
            "condition": {"background": "#f59e0b", "color": "white", "border": "2px solid #f59e0b"},
            "action": {"background": "#8b5cf6", "color": "white", "border": "2px solid #8b5cf6"},
            "integration": {"background": "#06b6d4", "color": "white", "border": "2px solid #06b6d4"},
            "wait": {"background": "#64748b", "color": "white", "border": "2px solid #64748b"},
            "end": {"background": "#dc2626", "color": "white", "border": "2px solid #dc2626"}
        }
        
        react_flow_node = {
            "id": node_id,
            "type": rf_type,
            "position": {"x": 0, "y": 0},  # Will be set by optimization
            "data": node_data,
            "style": node_styles.get(node_type, {}),
            "sourcePosition": "top",
            "targetPosition": "bottom"
        }
        
        react_flow_nodes.append(react_flow_node)
    
    # Convert connections to React Flow edges
    react_flow_edges = []
    for i, conn in enumerate(connections):
        edge_id = f"e{i+1}"
        
        edge = {
            "id": edge_id,
            "source": conn["from"],
            "target": conn["to"],
            "type": "smoothstep",
            "animated": False
        }
        
        # Add label if provided
        if "label" in conn:
            edge["label"] = conn["label"]
        
        # Add sourceHandle for condition nodes if needed
        source_node = next((n for n in nodes if n["id"] == conn["from"]), None)
        if source_node and source_node.get("type") == "condition":
            edge["sourceHandle"] = conn["to"]  # Use target as handle identifier
        
        react_flow_edges.append(edge)
    
    # Create React Flow structure
    react_flow = {
        "nodes": react_flow_nodes,
        "edges": react_flow_edges,
        "viewport": {"x": 0, "y": 0, "zoom": 0.8},
        "description": design_graph.get("description", ""),  # Include description from design
        "name": design_graph.get("name", "")  # Include name from design
    }
    
    return react_flow

def optimize_positions_for_desktop(react_flow: Dict[str, Any]) -> Dict[str, Any]:
    """
    Optimize node positions for desktop viewing with better spacing and organization.
    
    Args:
        react_flow: React Flow design dictionary
        
    Returns:
        Optimized React Flow design with better positioning
    """
    nodes = react_flow.get("nodes", [])
    edges = react_flow.get("edges", [])
    
    if not nodes:
        return react_flow
    
    # Build dependency graph for layering
    from collections import defaultdict, deque
    
    children = defaultdict(list)
    parents = defaultdict(list)
    
    for edge in edges:
        children[edge["source"]].append(edge["target"])
        parents[edge["target"]].append(edge["source"])
    
    # Find root nodes (no parents)
    all_node_ids = {node["id"] for node in nodes}
    root_nodes = [node_id for node_id in all_node_ids if not parents[node_id]]
    
    # If no clear roots, pick trigger/input type nodes
    if not root_nodes:
        root_nodes = [node["id"] for node in nodes 
                     if node.get("type") in ["input"] or 
                        node.get("data", {}).get("nodeType") == "trigger"]
    
    # If still no roots, pick first node
    if not root_nodes and nodes:
        root_nodes = [nodes[0]["id"]]
    
    # Assign layers using BFS
    layers = []
    visited = set()
    current_layer = root_nodes[:]
    
    while current_layer:
        layers.append(current_layer[:])
        next_layer = []
        
        for node_id in current_layer:
            visited.add(node_id)
            for child in children[node_id]:
                if child not in visited and all(p in visited for p in parents[child]):
                    if child not in next_layer:
                        next_layer.append(child)
        
        current_layer = next_layer
    
    # Handle any remaining nodes (cycles or disconnected)
    remaining = all_node_ids - visited
    if remaining:
        layers.append(list(remaining))
    
    # Desktop-optimized positioning
    desktop_config = {
        "start_x": 100,           # Left margin
        "start_y": 50,            # Top margin  
        "horizontal_spacing": 350, # Space between nodes horizontally
        "vertical_spacing": 200,   # Space between layers
        "max_width": 1600,        # Maximum workflow width
        "node_width": 250,        # Estimated node width
        "condition_extra_space": 100  # Extra space for condition nodes
    }
    
    # Create node ID to node mapping
    node_map = {node["id"]: node for node in nodes}
    
    # Position nodes layer by layer
    for layer_idx, layer in enumerate(layers):
        y = desktop_config["start_y"] + (layer_idx * desktop_config["vertical_spacing"])
        
        # Calculate layer width and starting position
        layer_node_count = len(layer)
        
        # Check for condition nodes in this layer (need extra space)
        condition_nodes = [node_id for node_id in layer 
                          if node_map.get(node_id, {}).get("data", {}).get("nodeType") == "condition"]
        
        # Adjust spacing for condition nodes
        spacing = desktop_config["horizontal_spacing"]
        if condition_nodes:
            spacing += desktop_config["condition_extra_space"]
        
        # Calculate total layer width
        total_layer_width = (layer_node_count - 1) * spacing if layer_node_count > 1 else 0
        
        # Center the layer horizontally
        if total_layer_width > desktop_config["max_width"]:
            # If layer is too wide, reduce spacing
            spacing = desktop_config["max_width"] // layer_node_count if layer_node_count > 1 else spacing
            total_layer_width = (layer_node_count - 1) * spacing
        
        start_x = desktop_config["start_x"] + max(0, (desktop_config["max_width"] - total_layer_width) // 2)
        
        # Position each node in the layer
        for node_idx, node_id in enumerate(layer):
            if node_id in node_map:
                x = start_x + (node_idx * spacing)
                
                # Ensure positions are on 50px grid
                x = round(x / 50) * 50
                y_grid = round(y / 50) * 50
                
                # Update node position
                node_map[node_id]["position"] = {"x": x, "y": y_grid}
    
    # Update viewport for desktop viewing
    react_flow["viewport"] = {
        "x": 0,
        "y": 0, 
        "zoom": 0.8  # Slightly zoomed out for desktop overview
    }
    
    return react_flow

def validate_react_flow_design(design: Dict[str, Any]) -> List[str]:
    """
    Validate React Flow design for common issues.
    
    Args:
        design: React Flow design dictionary
        
    Returns:
        List of validation warnings/errors
    """
    warnings = []
    
    # Check required structure
    required_keys = ["nodes", "edges"]  # Simplified required keys
    missing_keys = [k for k in required_keys if k not in design]
    if missing_keys:
        warnings.append(f"Missing required keys: {', '.join(missing_keys)}")
        return warnings
    
    nodes = design.get("nodes", [])
    edges = design.get("edges", [])
    
    if not nodes:
        warnings.append("No nodes defined")
        return warnings
    
    # Check node structure
    node_ids = {node["id"] for node in nodes}
    for node in nodes:
        required_node_fields = ["id", "type", "position", "data"]
        missing_fields = [f for f in required_node_fields if f not in node]
        if missing_fields:
            warnings.append(f"Node {node.get('id', 'unknown')} missing fields: {', '.join(missing_fields)}")
    
    # Check edge references
    for edge in edges:
        if edge["source"] not in node_ids:
            warnings.append(f"Edge {edge['id']} references non-existent source: {edge['source']}")
        if edge["target"] not in node_ids:
            warnings.append(f"Edge {edge['id']} references non-existent target: {edge['target']}")
    
    # Check for overlapping positions
    positions = [(node["position"]["x"], node["position"]["y"]) for node in nodes if "position" in node]
    if len(positions) != len(set(positions)):
        warnings.append("Some nodes have overlapping positions")
    
    return warnings

def create_and_save_react_workflow(design_graph: Dict[str, Any]) -> Dict[str, Any]:
    """
    Save React Flow design to database
    
    Args:
        design_graph: Design graph dictionary with nodes and connections
        
    Returns:
        React Flow design dictionary
    """
    # Convert design graph to React Flow
    react_flow = convert_design_to_react_flow(design_graph)
    
    # Save to database
    try:
        save_react_flow_to_db(design_graph, react_flow)
        react_flow["saved_to_db"] = True
    except Exception as e:
        print(f"Failed to save React Flow to database: {e}")
        react_flow["save_error"] = str(e)
        react_flow["saved_to_db"] = False
    
    return react_flow

# Usage example
if __name__ == "__main__":
    # Convert design graph to React Flow workflow
    design_graph = {
        "name": "Sample Workflow",
        "description": "Sample workflow description",
        "nodes": [
            {
                "id": "start",
                "name": "Start Process",
                "type": "trigger",
                "description": "Initial trigger"
            }
        ],
        "connections": [
            {
                "from": "start",
                "to": "process",
                "label": "Begin"
            }
        ]
    }
    
    result = create_and_save_react_workflow(design_graph)
    print(f"Created React Flow workflow: {result.get('json', {}).get('_id', 'No ID')}")
#!/usr/bin/env python3
"""
Mermaid Designer Agent
======================
Creates visual mermaid workflow diagrams from user requirements.
"""

from typing import Dict, Any, List
from agents.llm_inference import run_inference

SYSTEM = """
You are the Mermaid Designer agent for VibeFlows, specialized in creating visual workflow diagrams.

Pay attention. Sometimes we provide the context of the last understanding and mermaid diagram. 
And if you need to make changes, the chanegs should consider the context, not random. 

<role>
Your job is to convert user requirements into beautiful, clear mermaid flowchart diagrams that visualize their marketing automation workflow.
</role>

<task>
Based on the user's requirements analysis, create a mermaid flowchart that shows:
1. Trigger points (form submissions, emails, etc.)
2. Data processing steps (enrichment, scoring, etc.) 
3. Decision points with clear conditions
4. Actions (send emails, create tasks, notifications)
5. Integrations with specific platforms
6. Flow logic and loops
</task>

<mermaid_guidelines>
- Use "flowchart TD" for top-down diagrams
- Use appropriate node shapes:
  - [Square] for actions/processes
  - {Diamond} for decisions/conditions
  - ((Circle)) for start/end points
- Include emojis in labels for visual appeal
- Use clear, descriptive labels
- Show conditional flows with |condition text|
- Add styling with colors for different node types
- Keep diagrams clean and easy to follow
</mermaid_guidelines>

<output_format>
Respond with ONLY the mermaid diagram code. No explanations, no markdown code blocks, just the raw mermaid syntax that can be directly used.

Start with "flowchart TD" and include proper spacing and styling.
</output_format>

<example_structure>
flowchart TD
    A[🔗 Trigger] --> B{Condition?}
    B -->|Yes| C[✅ Action]
    B -->|No| D[❌ Alternative]
    
    %% Styling
    style A fill:#e3f2fd,stroke:#1976d2,stroke-width:2px
    style C fill:#e8f5e8,stroke:#388e3c,stroke-width:2px
</example_structure>
"""

def create_mermaid_diagram(context: Dict[str, Any], model_name="claude-sonnet-4-20250514") -> str:
    """
    Create a mermaid diagram from user requirements.
    
    Args:
        understanding_result: JSON from understanding agent
        model_name: LLM model to use
        
    Returns:
        Mermaid diagram string
    """

    messages = [{"role": "system", "content": SYSTEM}]
    if "last_understanding" in context:
        messages.append({"role": "assistant", "content": str(context["last_understanding"])})
    if "last_mermaid" in context:
        messages.append({"role": "assistant", "content": str(context["last_mermaid"])})
    if "current_mermaid" in context:
        messages.append({"role": "assistant", "content": str(context["current_mermaid"])})
    if "current_understanding" in context:
        messages.append({"role": "assistant", "content": str(context["current_understanding"])})  
    if "user_message" in context:
        messages.append({"role": "user", "content": str(context["user_message"])})
    
    messages.append({"role": "user", "content": "Create a mermaid diagram or update the existing one based on the user requirements and the context."})
    
    try:
        mermaid_diagram = run_inference(messages, model_name=model_name)
        return mermaid_diagram.strip()
    except Exception as e:
        # Fallback diagram if LLM fails
        return "ERROR: Failed to create mermaid diagram"

def generate_workflow_description(mermaid_diagram, model_name="claude-sonnet-4-20250514") -> str:
    """
    Generate a user-friendly description of the workflow.
    
    Args:
        understanding_result: JSON from understanding agent
        model_name: LLM model to use
        
    Returns:
        Workflow description string
    """
    
    description_prompt = f"""
Based on this mermaid diagram: {mermaid_diagram}

Write a friendly, 2-3 sentence description of what this workflow will do for the user. 

Focus on the business benefits and outcomes.

Respond with ONLY the description of diagram in plain langauge. 

No long explanations, Markdown is fine. Don't ask questions.
"""
    
    messages = [
        {"role": "system", "content": "You are a helpful assistant that explains marketing workflows in simple, benefit-focused language."},
        {"role": "user", "content": description_prompt}
    ]
    
    try:
        description = run_inference(messages, model_name=model_name)
        return description.strip()
    except Exception as e:
        return "Error: Mermaid desc."

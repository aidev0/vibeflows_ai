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

def create_mermaid_diagram(understanding_result: Dict[str, Any], model_name="claude-sonnet-4-20250514") -> str:
    """
    Create a mermaid diagram from user requirements.
    
    Args:
        understanding_result: JSON from understanding agent
        model_name: LLM model to use
        
    Returns:
        Mermaid diagram string
    """
    
    # Extract key information
    project_type = understanding_result.get('project_type', 'workflow')
    summary = understanding_result.get('summary', 'Marketing automation workflow')
    requirements = understanding_result.get('requirements', [])
    tech_preferences = understanding_result.get('tech_preferences', [])
    constraints = understanding_result.get('constraints', {})
    
    # Create context for the designer
    context = f"""
User wants to create: {summary}

Project type: {project_type}

Requirements:
{chr(10).join(f'- {req}' for req in requirements)}

Technologies mentioned:
{chr(10).join(f'- {tech}' for tech in tech_preferences)}

Constraints:
{chr(10).join(f'- {k}: {v}' for k, v in constraints.items() if v)}

Create a mermaid flowchart diagram that visualizes this marketing automation workflow.
"""
    
    # Prepare messages for LLM
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": context}
    ]
    
    try:
        mermaid_diagram = run_inference(messages, model_name=model_name)
        return mermaid_diagram.strip()
    except Exception as e:
        # Fallback diagram if LLM fails
        return create_fallback_diagram(summary, requirements, tech_preferences)

def create_fallback_diagram(summary: str, requirements: List[str], tech_preferences: List[str]) -> str:
    """Create a basic fallback diagram if LLM fails."""
    
    # Determine main components based on requirements
    has_email = any('email' in req.lower() for req in requirements)
    has_crm = any('crm' in req.lower() or any(tech.lower() in ['hubspot', 'salesforce', 'pipedrive'] for tech in tech_preferences) for req in requirements)
    has_social = any('social' in req.lower() for req in requirements)
    has_analytics = any('analytics' in req.lower() or 'tracking' in req.lower() for req in requirements)
    
    # Build diagram based on detected components
    diagram = """flowchart TD
    A[🎯 Marketing Trigger] --> B{Data Available?}
    B -->|Yes| C[📊 Process Data]
    B -->|No| D[📝 Collect Information]
    
    D --> C
    C --> E{Qualification Check}
    
    E -->|Qualified| F[✅ Primary Action]
    E -->|Not Qualified| G[🔄 Nurture Process]"""
    
    # Add email flow if detected
    if has_email:
        diagram += """
    
    F --> H[📧 Email Campaign]
    G --> I[📧 Nurture Emails]"""
    
    # Add CRM integration if detected
    if has_crm:
        diagram += """
    
    H --> J[💾 Update CRM]
    I --> J"""
    
    # Add social media if detected
    if has_social:
        diagram += """
    
    J --> K[📱 Social Media Post]"""
    
    # Add analytics if detected
    if has_analytics:
        diagram += """
    
    K --> L[📈 Track Analytics]"""
    else:
        diagram += """
    
    J --> L[📈 Track Results]"""
    
    # Add styling
    diagram += """
    
    %% Styling
    style A fill:#e3f2fd,stroke:#1976d2,stroke-width:2px
    style F fill:#e8f5e8,stroke:#388e3c,stroke-width:2px
    style G fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    style L fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
    
    %% Process styling
    style C fill:#e1f5fe,stroke:#0277bd,stroke-width:2px"""
    
    if has_email:
        diagram += """
    style H fill:#ffebee,stroke:#d32f2f,stroke-width:2px
    style I fill:#ffebee,stroke:#d32f2f,stroke-width:2px"""
    
    return diagram

def generate_workflow_description(understanding_result: Dict[str, Any], model_name="claude-sonnet-4-20250514") -> str:
    """
    Generate a user-friendly description of the workflow.
    
    Args:
        understanding_result: JSON from understanding agent
        model_name: LLM model to use
        
    Returns:
        Workflow description string
    """
    
    summary = understanding_result.get('summary', 'Your marketing automation')
    requirements = understanding_result.get('requirements', [])
    
    description_prompt = f"""
Based on this marketing automation request: {summary}

Key requirements: {', '.join(requirements)}

Write a friendly, 2-3 sentence description of what this workflow will do for the user. Focus on the business benefits and outcomes.
"""
    
    messages = [
        {"role": "system", "content": "You are a helpful assistant that explains marketing workflows in simple, benefit-focused language."},
        {"role": "user", "content": description_prompt}
    ]
    
    try:
        description = run_inference(messages, model_name=model_name)
        return description.strip()
    except Exception as e:
        return f"This workflow will automate your {summary.lower()}, saving you time and ensuring consistent execution of your marketing processes."

def update_mermaid_diagram(current_diagram: str, user_feedback: str, understanding_result: Dict[str, Any], model_name="claude-sonnet-4-20250514") -> str:
    """
    Update an existing mermaid diagram based on user feedback.
    
    Args:
        current_diagram: Current mermaid diagram
        user_feedback: User's change requests
        understanding_result: Original requirements
        model_name: LLM model to use
        
    Returns:
        Updated mermaid diagram string
    """
    
    update_prompt = f"""
Current mermaid diagram:
{current_diagram}

User feedback: {user_feedback}

Original requirements summary: {understanding_result.get('summary', '')}

Update the mermaid diagram based on the user feedback while maintaining the same structure and styling. 
Respond with ONLY the updated mermaid diagram code.
"""
    
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": update_prompt}
    ]
    
    try:
        updated_diagram = run_inference(messages, model_name=model_name)
        return updated_diagram.strip()
    except Exception as e:
        print(f"Error updating diagram: {e}")
        # Return original diagram if update fails
        return current_diagram

# Test function
def test_mermaid_designer():
    """Test the mermaid designer with sample data."""
    
    print("🧪 Testing Mermaid Designer Agent")
    print("=" * 40)
    
    # Sample understanding result
    sample_understanding = {
        "project_type": "workflow",
        "summary": "Automate lead generation and qualification for B2B SaaS company",
        "requirements": [
            "capture leads from website forms",
            "enrich lead data automatically", 
            "score leads based on company size and industry",
            "send qualified leads to sales team",
            "nurture unqualified leads with email campaigns"
        ],
        "tech_preferences": ["HubSpot", "Mailchimp", "Slack"],
        "constraints": {
            "timeline": "2 weeks",
            "budget": "startup",
            "scale": "100 leads per month"
        },
        "confidence": 0.85
    }
    
    # Test diagram creation
    print("Creating mermaid diagram...")
    diagram = create_mermaid_diagram(sample_understanding)
    print("\nGenerated Diagram:")
    print(diagram)
    
    # Test description generation
    print("\n" + "=" * 40)
    print("Creating workflow description...")
    description = generate_workflow_description(sample_understanding)
    print("\nGenerated Description:")
    print(description)
    
    # Test diagram update
    print("\n" + "=" * 40)
    print("Testing diagram update...")
    feedback = "Add a step to send notifications to Slack when high-value leads are identified"
    updated_diagram = update_mermaid_diagram(diagram, feedback, sample_understanding)
    print("\nUpdated Diagram:")
    print(updated_diagram)

if __name__ == "__main__":
    test_mermaid_designer()
import logging
from typing import Dict, Any
from template_examples import previous_correspondence
from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)

def generate_templates(llm_client, analysis: Dict[str, Any], request_number: str) -> Dict[str, Dict[str, str]]:
    """
    Generate message templates based on request analysis.
    """
    try:
        # Extract context from analysis
        context = _extract_context(analysis, request_number)
        
        # Generate templates for each type
        templates = {}
        template_configs = [
            ("1", "status_update", "Status Update Request"),
            ("2", "additional_info", "Additional Information"),
            ("3", "clarification", "Request Clarification"),
            ("4", "thank_you", "Thank You")
        ]
        
        for key, template_type, subject_base in template_configs:
            try:
                template = _generate_single_template(llm_client, template_type, context, subject_base)
                templates[key] = template
            except Exception as e:
                logger.warning(f"Failed to generate {template_type} template: {e}")
                templates[key] = _get_fallback_template(template_type, subject_base, context)
        
        return templates
        
    except Exception as e:
        logger.error(f"AI template generation failed: {e}")
        return _get_all_fallback_templates()


def _extract_context(analysis, request_number: str) -> Dict[str, Any]:
    """Extract relevant context from RequestDetailAnalysis object"""
    
    contact_name = _extract_contact_name(analysis.staff_contact)
    
    return {
        "request_number": request_number,
        "status": analysis.current_status,
        "contact_name": contact_name,
        "contact_info": analysis.staff_contact,
        "completion": analysis.estimated_completion,
        "action_required": "YES" if analysis.action_required else "NO",
        "action_description": analysis.action_description,
        "correspondence_summary": analysis.correspondence_summary,
        "timeline": analysis.timeline_summary,
        "key_insights": analysis.key_insights,
        "next_steps": analysis.next_steps,
        "documents_available": analysis.documents_available,
        "outstanding_payments": analysis.outstanding_payments,
        "last_timeline_entry": _get_last_timeline_entry(analysis.timeline_summary),
        "full_analysis": analysis
    }

def _extract_contact_name(contact_string: str) -> str:
    """Extract contact name from contact information"""
    if not contact_string:
        return ""
    
    # Handle format like "Law Admin 09 (City Attorney's Office)"
    if "(" in contact_string:
        name_part = contact_string.split("(")[0].strip()
        return name_part
    
    # Handle comma-separated format
    parts = contact_string.split(",")
    if parts:
        return parts[0].strip()
    
    return contact_string.strip()

def _get_last_timeline_entry(timeline) -> str:
    """Get the most recent timeline entry"""
    if not timeline:
        return ""
    
    if isinstance(timeline, list) and len(timeline) > 0:
        return timeline[-1]
    elif isinstance(timeline, str):
        return timeline
    
    return ""

def _generate_single_template(llm_client, template_type: str, context: Dict[str, Any], subject_base: str) -> Dict[str, str]:
    """Generate a single template using the LLM"""
    
    prompt = _build_comprehensive_prompt(template_type, context, subject_base)
    
    try:
        messages = [
            SystemMessage(content=prompt),
            HumanMessage(content=f"Generate a {template_type} message for request {context['request_number']}.")
        ]
        
        response = llm_client.invoke(messages)
        
        return _parse_llm_response(response.content, subject_base, context)
        
    except Exception as e:
        logger.error(f"LLM call failed for {template_type}: {e}")
        raise

def _build_comprehensive_prompt(template_type: str, context: Dict[str, Any], subject_base: str) -> str:
    """Build a comprehensive AI prompt with all available context"""
    
    # Format timeline for better readability
    timeline_text = ""
    if context['timeline']:
        if isinstance(context['timeline'], list):
            timeline_text = "\n".join([f"   • {entry}" for entry in context['timeline']])
        else:
            timeline_text = str(context['timeline'])
    
    # Format key insights
    key_insights_text = ""
    if context['key_insights']:
        if isinstance(context['key_insights'], list):
            key_insights_text = "\n".join([f"   • {insight}" for insight in context['key_insights']])
        else:
            key_insights_text = str(context['key_insights'])
    
    comprehensive_prompt = f"""
You are generating a professional follow-up message for a public records request. You must create a contextually appropriate, professional message based on the specific situation described below.

IMPORTANT: You are NOT writing as the "California Reporting Project" or any specific organization. The examples below are ONLY provided as gold standard examples of professional tone and style. Do NOT reference California Reporting Project, Katey Rusch, or any specific organization names in your response.

GOLD STANDARD CORRESPONDENCE EXAMPLES (for tone and style reference only):
{previous_correspondence}

CURRENT REQUEST ANALYSIS - USE THIS CONTEXT:
================================================================
📊 Request Number: {context['request_number']}
📈 Status: {context['status']}
⚡ Action Required: {context['action_required']}
👤 Contact: {context['contact_info']}
⏰ Completion: {context['completion']}

📋 CORRESPONDENCE SUMMARY:
{context['correspondence_summary']}

📅 TIMELINE:
{timeline_text}

💡 KEY INSIGHTS:
{key_insights_text}

🎯 NEXT STEPS: {context['next_steps']}
================================================================

WRITING GUIDELINES:
1. Be professional and concise like the gold standard examples
2. Reference the specific request number: {context['request_number']}
3. Address the contact by name if available: {context['contact_name']}
4. Use the timeline and key insights to inform your message appropriately
5. Consider the current status and whether action is required
6. Match the professional tone of the examples but DO NOT copy organization-specific details
7. End with "Best regards" or similar professional closing
8. Keep the message focused and relevant to the current situation

"""

    if template_type == "status_update":
        specific_prompt = f"""
MESSAGE TYPE: Status Update Request

CONTEXT ANALYSIS:
- Current Status: {context['status']}
- Action Required: {context['action_required']}
- Last Communication: {context['last_timeline_entry']}
- Key Situation: {key_insights_text}

TASK: Generate a professional status update request that:
1. Acknowledges the current situation based on the timeline and key insights
2. Asks for an appropriate status update given the context
3. References recent communication if relevant
4. Shows understanding of the process stage
5. Is appropriately timed based on the last communication

Consider:
- If the request shows "NO action required" and recent activity, acknowledge their work
- If there's been a long gap, politely inquire about progress
- If there are specific insights about delays or issues, address them appropriately
- Reference the specific request details and timeline context

Subject should reference the request number: {context['request_number']}
"""
    
    elif template_type == "additional_info":
        specific_prompt = f"""
MESSAGE TYPE: Additional Information

CONTEXT ANALYSIS:
- Current Status: {context['status']}
- Correspondence Summary: {context['correspondence_summary']}
- Key Context: {key_insights_text}

TASK: Generate a message offering additional information that:
1. References the current status and any relevant timeline events
2. Acknowledges ongoing work if applicable
3. Offers to provide additional helpful information
4. Is contextually appropriate to the current stage of the request
5. Leaves clear space for the user to add their specific additional details

Consider:
- The current processing stage
- Any complexities mentioned in key insights
- Whether clarification might help with identified issues
- The relationship established in prior correspondence

Subject should reference the request number: {context['request_number']}
"""
    
    elif template_type == "clarification":
        specific_prompt = f"""
MESSAGE TYPE: Request Clarification

CONTEXT ANALYSIS:
- Current Status: {context['status']}
- Action Required: {context['action_required']}
- Process Context: {context['correspondence_summary']}
- Key Insights: {key_insights_text}

TASK: Generate a clarification request that:
1. Shows understanding of the current situation
2. Asks for clarification in a way that's relevant to the current context
3. References any specific issues or complexities from the key insights
4. Demonstrates awareness of the timeline and current status
5. Offers to provide additional details if helpful

Consider:
- Specific challenges or complexities mentioned in the analysis
- The current stage of processing
- Any areas where clarification might genuinely help
- Recent communications and their context

Subject should reference the request number: {context['request_number']}
"""
    
    elif template_type == "thank_you":
        specific_prompt = f"""
MESSAGE TYPE: Thank You Message

CONTEXT ANALYSIS:
- Recent Activity: {context['last_timeline_entry']}
- Current Status: {context['status']}
- Key Work Done: {key_insights_text}
- Contact: {context['contact_name']}

TASK: Generate a genuine thank you message that:
1. Specifically acknowledges recent work or updates mentioned in the timeline
2. References appropriate details from the key insights about work being done
3. Shows appreciation for specific efforts (like reviving dormant requests, compilation work, etc.)
4. Is genuine and contextually relevant
5. Acknowledges the current status appropriately

Consider:
- Specific work mentioned in recent timeline entries
- Efforts described in the key insights
- The complexity or effort involved based on the analysis
- Personal touches like using the contact's name
- Recent positive developments in the process

Subject should reference the request number: {context['request_number']}
"""
    
    return comprehensive_prompt + "\n" + specific_prompt + "\n\nGenerate a complete, professional message. Return ONLY the subject line and message body in this exact format:\nSUBJECT: [subject here]\nMESSAGE: [message here]"

def _parse_llm_response(response: str, fallback_subject: str, context: Dict[str, Any]) -> Dict[str, str]:
    """Parse LLM response into subject and message"""
    try:
        lines = response.strip().split('\n')
        subject = fallback_subject
        message_lines = []
        
        in_message = False
        
        for line in lines:
            line = line.strip()
            if line.upper().startswith('SUBJECT:'):
                subject = line.split(':', 1)[1].strip()
            elif line.upper().startswith('MESSAGE:'):
                in_message = True
                message_content = line.split(':', 1)[1].strip()
                if message_content:
                    message_lines.append(message_content)
            elif in_message and line:
                message_lines.append(line)
        
        message = '\n'.join(message_lines).strip()
        
        # Ensure we have content
        if not message:
            return _get_fallback_template("generic", fallback_subject, context)
        
        return {
            "subject": subject,
            "message": message
        }
        
    except Exception as e:
        logger.error(f"Failed to parse LLM response: {e}")
        return _get_fallback_template("generic", fallback_subject, context)

def _get_fallback_template(template_type: str, subject: str, context: Dict[str, Any]) -> Dict[str, str]:
    """Get fallback template if AI generation fails"""
    
    contact_greeting = f"Hello {context['contact_name']}," if context['contact_name'] else "Hello,"
    request_ref = f" regarding request {context['request_number']}" if context['request_number'] else ""
    
    fallbacks = {
        "status_update": {
            "subject": f"Status Update Request - {context['request_number']}",
            "message": f"{contact_greeting}\n\nI am writing to inquire about the status of my public records request{request_ref}. Could you please provide an update on the progress and expected completion timeline?\n\nThank you for your time and assistance.\n\nBest regards"
        },
        "additional_info": {
            "subject": f"Additional Information - {context['request_number']}",
            "message": f"{contact_greeting}\n\nI wanted to provide additional information that may help with processing my request{request_ref}:\n\n[Please add your additional details here]\n\nThank you for your assistance.\n\nBest regards"
        },
        "clarification": {
            "subject": f"Request Clarification - {context['request_number']}",
            "message": f"{contact_greeting}\n\nI would like to clarify my request{request_ref} to ensure you have all the necessary information:\n\n[Please add your clarification here]\n\nPlease let me know if you need any additional details.\n\nBest regards"
        },
        "thank_you": {
            "subject": f"Thank You - {context['request_number']}",
            "message": f"{contact_greeting}\n\nThank you for your work on processing my public records request{request_ref}. I appreciate your time and effort.\n\nBest regards"
        }
    }
    
    return fallbacks.get(template_type, {
        "subject": subject,
        "message": f"{contact_greeting}\n\nRegarding my public records request{request_ref}.\n\nBest regards"
    })

def _get_all_fallback_templates() -> Dict[str, Dict[str, str]]:
    """Return all fallback templates if everything fails"""
    return {
        "1": {
            "subject": "Request Status Update",
            "message": "Hello,\n\nI am writing to inquire about the status of my public records request. Could you please provide an update on the progress and expected completion timeline?\n\nThank you for your time and assistance.\n\nBest regards"
        },
        "2": {
            "subject": "Additional Information",
            "message": "Hello,\n\nI wanted to provide additional information that may help with processing my request:\n\n[Please add your additional details here]\n\nThank you for your assistance.\n\nBest regards"
        },
        "3": {
            "subject": "Request Clarification",
            "message": "Hello,\n\nI would like to clarify my request to ensure you have all the necessary information:\n\n[Please add your clarification here]\n\nPlease let me know if you need any additional details.\n\nBest regards"
        },
        "4": {
            "subject": "Thank You",
            "message": "Hello,\n\nThank you for your work on processing my public records request. I appreciate your time and effort.\n\nBest regards"
        }
    }
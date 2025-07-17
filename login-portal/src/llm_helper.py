import base64
import logging
from typing import Dict, Any, List
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)

class RequestTableAnalysis(BaseModel):
    """Model for analyzing the requests table page"""
    total_requests_found: int = Field(description="Number of requests visible in table")
    request_numbers: List[str] = Field(description="List of request numbers found")
    requests_with_issues: List[str] = Field(description="Request numbers that appear to need attention")
    table_structure_understood: bool = Field(description="Whether the table structure was properly identified")
    navigation_elements: List[str] = Field(description="Available navigation or action elements")
    quick_insights: List[str] = Field(description="Quick insights about the requests visible")

class RequestDetailAnalysis(BaseModel):
    """Model for analyzing individual request detail pages"""
    request_number: str = Field(description="Request number being analyzed")
    current_status: str = Field(description="Current status in plain language")
    action_required: bool = Field(description="Whether user action is needed")
    action_description: str = Field(description="What action is needed if any")
    timeline_summary: List[str] = Field(description="Key timeline events in chronological order")
    correspondence_summary: str = Field(description="Summary of all correspondence")
    documents_available: List[str] = Field(description="Documents ready for download")
    outstanding_payments: List[str] = Field(description="Any fees or invoices due")
    staff_contact: str = Field(description="Point of contact information")
    estimated_completion: str = Field(description="When request might be completed")
    key_insights: List[str] = Field(description="Important insights user should know")
    next_steps: str = Field(description="What the user should do next")

class MultiRequestSummary(BaseModel):
    """Model for summarizing multiple requests"""
    total_requests: int = Field(description="Total number of requests analyzed")
    urgent_requests: List[str] = Field(description="Requests needing immediate attention")
    completed_requests: List[str] = Field(description="Requests that are completed")
    waiting_requests: List[str] = Field(description="Requests waiting for agency response")
    overall_status: str = Field(description="Overall status of all requests")
    recommended_actions: List[str] = Field(description="Recommended actions for the user")
    summary: str = Field(description="Executive summary of all request activity")

class LLMHelper:
    """LLM helper specifically designed for Phase 3 request analysis"""
    
    def __init__(self, llm_client):
        self.llm_client = llm_client
    
    def analyze_requests_table_page(self, screenshot_base64: str, page_text: str) -> RequestTableAnalysis:
        """Analyze the 'All requests' table page using multimodal LLM"""
        
        analysis_prompt = """
        You are analyzing a screenshot of the "All requests" page from a public records portal.
        
        This page shows a table with multiple public records requests. Your job is to:
        
        1. **Count the requests**: How many requests are visible in the table?
        2. **Extract request numbers**: What are the request IDs/numbers shown?
        3. **Identify status issues**: Which requests appear to need attention (look for warning colors, "action required" status, etc.)?
        4. **Understand table structure**: Can you identify the columns (Request, Status, Description, Department, Contact, etc.)?
        5. **Find navigation elements**: What buttons, links, or actions are available?
        6. **Provide quick insights**: What stands out about these requests?
        
        Look carefully at:
        - Request numbers (usually clickable links like "25-370")
        - Status indicators (open, closed, pending, action required)
        - Any visual cues about urgency (colors, icons, alerts)
        - Available actions (buttons, links, filters)
        - Overall patterns in the requests
        
        Focus on actionable information that would help the user understand their request portfolio.
        """
        
        try:
            structured_llm = self.llm_client.with_structured_output(RequestTableAnalysis)
            
            messages = [
                SystemMessage(content=analysis_prompt),
                HumanMessage(content=[
                    {
                        "type": "text",
                        "text": f"Analyze this requests table page. Here's some page text for context:\n\n{page_text[:1500]}...\n\nPlease provide a comprehensive analysis of what you see."
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{screenshot_base64}"
                        }
                    }
                ])
            ]
            
            result = structured_llm.invoke(messages)
            logger.info(f"Requests table analysis completed. Found {result.total_requests_found} requests")
            return result
            
        except Exception as e:
            logger.error(f"Failed to analyze requests table: {str(e)}")
            return RequestTableAnalysis(
                total_requests_found=0,
                request_numbers=[],
                requests_with_issues=[],
                table_structure_understood=False,
                navigation_elements=[],
                quick_insights=[f"Analysis failed: {str(e)}"]
            )
    
    def analyze_request_detail_page(self, screenshot_base64: str, page_text: str, request_number: str = "") -> RequestDetailAnalysis:
        """Analyze individual request detail page using multimodal LLM"""
        
        analysis_prompt = f"""
        <role>
        You are an expert analyst for public records request management systems. Your job is to analyze detailed request views and provide clear, actionable summaries for users.
        </role>

        <task>
        Analyze the screenshot of public records request {request_number} and provide a comprehensive summary following the specified format and guidelines.
        </task>

        <thinking_process>
        Before writing your response, think through:
        1. What is the current status and what does it mean for the user?
        2. Who are the key players in this request (user vs staff vs other parties)?
        3. What is the chronological flow of events and communications?
        4. What actions, if any, does the user need to take?
        5. What are the most important insights the user should understand?
        6. What should happen next and when?
        </thinking_process>

        <analysis_framework>
        Extract and analyze the following elements:

        1. **Current Status**: Active/Open/Closed/On Hold/Completed
        2. **Action Required**: YES/NO - Does user need to respond or take action?
        3. **Staff Contact**: Who is handling the request and their department
        4. **Timeline Analysis**: Chronological events with proper attribution
        5. **Correspondence Summary**: Key messages exchanged
        6. **Document Status**: Available files, invoices, payments due
        7. **Completion Assessment**: Expected timeline and next milestones
        8. **Key Insights**: Important patterns or issues to note
        9. **Next Steps**: Specific recommendations for the user
        </analysis_framework>

        <formatting_requirements>
        - Use "You:" for messages from the requester
        - Use "Staff:" for messages from government personnel
        - Use proper names when available (e.g., "Law Admin 09:", "John Smith:")
        - Include dates in format: [Month Day, Year]
        - Use clear visual hierarchy with emojis and formatting
        - Provide actionable, specific recommendations
        </formatting_requirements>

        <examples>
        <example_1>
        **Input**: Request shows requester sent follow-up on March 15, staff responded March 20 saying they need more details, requester hasn't responded yet.

        **Output Timeline**:
        • March 15, 2024: You sent a follow-up inquiry about the status
        • March 20, 2024: Staff (Records Clerk) responded requesting additional details about the date range needed
        • **Action Required**: YES - You need to respond with the requested clarification

        **Next Steps**: Reply to staff with the specific date range or additional details they requested.
        </example_1>

        <example_2>
        **Input**: Request shows completed with documents ready, invoice paid, download link available.

        **Output Timeline**:
        • January 5, 2024: You submitted the original request
        • February 12, 2024: Staff (Legal Department) notified you that documents were ready and sent invoice
        • February 15, 2024: You paid the invoice ($25.00)
        • February 16, 2024: Staff provided download link for requested documents
        • **Action Required**: NO - Documents are ready for download

        **Next Steps**: Download your documents using the provided link. Request is complete.
        </example_2>
        </examples>

        <output_format>
        ANALYSIS SUMMARY FOR REQUEST {request_number}
        ======================================================================
        Status: [Current Status]
        Action Required: [YES/NO]
        Contact: [Staff Name, Department]
        Completion: [Expected timeline or completion status]

        CORRESPONDENCE SUMMARY:
        [Brief overview of key communications and current state]

        TIMELINE:
        [Chronological list with proper attribution using "You:" and "Staff:" or proper names]

        KEY INSIGHTS:
        [Important patterns, delays, issues, or notable aspects]

        NEXT STEPS: 
        [Specific, actionable recommendations for the user]
        </output_format>

        <quality_checklist>
        - [ ] Timeline uses proper attribution (You: vs Staff: vs proper names)
        - [ ] All dates are included and chronologically ordered
        - [ ] Action required is clearly stated (YES/NO)
        - [ ] Next steps are specific and actionable
        - [ ] Key insights highlight important patterns or issues
        - [ ] Contact information is clearly identified
        - [ ] Status assessment is accurate based on available information
        </quality_checklist>

        Analyze the provided screenshot following these guidelines and provide a comprehensive summary.
        """

        try:
            structured_llm = self.llm_client.with_structured_output(RequestDetailAnalysis)
            
            messages = [
                SystemMessage(content=analysis_prompt),
                HumanMessage(content=[
                    {
                        "type": "text",
                        "text": f"Analyze this request detail page for request {request_number}. Here's the page text:\n\n{page_text[:2500]}...\n\nPlease provide a comprehensive analysis focusing on status, actions needed, and key insights."
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{screenshot_base64}"
                        }
                    }
                ])
            ]
            
            result = structured_llm.invoke(messages)
            logger.info(f"Request detail analysis completed for {request_number}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to analyze request detail: {str(e)}")
            return RequestDetailAnalysis(
                request_number=request_number,
                current_status="Analysis failed",
                action_required=False,
                action_description="",
                timeline_summary=[],
                correspondence_summary=f"Could not analyze: {str(e)}",
                documents_available=[],
                outstanding_payments=[],
                staff_contact="Unknown",
                estimated_completion="Unknown",
                key_insights=[f"Analysis error: {str(e)}"],
                next_steps="Manually review the request"
            )
    
    def generate_multi_request_summary(self, individual_analyses: List[RequestDetailAnalysis]) -> MultiRequestSummary:
        """Generate overall summary across multiple requests using text LLM"""
        
        if not individual_analyses:
            return MultiRequestSummary(
                total_requests=0,
                urgent_requests=[],
                completed_requests=[],
                waiting_requests=[],
                overall_status="No requests analyzed",
                recommended_actions=[],
                summary="No request data available for analysis"
            )
        
        summary_prompt = f"""
        You are providing an executive summary of multiple public records requests for a user.
        
        Here are the individual request analyses:
        
        {self._format_analyses_for_prompt(individual_analyses)}
        
        Your job is to:
        
        1. **Categorize requests**: Which need urgent attention, which are completed, which are waiting?
        2. **Identify patterns**: Are there common issues or themes across requests?
        3. **Prioritize actions**: What should the user focus on first?
        4. **Assess overall health**: How is the user's request portfolio doing?
        5. **Provide strategic guidance**: What should their next steps be?
        
        Focus on:
        - **URGENT**: Requests needing immediate user action
        - **COMPLETED**: Requests with documents ready or fully closed
        - **WAITING**: Requests in progress waiting for agency response
        - **BLOCKED**: Requests stuck due to payments or other issues
        
        Provide clear, actionable recommendations that help the user manage their public records requests effectively.
        """
        
        try:
            structured_llm = self.llm_client.with_structured_output(MultiRequestSummary)
            
            result = structured_llm.invoke([
                SystemMessage(content=summary_prompt),
                HumanMessage(content="Generate a comprehensive summary of all these public records requests with clear action items.")
            ])
            
            logger.info(f"Multi-request summary generated for {len(individual_analyses)} requests")
            return result
            
        except Exception as e:
            logger.error(f"Failed to generate multi-request summary: {str(e)}")
            return MultiRequestSummary(
                total_requests=len(individual_analyses),
                urgent_requests=[],
                completed_requests=[],
                waiting_requests=[],
                overall_status=f"Summary generation failed: {str(e)}",
                recommended_actions=["Manually review individual requests"],
                summary=f"Could not generate summary due to error: {str(e)}"
            )
    
    def _format_analyses_for_prompt(self, analyses: List[RequestDetailAnalysis]) -> str:
        """Format individual analyses for inclusion in summary prompt"""
        
        formatted = []
        
        for analysis in analyses:
            formatted.append(f"""
REQUEST {analysis.request_number}:
- Status: {analysis.current_status}
- Action Required: {analysis.action_required}
- Action Description: {analysis.action_description}
- Key Insights: {'; '.join(analysis.key_insights)}
- Next Steps: {analysis.next_steps}
- Documents Available: {len(analysis.documents_available)} documents
- Outstanding Payments: {len(analysis.outstanding_payments)} payments
- Staff Contact: {analysis.staff_contact}
""")
        
        return "\n".join(formatted)
    
    def get_screenshot_from_driver(self, driver) -> str:
        """Helper to get base64 screenshot from selenium driver"""
        try:
            screenshot = driver.get_screenshot_as_png()
            return base64.b64encode(screenshot).decode('utf-8')
        except Exception as e:
            logger.error(f"Failed to take screenshot: {str(e)}")
            return ""
    
    def extract_page_text(self, driver) -> str:
        """Helper to extract page text for LLM context"""
        try:
            return driver.find_element("tag name", "body").text
        except Exception as e:
            logger.warning(f"Could not extract page text: {str(e)}")
            return ""
    
    def analyze_correspondence_intelligence(self, timeline_messages: List[str], request_context: str) -> Dict[str, Any]:
        """Deep analysis of correspondence using text LLM"""
        
        correspondence_prompt = f"""
        You are analyzing correspondence for a public records request to identify patterns and provide insights.
        
        REQUEST CONTEXT:
        {request_context}
        
        TIMELINE MESSAGES:
        {chr(10).join([f"- {msg}" for msg in timeline_messages])}
        
        Analyze this correspondence to determine:
        
        1. **Communication patterns**: How responsive is the agency? Are there delays?
        2. **Clarification requests**: What specific information has the agency asked for?
        3. **Roadblocks**: What's preventing progress on this request?
        4. **Agency behavior**: Is the agency being helpful, evasive, or standard?
        5. **Strategic insights**: What should the requester know about how to handle this agency?
        
        Provide tactical advice based on the communication patterns you observe.
        """
        
        try:
            result = self.llm_client.invoke([
                SystemMessage(content=correspondence_prompt),
                HumanMessage(content="Analyze this correspondence and provide strategic insights.")
            ])
            
            return {
                "success": True,
                "insights": result.content,
                "analysis_type": "correspondence_intelligence"
            }
            
        except Exception as e:
            logger.error(f"Failed correspondence intelligence analysis: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "analysis_type": "correspondence_intelligence"
            }
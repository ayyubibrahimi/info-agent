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
        You are analyzing a screenshot of a detailed view for public records request {request_number}.
        
        This page contains comprehensive information about a single request. Your job is to:
        
        1. **Extract current status**: What's the current state of this request?
        2. **Identify required actions**: Does the user need to do anything?
        3. **Summarize timeline**: What are the key events that have happened?
        4. **Analyze correspondence**: What messages have been exchanged?
        5. **Check for documents**: Are there any files ready for download?
        6. **Look for payments**: Are there any fees or invoices due?
        7. **Find staff contact**: Who is handling this request?
        8. **Assess completion**: When might this be finished?
        9. **Provide insights**: What should the user know?
        10. **Recommend next steps**: What should the user do?
        
        Look carefully at:
        - Status indicators and progress
        - Timeline section with chronological events
        - Any messages from staff requesting clarification
        - Documents tab or download links
        - Invoice/payment sections
        - Staff assignment information
        - Any urgent notifications or alerts
        
        Pay special attention to:
        - Messages asking for "more details" or "clarification"
        - Requests that are "on hold" waiting for user response
        - Completed requests with documents ready
        - Payment requests or fee notifications
        
        Provide actionable insights in plain language that help the user understand exactly what's happening with their request.
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
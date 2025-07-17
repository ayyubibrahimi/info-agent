import time
import logging
from typing import Dict, Any, List, Optional
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# TODO filter by requester and/or open and closed requests

logger = logging.getLogger(__name__)

class RequestManager:
    """LLM-powered manager for analyzing public records requests"""
    
    def __init__(self, driver, screenshot_func, llm_client=None):
        self.driver = driver
        self.take_screenshot = screenshot_func
        
        # Initialize LLM helper if available
        if llm_client:
            from llm_helper import LLMHelper
            self.llm_helper = LLMHelper(llm_client)
            logger.info("✅ LLM helper initialized for intelligent request analysis")
        else:
            self.llm_helper = None
            logger.warning("⚠️ No LLM client - will use basic analysis only")
    
    def navigate_to_all_requests(self) -> Dict[str, Any]:
        """Navigate to the 'All requests' page"""
        try:
            logger.info("🔍 Navigating to 'All requests' page")
            
            # Look for "All requests" link in navigation
            all_requests_selectors = [
                (By.LINK_TEXT, "All requests"),
                (By.PARTIAL_LINK_TEXT, "All requests"),
                (By.XPATH, "//a[contains(text(), 'All requests')]"),
                (By.CSS_SELECTOR, "a[href*='requests']"),
                (By.XPATH, "//nav//a[contains(text(), 'requests')]")
            ]
            
            for selector_type, selector_value in all_requests_selectors:
                try:
                    element = WebDriverWait(self.driver, 8).until(
                        EC.element_to_be_clickable((selector_type, selector_value))
                    )
                    
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
                    time.sleep(1)
                    element.click()
                    time.sleep(3)
                    
                    logger.info(f"✅ Successfully navigated to All requests using: {selector_type}")
                    self.take_screenshot("all_requests_page")
                    
                    return {
                        'success': True,
                        'url': self.driver.current_url,
                        'title': self.driver.title
                    }
                    
                except TimeoutException:
                    continue
                except Exception as e:
                    logger.warning(f"Failed to click All requests with {selector_type}: {str(e)}")
                    continue
            
            logger.error("❌ Could not find 'All requests' navigation link")
            return {
                'success': False,
                'error': "Could not find 'All requests' navigation link"
            }
            
        except Exception as e:
            logger.error(f"Failed to navigate to all requests: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def analyze_requests_overview(self) -> Dict[str, Any]:
        """Use LLM to analyze the requests table page intelligently"""
        try:
            logger.info("🧠 Analyzing requests overview with LLM")
            
            if not self.llm_helper:
                return self._basic_requests_analysis()
            
            # Get screenshot and page text for LLM analysis
            screenshot_b64 = self.llm_helper.get_screenshot_from_driver(self.driver)
            page_text = self.llm_helper.extract_page_text(self.driver)
            
            if not screenshot_b64:
                logger.warning("Could not capture screenshot for LLM analysis")
                return self._basic_requests_analysis()
            
            # Use LLM to analyze the table
            table_analysis = self.llm_helper.analyze_requests_table_page(screenshot_b64, page_text)
            
            logger.info(f"🎯 LLM found {table_analysis.total_requests_found} requests")
            logger.info(f"📋 Request numbers: {table_analysis.request_numbers}")
            
            if table_analysis.requests_with_issues:
                logger.info(f"⚠️ Requests needing attention: {table_analysis.requests_with_issues}")
            
            return {
                'success': True,
                'analysis_type': 'llm_powered',
                'total_requests': table_analysis.total_requests_found,
                'request_numbers': table_analysis.request_numbers,
                'requests_with_issues': table_analysis.requests_with_issues,
                'navigation_elements': table_analysis.navigation_elements,
                'quick_insights': table_analysis.quick_insights,
                'table_understood': table_analysis.table_structure_understood
            }
            
        except Exception as e:
            logger.error(f"LLM analysis failed: {str(e)}")
            return self._basic_requests_analysis()
    
    def _basic_requests_analysis(self) -> Dict[str, Any]:
        """Fallback analysis without LLM"""
        try:
            logger.info("🔧 Using basic analysis (no LLM)")
            
            # Try to count table rows
            rows = self.driver.find_elements(By.CSS_SELECTOR, "table tr, [role='table'] [role='row']")
            request_count = max(0, len(rows) - 1)  # Subtract header
            
            # Try to extract request numbers
            request_numbers = []
            try:
                request_links = self.driver.find_elements(By.CSS_SELECTOR, "table a, .table a")
                for link in request_links:
                    text = link.text.strip()
                    if text and any(char.isdigit() for char in text):
                        request_numbers.append(text)
            except:
                pass
            
            return {
                'success': True,
                'analysis_type': 'basic',
                'total_requests': request_count,
                'request_numbers': request_numbers,
                'requests_with_issues': [],
                'navigation_elements': [],
                'quick_insights': [f"Found {request_count} requests using basic analysis"],
                'table_understood': len(request_numbers) > 0
            }
            
        except Exception as e:
            logger.error(f"Basic analysis failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def click_request(self, request_number: str) -> Dict[str, Any]:
        """Click on a specific request to view details"""
        try:
            logger.info(f"🖱️ Clicking on request: {request_number}")
            
            # Find and click the request link
            request_selectors = [
                (By.LINK_TEXT, request_number),
                (By.PARTIAL_LINK_TEXT, request_number),
                (By.XPATH, f"//a[contains(text(), '{request_number}')]"),
                (By.XPATH, f"//td[contains(text(), '{request_number}')]//a"),
                (By.CSS_SELECTOR, f"a[href*='{request_number}']")
            ]
            
            for selector_type, selector_value in request_selectors:
                try:
                    element = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((selector_type, selector_value))
                    )
                    
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
                    time.sleep(1)
                    element.click()
                    time.sleep(3)
                    
                    logger.info(f"✅ Successfully clicked request {request_number}")
                    self.take_screenshot(f"request_detail_{request_number}")
                    
                    return {
                        'success': True,
                        'request_number': request_number,
                        'url': self.driver.current_url,
                        'title': self.driver.title
                    }
                    
                except TimeoutException:
                    continue
                except Exception as e:
                    logger.warning(f"Failed to click request with {selector_type}: {str(e)}")
                    continue
            
            logger.error(f"❌ Could not find clickable element for request {request_number}")
            return {
                'success': False,
                'error': f"Could not find clickable element for request {request_number}"
            }
            
        except Exception as e:
            logger.error(f"Failed to click request {request_number}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def analyze_single_request_intelligent(self, request_number: str) -> Dict[str, Any]:
        """Use LLM to intelligently analyze a single request"""
        try:
            logger.info(f"🧠 Intelligently analyzing request: {request_number}")
            
            if not self.llm_helper:
                return self._basic_request_analysis(request_number)
            
            # Get screenshot and page text
            screenshot_b64 = self.llm_helper.get_screenshot_from_driver(self.driver)
            page_text = self.llm_helper.extract_page_text(self.driver)
            
            if not screenshot_b64:
                logger.warning("Could not capture screenshot, using basic analysis")
                return self._basic_request_analysis(request_number)
            
            # Use LLM to analyze the request detail page
            detail_analysis = self.llm_helper.analyze_request_detail_page(
                screenshot_b64, page_text, request_number
            )
            
            # Extract timeline messages for deeper analysis
            timeline_messages = self._extract_timeline_text()
            
            # Get correspondence intelligence if we have timeline data
            correspondence_intel = None
            if timeline_messages and len(timeline_messages) > 1:
                correspondence_intel = self.llm_helper.analyze_correspondence_intelligence(
                    timeline_messages, 
                    f"Request {request_number}: {detail_analysis.correspondence_summary}"
                )
            
            logger.info(f"🎯 Analysis complete for {request_number}")
            logger.info(f"📊 Status: {detail_analysis.current_status}")
            logger.info(f"⚡ Action required: {detail_analysis.action_required}")
            
            if detail_analysis.action_required:
                logger.info(f"🔔 Action needed: {detail_analysis.action_description}")
            
            return {
                'success': True,
                'analysis_type': 'llm_intelligent',
                'request_number': request_number,
                'current_status': detail_analysis.current_status,
                'action_required': detail_analysis.action_required,
                'action_description': detail_analysis.action_description,
                'timeline_summary': detail_analysis.timeline_summary,
                'correspondence_summary': detail_analysis.correspondence_summary,
                'documents_available': detail_analysis.documents_available,
                'outstanding_payments': detail_analysis.outstanding_payments,
                'staff_contact': detail_analysis.staff_contact,
                'estimated_completion': detail_analysis.estimated_completion,
                'key_insights': detail_analysis.key_insights,
                'next_steps': detail_analysis.next_steps,
                'correspondence_intelligence': correspondence_intel,
                'full_analysis': detail_analysis.dict()
            }
            
        except Exception as e:
            logger.error(f"Intelligent analysis failed for {request_number}: {str(e)}")
            return self._basic_request_analysis(request_number)
    
    def _basic_request_analysis(self, request_number: str) -> Dict[str, Any]:
        """Fallback analysis without LLM"""
        try:
            logger.info(f"🔧 Basic analysis for {request_number}")
            
            # Extract basic information
            status = "Unknown"
            try:
                status_element = self.driver.find_element(By.CSS_SELECTOR, ".status, .badge, [class*='status']")
                status = status_element.text.strip()
            except:
                pass
            
            # Check for obvious action indicators
            action_required = False
            try:
                page_text = self.driver.find_element(By.TAG_NAME, "body").text.lower()
                action_keywords = ['please provide', 'need more', 'clarification', 'action required']
                action_required = any(keyword in page_text for keyword in action_keywords)
            except:
                pass
            
            return {
                'success': True,
                'analysis_type': 'basic',
                'request_number': request_number,
                'current_status': status,
                'action_required': action_required,
                'action_description': 'Manual review needed' if action_required else '',
                'timeline_summary': ['Basic analysis - check page manually'],
                'correspondence_summary': 'LLM analysis not available',
                'documents_available': [],
                'outstanding_payments': [],
                'staff_contact': 'Unknown',
                'estimated_completion': 'Unknown',
                'key_insights': ['Basic analysis only - limited information available'],
                'next_steps': 'Review request details manually',
                'correspondence_intelligence': None
            }
            
        except Exception as e:
            logger.error(f"Basic analysis failed for {request_number}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _extract_timeline_text(self) -> List[str]:
        """Extract timeline messages as text for correspondence analysis"""
        try:
            # Try to find timeline section
            timeline_messages = []
            
            timeline_selectors = [
                ".timeline",
                ".activity",
                ".messages",
                "[class*='timeline']",
                "[class*='activity']"
            ]
            
            for selector in timeline_selectors:
                try:
                    timeline_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in timeline_elements:
                        text = element.text.strip()
                        if text and len(text) > 10:
                            timeline_messages.append(text)
                    
                    if timeline_messages:
                        break
                except:
                    continue
            
            return timeline_messages
            
        except Exception as e:
            logger.warning(f"Could not extract timeline text: {str(e)}")
            return []
    
    def analyze_all_requests_intelligent(self) -> Dict[str, Any]:
        """Comprehensive intelligent analysis of all requests"""
        try:
            logger.info("🚀 Starting comprehensive analysis of all requests")
            
            # Step 1: Navigate to all requests page
            nav_result = self.navigate_to_all_requests()
            if not nav_result['success']:
                return {
                    'success': False,
                    'error': f"Failed to navigate: {nav_result['error']}"
                }
            
            # Step 2: Get overview of requests table
            overview = self.analyze_requests_overview()
            if not overview['success']:
                return {
                    'success': False,
                    'error': f"Failed to analyze overview: {overview.get('error', 'Unknown error')}"
                }
            
            # Step 3: Analyze each request individually
            individual_analyses = []
            failed_analyses = []
            
            for request_number in overview['request_numbers']:
                try:
                    logger.info(f"🔍 Analyzing request: {request_number}")
                    
                    # Click on request
                    click_result = self.click_request(request_number)
                    if not click_result['success']:
                        failed_analyses.append({
                            'request_number': request_number,
                            'error': click_result['error']
                        })
                        continue
                    
                    # Analyze the request
                    analysis = self.analyze_single_request_intelligent(request_number)
                    if analysis['success']:
                        individual_analyses.append(analysis)
                    else:
                        failed_analyses.append({
                            'request_number': request_number,
                            'error': analysis.get('error', 'Analysis failed')
                        })
                    
                    # Navigate back to requests list
                    self.driver.back()
                    time.sleep(2)
                    
                except Exception as e:
                    logger.warning(f"Failed to analyze request {request_number}: {str(e)}")
                    failed_analyses.append({
                        'request_number': request_number,
                        'error': str(e)
                    })
                    
                    # Try to get back to requests list
                    try:
                        self.navigate_to_all_requests()
                        time.sleep(1)
                    except:
                        pass
            
            # Step 4: Generate overall summary if we have LLM
            overall_summary = None
            if self.llm_helper and individual_analyses:
                try:
                    # Convert analyses to the format expected by LLM helper
                    from llm_helper import RequestDetailAnalysis
                    
                    llm_analyses = []
                    for analysis in individual_analyses:
                        llm_analysis = RequestDetailAnalysis(
                            request_number=analysis['request_number'],
                            current_status=analysis['current_status'],
                            action_required=analysis['action_required'],
                            action_description=analysis['action_description'],
                            timeline_summary=analysis['timeline_summary'],
                            correspondence_summary=analysis['correspondence_summary'],
                            documents_available=analysis['documents_available'],
                            outstanding_payments=analysis['outstanding_payments'],
                            staff_contact=analysis['staff_contact'],
                            estimated_completion=analysis['estimated_completion'],
                            key_insights=analysis['key_insights'],
                            next_steps=analysis['next_steps']
                        )
                        llm_analyses.append(llm_analysis)
                    
                    overall_summary = self.llm_helper.generate_multi_request_summary(llm_analyses)
                    logger.info("📊 Generated comprehensive multi-request summary")
                    
                except Exception as e:
                    logger.warning(f"Failed to generate overall summary: {str(e)}")
            
            # Compile final results
            result = {
                'success': True,
                'analysis_type': 'comprehensive_intelligent' if self.llm_helper else 'comprehensive_basic',
                'overview': overview,
                'total_requests_found': overview['total_requests'],
                'successfully_analyzed': len(individual_analyses),
                'failed_analyses': len(failed_analyses),
                'individual_analyses': individual_analyses,
                'failed_requests': failed_analyses,
                'overall_summary': overall_summary.dict() if overall_summary else None
            }
            
            # Log summary
            logger.info(f"🎯 Analysis complete!")
            logger.info(f"📈 Found: {result['total_requests_found']} requests")
            logger.info(f"✅ Analyzed: {result['successfully_analyzed']} requests")
            logger.info(f"❌ Failed: {result['failed_analyses']} requests")
            
            if overall_summary:
                logger.info(f"🚨 Urgent requests: {len(overall_summary.urgent_requests)}")
                logger.info(f"✅ Completed requests: {len(overall_summary.completed_requests)}")
                logger.info(f"⏳ Waiting requests: {len(overall_summary.waiting_requests)}")
            
            return result
            
        except Exception as e:
            logger.error(f"Comprehensive analysis failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_urgent_requests(self) -> Dict[str, Any]:
        """Get requests that need immediate attention"""
        try:
            logger.info("🚨 Identifying urgent requests")
            
            # Run comprehensive analysis
            full_analysis = self.analyze_all_requests_intelligent()
            
            if not full_analysis['success']:
                return {
                    'success': False,
                    'error': full_analysis['error']
                }
            
            urgent_requests = []
            
            # Extract urgent requests from individual analyses
            for analysis in full_analysis['individual_analyses']:
                if analysis.get('action_required', False):
                    urgent_requests.append({
                        'request_number': analysis['request_number'],
                        'status': analysis['current_status'],
                        'action_needed': analysis['action_description'],
                        'key_insights': analysis['key_insights'],
                        'next_steps': analysis['next_steps']
                    })
            
            # Also check overall summary for urgent items
            urgent_from_summary = []
            if full_analysis.get('overall_summary') and full_analysis['overall_summary'].get('urgent_requests'):
                urgent_from_summary = full_analysis['overall_summary']['urgent_requests']
            
            logger.info(f"🔔 Found {len(urgent_requests)} requests needing immediate attention")
            
            return {
                'success': True,
                'urgent_count': len(urgent_requests),
                'urgent_requests': urgent_requests,
                'urgent_from_summary': urgent_from_summary,
                'recommended_actions': full_analysis.get('overall_summary', {}).get('recommended_actions', [])
            }
            
        except Exception as e:
            logger.error(f"Failed to get urgent requests: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def generate_status_report(self) -> Dict[str, Any]:
        """Generate a comprehensive status report of all requests"""
        try:
            logger.info("📋 Generating comprehensive status report")
            
            # Get full analysis
            analysis = self.analyze_all_requests_intelligent()
            
            if not analysis['success']:
                return {
                    'success': False,
                    'error': analysis['error']
                }
            
            # Categorize requests
            urgent_requests = []
            completed_requests = []
            in_progress_requests = []
            blocked_requests = []
            
            for req_analysis in analysis['individual_analyses']:
                req_number = req_analysis['request_number']
                status = req_analysis['current_status'].lower()
                
                if req_analysis.get('action_required', False):
                    urgent_requests.append(req_number)
                elif 'complete' in status or 'closed' in status:
                    completed_requests.append(req_number)
                elif 'payment' in status or req_analysis.get('outstanding_payments'):
                    blocked_requests.append(req_number)
                else:
                    in_progress_requests.append(req_number)
            
            # Generate user-friendly report
            report = {
                'success': True,
                'report_timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'summary': {
                    'total_requests': analysis['total_requests_found'],
                    'urgent_requests': len(urgent_requests),
                    'completed_requests': len(completed_requests),
                    'in_progress_requests': len(in_progress_requests),
                    'blocked_requests': len(blocked_requests)
                },
                'categorized_requests': {
                    'urgent': urgent_requests,
                    'completed': completed_requests,
                    'in_progress': in_progress_requests,
                    'blocked': blocked_requests
                },
                'detailed_analyses': analysis['individual_analyses'],
                'overall_summary': analysis.get('overall_summary'),
                'recommendations': analysis.get('overall_summary', {}).get('recommended_actions', [])
            }
            
            logger.info("📊 Status report generated successfully")
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate status report: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def navigate_back_to_home(self) -> bool:
        """Navigate back to portal home page"""
        try:
            logger.info("🏠 Navigating back to portal home")
            
            home_selectors = [
                (By.LINK_TEXT, "Home"),
                (By.PARTIAL_LINK_TEXT, "Home"),
                (By.CSS_SELECTOR, ".logo"),
                (By.CSS_SELECTOR, "[class*='brand']"),
                (By.XPATH, "//a[contains(@href, '/') and not(contains(@href, '/requests'))]")
            ]
            
            for selector_type, selector_value in home_selectors:
                try:
                    element = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((selector_type, selector_value))
                    )
                    
                    element.click()
                    time.sleep(2)
                    
                    logger.info("✅ Successfully navigated back to home")
                    self.take_screenshot("back_to_home")
                    return True
                    
                except TimeoutException:
                    continue
                except Exception as e:
                    logger.warning(f"Failed to click home with {selector_type}: {str(e)}")
                    continue
            
            logger.warning("Could not find home navigation, trying browser back")
            self.driver.back()
            time.sleep(2)
            return True
            
        except Exception as e:
            logger.error(f"Failed to navigate home: {str(e)}")
            return False
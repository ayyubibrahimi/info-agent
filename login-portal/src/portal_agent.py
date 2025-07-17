import time
import logging
from typing import Dict, Any, Optional
from pathlib import Path
from models import LoginCredentials
from browser_setup import BrowserSetup
from screenshot_manager import ScreenshotManager
from llm import LLMAnalyzer
from login_handler import LoginHandler
from session_manager import SessionManager
import json

logger = logging.getLogger(__name__)

class PortalAgent:
    def __init__(self, llm_client, headless: bool = False):
        self.llm_client = llm_client
        self.headless = headless
        self.driver = None
        self.screenshot_manager = None
        self.llm_analyzer = None
        self.login_handler = None
        self.request_workflow = None  # New: Request workflow
        self.is_logged_in = False     # New: Track login status
        self.results_dir = Path(".")  # Add results directory
        
    def __enter__(self):
        self.setup()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.driver:
            self.driver.quit()
    
    def setup(self):
        """Initialize all components"""
        self.driver = BrowserSetup.create_chrome_driver(self.headless)
        self.screenshot_manager = ScreenshotManager(self.driver)
        self.llm_analyzer = LLMAnalyzer(self.llm_client)
        self.login_handler = LoginHandler(
            self.driver,
            self.screenshot_manager.take_screenshot,
            self.analyze_screenshot_with_llm
        )
    
    def setup_request_workflow(self):
        """Setup request workflow after successful login"""
        try:
            from request_workflow import RequestWorkflow
            self.request_workflow = RequestWorkflow(
                self.llm_client,
                self.driver,
                self.screenshot_manager.take_screenshot
            )
            logger.info("Request workflow initialized successfully")
        except ImportError as e:
            logger.error(f"Failed to import request workflow: {str(e)}")
            logger.error("Make sure request_workflow.py and related modules are available")
            raise
    
    def analyze_screenshot_with_llm(self, screenshot_data: Dict[str, Any]):
        """Wrapper method for LLM analysis"""
        page_text = self.screenshot_manager.get_page_text_content()
        return self.llm_analyzer.analyze_page(screenshot_data, page_text)
    
    def take_screenshot(self, label: str = "screenshot"):
        """Wrapper for screenshot functionality"""
        return self.screenshot_manager.take_screenshot(label)
    
    def navigate_to_portal(self, portal_url: str) -> Dict[str, Any]:
        """Navigate to the portal with realistic human-like behavior"""
        try:
            logger.info(f"Navigating to portal: {portal_url}")
            
            # First, visit Google to establish a realistic browsing pattern
            self.driver.get("https://www.google.com")
            time.sleep(2)  # Human-like pause
            
            # Navigate to the actual portal
            self.driver.get(portal_url)
            
            # Wait for page to load
            time.sleep(5)
            
            # Perform human-like interactions
            try:
                # Scroll down and back up
                self.driver.execute_script("window.scrollTo(0, 100);")
                time.sleep(1)
                self.driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(0.5)
            except:
                pass  # Ignore scroll errors
            
            # Take initial screenshot
            screenshot = self.screenshot_manager.take_screenshot("initial_portal_view")
            
            # Check if we were redirected to a block page
            current_url = self.driver.current_url
            if 'block.php' in current_url or 'civicplus.com' in current_url:
                logger.warning(f"⚠️  Redirected to blocking page: {current_url}")
                analysis = self.analyze_screenshot_with_llm(screenshot)
                return {
                    'success': False,
                    'blocked': True,
                    'redirect_url': current_url,
                    'screenshot': screenshot,
                    'analysis': analysis,
                    'url': current_url,
                    'title': self.driver.title,
                    'error': f"Access blocked - redirected to {current_url}"
                }
            
            # Analyze the page
            analysis = self.analyze_screenshot_with_llm(screenshot)
            
            return {
                'success': True,
                'screenshot': screenshot,
                'analysis': analysis,
                'url': self.driver.current_url,
                'title': self.driver.title
            }
            
        except Exception as e:
            logger.error(f"Failed to navigate to portal: {str(e)}")
            
            # Try to take a screenshot even if navigation failed
            try:
                error_screenshot = self.screenshot_manager.take_screenshot("navigation_error")
                current_url = self.driver.current_url
                return {
                    'success': False,
                    'error': str(e),
                    'url': current_url,
                    'error_screenshot': error_screenshot,
                    'blocked': 'block.php' in current_url or 'civicplus.com' in current_url
                }
            except:
                return {
                    'success': False,
                    'error': str(e),
                    'url': portal_url
                }
    
    def access_portal_session(self, portal_url: str, credentials: Optional[LoginCredentials] = None) -> Dict[str, Any]:
        """Complete portal access session: navigate, analyze, and optionally login"""
        
        session_results = {}
        
        try:
            # Step 1: Navigate to portal
            logger.info("=== STEP 1: NAVIGATING TO ALAMEDA COUNTY NEXTREQUEST PORTAL ===")
            navigation_result = self.navigate_to_portal(portal_url)
            session_results['navigation'] = navigation_result
            
            if not navigation_result['success']:
                if navigation_result.get('blocked'):
                    logger.error("❌ Portal access blocked by CivicPlus security")
                else:
                    logger.error("❌ Failed to access portal")
                return session_results
            
            # Step 2: Analyze initial page
            initial_analysis = navigation_result['analysis']
            logger.info(f"✅ Portal accessed successfully!")
            logger.info(f"Page type: {initial_analysis.page_type}")
            logger.info(f"Login required: {initial_analysis.login_required}")
            logger.info(f"Key elements found: {initial_analysis.key_elements}")
            logger.info(f"Recommended next steps: {initial_analysis.next_steps}")
            
            # Step 3: Login if credentials provided
            if credentials:
                logger.info("=== STEP 2: ATTEMPTING LOGIN ===")
                login_result = self.login_handler.attempt_login(credentials)
                session_results['login'] = login_result
                
                if login_result['success']:
                    logger.info("✅ Login successful!")
                    self.is_logged_in = True  # Track login status
                    
                    # Take final screenshot
                    final_screenshot = self.screenshot_manager.take_screenshot("final_logged_in_state")
                    final_analysis = self.analyze_screenshot_with_llm(final_screenshot)
                    
                    session_results['final_state'] = {
                        'screenshot': final_screenshot,
                        'analysis': final_analysis
                    }
                    
                    logger.info(f"Final state: {final_analysis.page_type}")
                    logger.info(f"Available actions: {final_analysis.next_steps}")
                    
                    # Initialize request workflow after successful login
                    try:
                        self.setup_request_workflow()
                        logger.info("✅ Request functionality ready!")
                    except Exception as e:
                        logger.warning(f"⚠️  Request functionality not available: {str(e)}")
                    
                else:
                    logger.error(f"❌ Login failed: {login_result.get('error', 'Unknown error')}")
                    self.is_logged_in = False
            
            else:
                logger.info("ℹ️  No login credentials provided - analyzing portal without authentication")
                session_results['login'] = {'skipped': True, 'reason': 'No credentials provided'}
                self.is_logged_in = False
            
            # Save results
            SessionManager.save_session_results(
                session_results, 
                self.screenshot_manager.screenshots, 
                portal_url
            )
            
            return session_results
            
        except Exception as e:
            logger.error(f"Portal access session failed: {str(e)}")
            session_results['session_error'] = str(e)
            SessionManager.save_session_results(
                session_results, 
                self.screenshot_manager.screenshots, 
                portal_url
            )
            return session_results
    
    def submit_public_records_request(self, user_topic: str, user_info: Dict[str, str]) -> Dict[str, Any]:
        """Submit a public records request based on user topic"""
        
        if not self.is_logged_in:
            return {
                'success': False,
                'error': 'Must be logged in to submit requests',
                'user_topic': user_topic
            }
        
        if not self.request_workflow:
            try:
                self.setup_request_workflow()
            except Exception as e:
                return {
                    'success': False,
                    'error': f'Request functionality not available: {str(e)}',
                    'user_topic': user_topic
                }
        
        logger.info(f"=== SUBMITTING PUBLIC RECORDS REQUEST FOR: '{user_topic}' ===")
        
        try:
            result = self.request_workflow.execute_request_workflow(user_topic, user_info)
            
            # Save request results
            self._save_request_results(result, user_topic)
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to submit request: {str(e)}")
            return {
                'success': False,
                'error': f'Request submission failed: {str(e)}',
                'user_topic': user_topic
            }
    
    def analyze_existing_requests(self, detailed_analysis: bool = True) -> Dict[str, Any]:
        """
        PHASE 3: Analyze existing public records requests using LLM intelligence
        
        Args:
            detailed_analysis: If True, analyzes each request individually (slower but comprehensive)
                              If False, provides overview analysis only (faster)
        
        Returns:
            Dict containing comprehensive analysis of all requests
        """
        try:
            logger.info("🔍 PHASE 3: Starting analysis of existing requests")
            
            if not self.is_logged_in:
                return {
                    'success': False,
                    'error': 'Must be logged in to analyze requests',
                    'phase': 'phase_3_analyze_requests'
                }
            
            # Initialize enhanced request manager with LLM capabilities
            from request_manager import RequestManager
            
            request_manager = RequestManager(
                driver=self.driver,
                screenshot_func=self.take_screenshot,
                llm_client=self.llm_client
            )
            
            if detailed_analysis:
                # Comprehensive analysis of all requests
                logger.info("🧠 Running detailed LLM analysis of all requests")
                analysis_result = request_manager.analyze_all_requests_intelligent()
            else:
                # Quick overview analysis
                logger.info("⚡ Running quick overview analysis")
                nav_result = request_manager.navigate_to_all_requests()
                if not nav_result['success']:
                    return {
                        'success': False,
                        'error': nav_result['error'],
                        'phase': 'phase_3_analyze_requests'
                    }
                
                analysis_result = request_manager.analyze_requests_overview()
            
            if not analysis_result['success']:
                return {
                    'success': False,
                    'error': analysis_result.get('error', 'Analysis failed'),
                    'phase': 'phase_3_analyze_requests'
                }
            
            # Generate status report
            status_report = None
            if detailed_analysis:
                try:
                    status_report = request_manager.generate_status_report()
                except Exception as e:
                    logger.warning(f"Could not generate status report: {str(e)}")
            
            # Navigate back to home
            request_manager.navigate_back_to_home()
            
            # Save results
            self._save_phase3_results(analysis_result, status_report)
            
            logger.info("✅ PHASE 3: Request analysis completed successfully")
            
            return {
                'success': True,
                'phase': 'phase_3_analyze_requests',
                'analysis_type': analysis_result.get('analysis_type', 'unknown'),
                'total_requests': analysis_result.get('total_requests_found', 0),
                'analysis_result': analysis_result,
                'status_report': status_report,
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
        except Exception as e:
            logger.error(f"PHASE 3 failed: {str(e)}")
            self.take_screenshot("phase3_error")
            return {
                'success': False,
                'error': str(e),
                'phase': 'phase_3_analyze_requests'
            }

    def get_urgent_requests_summary(self) -> Dict[str, Any]:
        """
        Quick method to get just the urgent requests that need attention
        """
        try:
            logger.info("🚨 Getting urgent requests summary")
            
            if not self.is_logged_in:
                return {
                    'success': False,
                    'error': 'Must be logged in to check requests'
                }
            
            from request_manager import RequestManager
            
            request_manager = RequestManager(
                driver=self.driver,
                screenshot_func=self.take_screenshot,
                llm_client=self.llm_client
            )
            
            urgent_result = request_manager.get_urgent_requests()
            
            # Navigate back to home
            request_manager.navigate_back_to_home()
            
            return urgent_result
            
        except Exception as e:
            logger.error(f"Failed to get urgent requests: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def display_requests_summary(self, analysis_result: Dict[str, Any]):
        """Display a user-friendly summary of request analysis"""
        
        if not analysis_result.get('success'):
            print(f"❌ Analysis failed: {analysis_result.get('error', 'Unknown error')}")
            return
        
        print("\n" + "=" * 60)
        print("📊 PUBLIC RECORDS REQUESTS ANALYSIS")
        print("=" * 60)
        
        total = analysis_result.get('total_requests', 0)
        analysis_type = analysis_result.get('analysis_type', 'unknown')
        
        print(f"📈 Total Requests Found: {total}")
        print(f"🧠 Analysis Type: {analysis_type}")
        
        if analysis_result.get('analysis_result'):
            result = analysis_result['analysis_result']
            
            # Show overview insights
            if result.get('quick_insights'):
                print(f"\n💡 QUICK INSIGHTS:")
                for insight in result['quick_insights']:
                    print(f"  • {insight}")
            
            # Show urgent requests
            urgent_count = 0
            if result.get('individual_analyses'):
                urgent_requests = [
                    a for a in result['individual_analyses'] 
                    if a.get('action_required', False)
                ]
                urgent_count = len(urgent_requests)
                
                if urgent_requests:
                    print(f"\n🚨 URGENT REQUESTS ({urgent_count} need attention):")
                    for req in urgent_requests:
                        print(f"  • {req['request_number']}: {req['action_description']}")
            
            # Show overall summary from LLM
            if result.get('overall_summary'):
                summary = result['overall_summary']
                print(f"\n📋 AI SUMMARY:")
                print(f"  {summary.get('summary', 'No summary available')}")
                
                if summary.get('recommended_actions'):
                    print(f"\n✅ RECOMMENDED ACTIONS:")
                    for i, action in enumerate(summary['recommended_actions'], 1):
                        print(f"  {i}. {action}")
        
        print(f"\n📁 Detailed results saved to files in results directory")
        print("=" * 60)

    def _save_phase3_results(self, analysis_result: Dict[str, Any], status_report: Optional[Dict[str, Any]] = None):
        """Save Phase 3 analysis results to files"""
        try:
            timestamp = time.strftime('%Y%m%d_%H%M%S')
            
            # Save detailed analysis
            analysis_filename = f"alameda_requests_analysis_{timestamp}.json"
            analysis_filepath = self.results_dir / analysis_filename
            
            with open(analysis_filepath, 'w', encoding='utf-8') as f:
                json.dump(analysis_result, f, indent=2, default=str)
            
            logger.info(f"📁 Saved analysis results to: {analysis_filename}")
            
            # Save status report if available
            if status_report and status_report.get('success'):
                report_filename = f"alameda_requests_report_{timestamp}.txt"
                report_filepath = self.results_dir / report_filename
                
                with open(report_filepath, 'w', encoding='utf-8') as f:
                    f.write("ALAMEDA COUNTY PUBLIC RECORDS REQUESTS - STATUS REPORT\n")
                    f.write("=" * 60 + "\n")
                    f.write(f"Generated: {status_report['report_timestamp']}\n\n")
                    
                    summary = status_report['summary']
                    f.write(f"SUMMARY:\n")
                    f.write(f"- Total Requests: {summary['total_requests']}\n")
                    f.write(f"- Urgent (Action Required): {summary['urgent_requests']}\n")
                    f.write(f"- Completed: {summary['completed_requests']}\n")
                    f.write(f"- In Progress: {summary['in_progress_requests']}\n")
                    f.write(f"- Blocked/Payment Due: {summary['blocked_requests']}\n\n")
                    
                    # Urgent requests details
                    if status_report['categorized_requests']['urgent']:
                        f.write("URGENT REQUESTS (NEED YOUR ATTENTION):\n")
                        f.write("-" * 40 + "\n")
                        for req_num in status_report['categorized_requests']['urgent']:
                            # Find detailed info
                            for analysis in status_report['detailed_analyses']:
                                if analysis['request_number'] == req_num:
                                    f.write(f"Request {req_num}:\n")
                                    f.write(f"  Status: {analysis['current_status']}\n")
                                    f.write(f"  Action: {analysis['action_description']}\n")
                                    f.write(f"  Next Steps: {analysis['next_steps']}\n\n")
                                    break
                    
                    # Overall summary from LLM
                    if status_report.get('overall_summary'):
                        overall = status_report['overall_summary']
                        f.write("AI ANALYSIS SUMMARY:\n")
                        f.write("-" * 40 + "\n")
                        f.write(f"{overall.get('summary', 'No summary available')}\n\n")
                        
                        if overall.get('recommended_actions'):
                            f.write("RECOMMENDED ACTIONS:\n")
                            for i, action in enumerate(overall['recommended_actions'], 1):
                                f.write(f"{i}. {action}\n")
                
                logger.info(f"📄 Saved status report to: {report_filename}")
                
        except Exception as e:
            logger.warning(f"Could not save Phase 3 results: {str(e)}")

    def _save_request_results(self, result: Dict[str, Any], user_topic: str):
        """Save request submission results to a file"""
        try:
            import datetime
            import json
            
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"request_submission_{timestamp}.json"
            
            # Convert any non-serializable objects
            serializable_result = SessionManager.convert_to_dict(result)
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump({
                    'timestamp': timestamp,
                    'user_topic': user_topic,
                    'result': serializable_result,
                    'portal_url': 'https://alamedacountysheriffca.nextrequest.com/'
                }, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Request results saved to {filename}")
            
        except Exception as e:
            logger.error(f"Failed to save request results: {str(e)}")
    
    def get_portal_status(self) -> Dict[str, Any]:
        """Get current portal status and capabilities"""
        return {
            'is_logged_in': self.is_logged_in,
            'current_url': self.driver.current_url if self.driver else None,
            'request_functionality_available': self.request_workflow is not None,
            'total_screenshots': len(self.screenshot_manager.screenshots) if self.screenshot_manager else 0
        }
    
    # Add this method to your PortalAgent class

    def analyze_specific_requests(self) -> Dict[str, Any]:
        """
        PHASE 3 INTERACTIVE: Let user choose specific requests to analyze
        """
        try:
            logger.info("🎯 PHASE 3 INTERACTIVE: Starting specific request analysis")
            
            if not self.is_logged_in:
                return {
                    'success': False,
                    'error': 'Must be logged in to analyze requests'
                }
            
            # Initialize interactive analyzer
            from request_analyzer import RequestAnalyzer  # Changed this line
            
            analyzer = RequestAnalyzer(  # And this line
                driver=self.driver,
                screenshot_func=self.take_screenshot,
                llm_client=self.llm_client
            )
            
            # Run interactive workflow
            result = analyzer.interactive_analysis_workflow()
            
            # Navigate back to home
            analyzer.navigate_back_to_home()
            
            # Save results if successful
            if result['success']:
                self._save_interactive_results(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Interactive analysis failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def _save_interactive_results(self, result: Dict[str, Any]):
        """Save interactive analysis results"""
        try:
            timestamp = time.strftime('%Y%m%d_%H%M%S')
            filename = f"alameda_interactive_analysis_{timestamp}.json"
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, default=str)
            
            logger.info(f"📁 Saved interactive analysis to: {filename}")
            
        except Exception as e:
            logger.warning(f"Could not save interactive results: {str(e)}")
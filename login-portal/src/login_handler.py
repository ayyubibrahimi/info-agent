import time
import logging
from typing import Dict, Any, List, Tuple
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from models import LoginCredentials, ScreenshotAnalysis

logger = logging.getLogger(__name__)

class LoginHandler:
    def __init__(self, driver, screenshot_func, analyze_func):
        self.driver = driver
        self.take_screenshot = screenshot_func
        self.analyze_screenshot_with_llm = analyze_func
    
    def attempt_login(self, credentials: LoginCredentials) -> Dict[str, Any]:
        """Attempt to login to the portal"""
        try:
            logger.info("Attempting to login...")
            
            # First, look for "Sign in" button/link
            sign_in_selectors = [
                (By.LINK_TEXT, "Sign in"),
                (By.LINK_TEXT, "Sign In"),
                (By.LINK_TEXT, "Login"),
                (By.LINK_TEXT, "Log in"),
                (By.PARTIAL_LINK_TEXT, "Sign in"),
                (By.CSS_SELECTOR, "a[href*='sign']"),
                (By.CSS_SELECTOR, "button[data-test-id='sign-in']"),
                (By.CLASS_NAME, "sign-in-button"),
                (By.CLASS_NAME, "login-button")
            ]
            
            sign_in_clicked = self._try_click_elements(sign_in_selectors, "sign in")
            
            if not sign_in_clicked:
                logger.warning("No sign in button found, checking if already on login page")
            
            # Take screenshot after clicking sign in
            pre_login_screenshot = self.take_screenshot("after_sign_in_click")
            pre_login_analysis = self.analyze_screenshot_with_llm(pre_login_screenshot)
            
            # Find login form fields
            username_field = self._find_username_field()
            password_field = self._find_password_field()
            
            if not username_field or not password_field:
                return {
                    'success': False,
                    'error': 'Could not find login form fields',
                    'pre_login_screenshot': pre_login_screenshot,
                    'pre_login_analysis': pre_login_analysis,
                    'found_username': username_field is not None,
                    'found_password': password_field is not None
                }
            
            # Fill in credentials
            self._fill_credentials(username_field, password_field, credentials)
            
            # Find and click submit button
            submit_clicked = self._try_submit()
            
            if not submit_clicked:
                return {
                    'success': False,
                    'error': 'Could not find submit button',
                    'credentials_filled': True
                }
            
            # Wait for login to process
            time.sleep(8)
            
            # Take screenshot after login attempt
            post_login_screenshot = self.take_screenshot("after_login_attempt")
            post_login_analysis = self.analyze_screenshot_with_llm(post_login_screenshot)
            
            # Check if login was successful
            login_success = self._evaluate_login_success(post_login_analysis, post_login_screenshot)
            
            return {
                'success': login_success,
                'pre_login_screenshot': pre_login_screenshot,
                'pre_login_analysis': pre_login_analysis,
                'post_login_screenshot': post_login_screenshot,
                'post_login_analysis': post_login_analysis,
                'final_url': self.driver.current_url
            }
            
        except Exception as e:
            logger.error(f"Login attempt failed: {str(e)}")
            error_screenshot = self.take_screenshot("login_error")
            return {
                'success': False,
                'error': str(e),
                'error_screenshot': error_screenshot
            }
    
    def _try_click_elements(self, selectors: List[Tuple], element_type: str) -> bool:
        """Try to click elements using multiple selectors"""
        for selector_type, selector_value in selectors:
            try:
                element = WebDriverWait(self.driver, 3).until(
                    EC.element_to_be_clickable((selector_type, selector_value))
                )
                element.click()
                time.sleep(5)
                logger.info(f"Clicked {element_type} element: {selector_type}='{selector_value}'")
                return True
            except TimeoutException:
                continue
        return False
    
    def _find_username_field(self):
        """Find username field using multiple selectors"""
        username_selectors = [
            (By.CSS_SELECTOR, 'input[type="email"]'),
            (By.CSS_SELECTOR, 'input[name="email"]'),
            (By.CSS_SELECTOR, 'input[name="username"]'),
            (By.CSS_SELECTOR, 'input[placeholder*="email"]'),
            (By.CSS_SELECTOR, 'input[placeholder*="username"]'),
            (By.CSS_SELECTOR, 'input[id*="email"]'),
            (By.CSS_SELECTOR, 'input[id*="username"]')
        ]
        
        for selector_type, selector_value in username_selectors:
            try:
                field = WebDriverWait(self.driver, 3).until(
                    EC.presence_of_element_located((selector_type, selector_value))
                )
                logger.info(f"Found username field: {selector_type}='{selector_value}'")
                return field
            except TimeoutException:
                continue
        return None
    
    def _find_password_field(self):
        """Find password field using multiple selectors"""
        password_selectors = [
            (By.CSS_SELECTOR, 'input[type="password"]'),
            (By.CSS_SELECTOR, 'input[name="password"]'),
            (By.CSS_SELECTOR, 'input[id*="password"]')
        ]
        
        for selector_type, selector_value in password_selectors:
            try:
                field = WebDriverWait(self.driver, 3).until(
                    EC.presence_of_element_located((selector_type, selector_value))
                )
                logger.info(f"Found password field: {selector_type}='{selector_value}'")
                return field
            except TimeoutException:
                continue
        return None
    
    def _fill_credentials(self, username_field, password_field, credentials: LoginCredentials):
        """Fill in login credentials"""
        username_field.clear()
        username_field.send_keys(credentials.username)
        time.sleep(1)
        
        password_field.clear()
        password_field.send_keys(credentials.password)
        time.sleep(1)
    
    def _try_submit(self) -> bool:
        """Try to find and click submit button"""
        submit_selectors = [
            (By.CSS_SELECTOR, 'button[type="submit"]'),
            (By.CSS_SELECTOR, 'input[type="submit"]'),
            (By.XPATH, "//button[contains(text(), 'Sign in')]"),
            (By.XPATH, "//button[contains(text(), 'Login')]"),
            (By.XPATH, "//button[contains(text(), 'Log in')]"),
            (By.CSS_SELECTOR, '[data-test-id="login-submit"]'),
            (By.CLASS_NAME, 'login-submit'),
            (By.CLASS_NAME, 'submit-button')
        ]
        
        return self._try_click_elements(submit_selectors, "submit")
    
    def _evaluate_login_success(self, analysis: ScreenshotAnalysis, screenshot: Dict[str, Any]) -> bool:
        """Evaluate if login was successful based on page analysis"""
        success_indicators = [
            analysis.page_type == 'logged_in_dashboard',
            'dashboard' in screenshot['title'].lower(),
            'welcome' in screenshot['url'].lower(),
            not analysis.login_required,
            any('make request' in elem.lower() for elem in analysis.key_elements)
        ]
        
        # Check for error indicators
        error_indicators = [
            analysis.page_type == 'error',
            'error' in screenshot['title'].lower(),
            any('invalid' in elem.lower() for elem in analysis.key_elements),
            any('incorrect' in elem.lower() for elem in analysis.key_elements),
            any('failed' in elem.lower() for elem in analysis.key_elements)
        ]
        
        if any(error_indicators):
            return False
            
        return any(success_indicators)

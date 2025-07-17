import time
import logging
from typing import Dict, Any, Optional
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.keys import Keys

logger = logging.getLogger(__name__)

class FormSubmitter:
    def __init__(self, driver, screenshot_func, llm_client=None):
        self.driver = driver
        self.take_screenshot = screenshot_func
        
        # Initialize LLM-based analyzers if LLM client is provided
        if llm_client:
            from llm import CSSAndDOMAnalyzer, RichTextFormFiller
            self.css_dom_analyzer = CSSAndDOMAnalyzer(llm_client)
            self.rich_text_filler = RichTextFormFiller(driver, self.css_dom_analyzer)
            logger.info("✅ LLM analyzers initialized - will use intelligent form analysis")
        else:
            self.css_dom_analyzer = None
            self.rich_text_filler = None
            logger.info("⚠️ No LLM client provided - will use fallback methods only")
    
    def navigate_to_request_form(self) -> bool:
        """Navigate to the 'Make Request' form"""
        try:
            logger.info("Looking for 'Make Request' button on portal home page")
            
            make_request_selectors = [
                (By.XPATH, "//button[contains(text(), 'Make Request')]"),
                (By.LINK_TEXT, "Make Request"),
                (By.PARTIAL_LINK_TEXT, "Make Request"),
                (By.CSS_SELECTOR, "button:contains('Make Request')"),
                (By.CSS_SELECTOR, "a:contains('Make Request')"),
                (By.XPATH, "//a[contains(text(), 'Make Request')]"),
                (By.CSS_SELECTOR, "button[href*='request']"),
                (By.CSS_SELECTOR, "a[href*='request']")
            ]
            
            for selector_type, selector_value in make_request_selectors:
                try:
                    element = WebDriverWait(self.driver, 8).until(
                        EC.element_to_be_clickable((selector_type, selector_value))
                    )
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
                    time.sleep(1)
                    element.click()
                    time.sleep(4)
                    logger.info(f"Successfully clicked 'Make Request' using: {selector_type}")
                    self.take_screenshot("request_form_loaded")
                    return True
                except TimeoutException:
                    continue
                except Exception as e:
                    logger.warning(f"Failed to click Make Request with {selector_type}: {str(e)}")
                    continue
            
            logger.error("Could not find 'Make Request' button")
            return False
            
        except Exception as e:
            logger.error(f"Failed to navigate to request form: {str(e)}")
            return False
    
    def fill_and_submit_form(self, request_text: str, user_info: Dict[str, str]) -> Dict[str, Any]:
        """Enhanced form filling with LLM-powered rich text editor detection"""
        
        result = {
            'success': False,
            'steps_completed': [],
            'errors': [],
            'llm_analysis': None,
            'filling_method': None
        }
        
        try:
            # Take screenshot
            self.take_screenshot("form_before_filling")
            
            # Step 1: Fill request description using LLM analysis if available
            logger.info("=== FILLING REQUEST DESCRIPTION ===")
            
            if self.rich_text_filler and self.css_dom_analyzer:
                logger.info("🧠 Using LLM-powered intelligent form analysis")
                
                # Use the smart LLM-based approach
                fill_result = self.rich_text_filler.smart_fill_request_description(request_text)
                result['llm_analysis'] = fill_result.get('analysis')
                result['filling_method'] = fill_result.get('method_used')
                
                if fill_result['success']:
                    result['steps_completed'].append(f"Request description ({fill_result['method_used']})")
                    logger.info(f"✅ LLM-guided filling successful: {fill_result['method_used']}")
                else:
                    logger.warning("🔄 LLM analysis failed, trying enhanced fallback")
                    result['errors'].extend(fill_result.get('errors', []))
                    
                    # Try enhanced fallback that avoids address fields
                    if self._fill_request_description_enhanced_fallback(request_text):
                        result['steps_completed'].append("Request description (enhanced fallback)")
                        result['filling_method'] = "enhanced fallback"
                    else:
                        result['errors'].append("CRITICAL: All request description filling methods failed")
                        return result
            else:
                logger.info("🔧 No LLM available, using enhanced fallback methods")
                if self._fill_request_description_enhanced_fallback(request_text):
                    result['steps_completed'].append("Request description (enhanced fallback)")
                    result['filling_method'] = "enhanced fallback"
                else:
                    result['errors'].append("CRITICAL: Failed to fill request description")
                    return result
            
            # Step 2: Fill contact information
            logger.info("=== FILLING CONTACT INFORMATION ===")
            contact_result = self._fill_contact_information(user_info)
            
            if contact_result['filled_count'] > 0:
                result['steps_completed'].append(f"Contact information ({contact_result['filled_count']} fields)")
            
            result['errors'].extend(contact_result['errors'])
            
            # Step 3: Submit the form
            logger.info("=== SUBMITTING FORM ===")
            self.take_screenshot("before_form_submission")
            
            if self._submit_form():
                result['steps_completed'].append("Form submission")
                result['success'] = True
                time.sleep(4)
                self.take_screenshot("after_form_submission")
                
                confirmation = self._get_confirmation_info()
                result['confirmation'] = confirmation
            else:
                result['errors'].append("Failed to submit form")
            
            return result
            
        except Exception as e:
            logger.error(f"Form submission failed: {str(e)}")
            result['errors'].append(f"Unexpected error: {str(e)}")
            return result
    
    def _fill_request_description_enhanced_fallback(self, request_text: str) -> bool:
        """Enhanced fallback that specifically avoids address fields and targets request description"""
        
        strategies = [
            ("Placeholder-based targeting", self._try_placeholder_based_selection),
            ("Size-based selection (avoiding address)", self._try_size_based_selection_smart),
            ("JavaScript rich text detection", self._try_javascript_detection),
            ("Content-editable detection", self._try_content_editable_detection),
            ("Position-based (top of form)", self._try_position_based_selection),
            ("Label association", self._try_label_association)
        ]
        
        for strategy_name, strategy_func in strategies:
            try:
                logger.info(f"🔍 Trying: {strategy_name}")
                if strategy_func(request_text):
                    logger.info(f"✅ {strategy_name} succeeded!")
                    return True
                else:
                    logger.info(f"❌ {strategy_name} failed")
            except Exception as e:
                logger.warning(f"❌ {strategy_name} error: {str(e)}")
                continue
        
        logger.error("💥 All enhanced fallback strategies failed")
        return False
    
    def _try_placeholder_based_selection(self, request_text: str) -> bool:
        """Target fields with request-specific placeholder text"""
        try:
            # Target the exact placeholder we saw in the screenshot
            selectors = [
                "textarea[placeholder*='Enter your request - please include all information']",
                "textarea[placeholder*='Enter your request']",
                "[contenteditable][placeholder*='Enter your request']",
                "textarea[placeholder*='please include all information']"
            ]
            
            for selector in selectors:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    try:
                        # Must be a substantial field
                        rect = element.rect
                        if rect['height'] > 100:
                            return self._fill_element_with_verification(element, request_text, "placeholder-based")
                    except Exception:
                        continue
            
            return False
            
        except Exception as e:
            logger.error(f"Placeholder-based selection failed: {str(e)}")
            return False
    
    def _try_size_based_selection_smart(self, request_text: str) -> bool:
        """Find largest textarea but intelligently exclude address fields"""
        try:
            elements = self.driver.find_elements(By.CSS_SELECTOR, "textarea, [contenteditable='true'], [contenteditable]")
            
            candidates = []
            for element in elements:
                try:
                    rect = element.rect
                    area = rect['width'] * rect['height']
                    
                    # Must be substantial size
                    if area < 10000:
                        continue
                    
                    # Check context to avoid address fields
                    is_address = self._is_likely_address_field(element)
                    
                    candidates.append({
                        'element': element,
                        'area': area,
                        'is_address': is_address,
                        'rect': rect
                    })
                    
                except Exception:
                    continue
            
            # Sort by area, but prioritize non-address fields
            candidates.sort(key=lambda x: (not x['is_address'], x['area']), reverse=True)
            
            # Try the best candidates
            for candidate in candidates[:3]:
                if not candidate['is_address']:  # Prioritize non-address fields
                    try:
                        if self._fill_element_with_verification(candidate['element'], request_text, "size-based-smart"):
                            return True
                    except Exception:
                        continue
            
            return False
            
        except Exception as e:
            logger.error(f"Smart size-based selection failed: {str(e)}")
            return False
    
    def _try_javascript_detection(self, request_text: str) -> bool:
        """Use JavaScript to detect and fill rich text editors"""
        try:
            success = self.driver.execute_script(f"""
                var requestText = `{request_text.replace('`', '\\`')}`;
                
                // Strategy 1: TinyMCE
                try {{
                    if (typeof tinymce !== 'undefined' && tinymce.editors && tinymce.editors.length > 0) {{
                        var editor = tinymce.editors[0];
                        editor.setContent(requestText);
                        return 'tinymce-api';
                    }}
                }} catch(e) {{}}
                
                // Strategy 2: CKEditor
                try {{
                    if (typeof CKEDITOR !== 'undefined') {{
                        for (var instance in CKEDITOR.instances) {{
                            CKEDITOR.instances[instance].setData(requestText);
                            return 'ckeditor-api';
                        }}
                    }}
                }} catch(e) {{}}
                
                // Strategy 3: Find largest textarea that's NOT for address
                var textareas = Array.from(document.querySelectorAll('textarea'));
                var candidates = textareas.map(ta => {{
                    var rect = ta.getBoundingClientRect();
                    var area = rect.width * rect.height;
                    var parentText = (ta.parentElement?.textContent || '').toLowerCase();
                    var isAddress = parentText.includes('street') || parentText.includes('address');
                    var placeholder = (ta.placeholder || '').toLowerCase();
                    var isRequest = placeholder.includes('request') || placeholder.includes('enter your');
                    
                    return {{
                        element: ta,
                        area: area,
                        isAddress: isAddress,
                        isRequest: isRequest,
                        score: area * (isRequest ? 2 : 1) * (isAddress ? 0.1 : 1)
                    }};
                }}).filter(c => c.area > 5000);
                
                candidates.sort((a, b) => b.score - a.score);
                
                if (candidates.length > 0 && !candidates[0].isAddress) {{
                    var best = candidates[0].element;
                    best.focus();
                    best.value = requestText;
                    best.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    best.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    return 'textarea-smart';
                }}
                
                return false;
            """)
            
            if success:
                logger.info(f"JavaScript detection succeeded using: {success}")
                time.sleep(2)  # Allow event handlers to process
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"JavaScript detection failed: {str(e)}")
            return False
    
    def _try_content_editable_detection(self, request_text: str) -> bool:
        """Detect and fill contenteditable elements"""
        try:
            elements = self.driver.find_elements(By.CSS_SELECTOR, "[contenteditable='true'], [contenteditable]")
            
            for element in elements:
                try:
                    rect = element.rect
                    if rect['height'] > 100 and not self._is_likely_address_field(element):
                        return self._fill_element_with_verification(element, request_text, "contenteditable")
                except Exception:
                    continue
            
            return False
            
        except Exception as e:
            logger.error(f"Content-editable detection failed: {str(e)}")
            return False
    
    def _try_position_based_selection(self, request_text: str) -> bool:
        """Select based on position - request field should be near top"""
        try:
            elements = self.driver.find_elements(By.CSS_SELECTOR, "textarea, [contenteditable='true'], [contenteditable]")
            
            positioned_elements = []
            for element in elements:
                try:
                    rect = element.rect
                    if rect['height'] > 50 and not self._is_likely_address_field(element):
                        positioned_elements.append((element, rect['y']))
                except:
                    continue
            
            positioned_elements.sort(key=lambda x: x[1])  # Sort by Y position
            
            # Try top 3 elements
            for element, y_pos in positioned_elements[:3]:
                try:
                    if self._fill_element_with_verification(element, request_text, "position-based"):
                        return True
                except Exception:
                    continue
            
            return False
            
        except Exception as e:
            logger.error(f"Position-based selection failed: {str(e)}")
            return False
    
    def _try_label_association(self, request_text: str) -> bool:
        """Find field by associated labels"""
        try:
            label_texts = ['request description', 'description', 'request', 'enter your request']
            
            for label_text in label_texts:
                try:
                    labels = self.driver.find_elements(By.XPATH, f"//label[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{label_text}')]")
                    
                    for label in labels:
                        try:
                            # Get associated field
                            for_attr = label.get_attribute('for')
                            if for_attr:
                                field = self.driver.find_element(By.ID, for_attr)
                            else:
                                field = label.find_element(By.XPATH, ".//textarea | .//input | ./following-sibling::textarea | ./following-sibling::*//textarea")
                            
                            if self._fill_element_with_verification(field, request_text, "label-association"):
                                return True
                                
                        except Exception:
                            continue
                            
                except Exception:
                    continue
            
            return False
            
        except Exception as e:
            logger.error(f"Label association failed: {str(e)}")
            return False
    
    def _is_likely_address_field(self, element) -> bool:
        """Check if element is likely an address field"""
        try:
            # Check parent text for address indicators
            parent_text = ""
            try:
                parent = element.find_element(By.XPATH, "../..")
                parent_text = parent.text.lower()
            except:
                pass
            
            # Check element attributes
            element_attrs = ""
            try:
                element_attrs = f"{element.get_attribute('name')} {element.get_attribute('id')} {element.get_attribute('placeholder')}".lower()
            except:
                pass
            
            # Address indicators
            address_indicators = ['street', 'address', 'addr', 'mailing']
            request_indicators = ['request', 'description', 'enter your']
            
            has_address_indicator = any(indicator in parent_text or indicator in element_attrs for indicator in address_indicators)
            has_request_indicator = any(indicator in parent_text or indicator in element_attrs for indicator in request_indicators)
            
            # If it has request indicators, it's probably NOT an address field
            if has_request_indicator:
                return False
            
            return has_address_indicator
            
        except Exception:
            return False
    
    def _fill_element_with_verification(self, element, text: str, method: str) -> bool:
        """Fill element and verify success"""
        try:
            self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
            time.sleep(1)
            
            # Handle different element types
            if element.tag_name.lower() == 'textarea':
                element.click()
                element.clear()
                element.send_keys(text)
                content = element.get_attribute('value')
            elif element.get_attribute('contenteditable'):
                element.click()
                element.send_keys(Keys.CONTROL + "a")
                element.send_keys(text)
                content = element.text or element.get_attribute('textContent')
            else:
                element.click()
                element.clear()
                element.send_keys(text)
                content = element.get_attribute('value') or element.text
            
            # Verify substantial content was entered
            if content and len(content) > 100:
                logger.info(f"✅ Successfully filled using {method}: {len(content)} characters")
                return True
            else:
                logger.warning(f"⚠️ {method} may have failed - only {len(content) if content else 0} characters")
                return False
                
        except Exception as e:
            logger.warning(f"❌ {method} fill failed: {str(e)}")
            return False
    
    def _fill_contact_information(self, user_info: Dict[str, str]) -> Dict[str, Any]:
        """Fill contact information fields"""
        
        result = {
            'filled_count': 0,
            'errors': [],
            'skipped_count': 0
        }
        
        try:
            # Email field
            email_result = self._try_fill_field([
                (By.CSS_SELECTOR, "input[type='email']"),
                (By.CSS_SELECTOR, "input[name*='email']"),
                (By.CSS_SELECTOR, "input[id*='email']")
            ], user_info.get('email', ''), "Email", required=False)
            
            if email_result:
                result['filled_count'] += 1
            elif email_result is None:
                result['skipped_count'] += 1
            
            # Name field
            full_name = f"{user_info.get('first_name', '')} {user_info.get('last_name', '')}".strip()
            name_result = self._try_fill_field([
                (By.CSS_SELECTOR, "input[name*='name']"),
                (By.CSS_SELECTOR, "input[id*='name']"),
                (By.CSS_SELECTOR, "input[placeholder*='Name']")
            ], full_name, "Name", required=False)
            
            if name_result:
                result['filled_count'] += 1
            elif name_result is None:
                result['skipped_count'] += 1
            
            # Phone field
            phone_result = self._try_fill_field([
                (By.CSS_SELECTOR, "input[name*='phone']"),
                (By.CSS_SELECTOR, "input[id*='phone']"),
                (By.CSS_SELECTOR, "input[type='tel']")
            ], user_info.get('phone', ''), "Phone", required=False)
            
            if phone_result:
                result['filled_count'] += 1
            
            # Street address - be very careful here to only fill actual address fields
            address_result = self._try_fill_field([
                (By.CSS_SELECTOR, "textarea[name*='address']"),
                (By.CSS_SELECTOR, "textarea[id*='address']"),
                (By.CSS_SELECTOR, "textarea[placeholder*='street']")
            ], user_info.get('address', ''), "Street Address", required=False, is_textarea=True)
            
            if address_result:
                result['filled_count'] += 1
            
            # City, State, Zip, Company fields
            for field_name, selectors, value_key in [
                ("City", ["input[name*='city']", "input[id*='city']"], 'city'),
                ("Zip", ["input[name*='zip']", "input[id*='zip']"], 'zip'),
                ("Company", ["input[name*='company']", "input[id*='company']", "input[name*='organization']"], 'organization')
            ]:
                field_result = self._try_fill_field([
                    (By.CSS_SELECTOR, selector) for selector in selectors
                ], user_info.get(value_key, user_info.get('company', '') if value_key == 'organization' else ''), field_name, required=False)
                
                if field_result:
                    result['filled_count'] += 1
            
            # State dropdown
            if user_info.get('state'):
                try:
                    state_select = WebDriverWait(self.driver, 3).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "select"))
                    )
                    select = Select(state_select)
                    
                    try:
                        select.select_by_value(user_info['state'])
                        result['filled_count'] += 1
                        logger.info(f"Selected state: {user_info['state']}")
                    except:
                        try:
                            select.select_by_visible_text(user_info['state'])
                            result['filled_count'] += 1
                            logger.info(f"Selected state by text: {user_info['state']}")
                        except:
                            logger.warning("Could not select state value")
                except:
                    logger.warning("Could not find state dropdown")
            
            logger.info(f"Contact info summary: {result['filled_count']} filled, {result['skipped_count']} pre-filled/skipped")
            return result
            
        except Exception as e:
            logger.error(f"Error filling contact information: {str(e)}")
            result['errors'].append(f"Contact information error: {str(e)}")
            return result
    
    def _try_fill_field(self, selectors, value, field_name, required=False, is_textarea=False):
        """Try multiple selectors to find and fill a field"""
        
        if not value:
            if required:
                logger.error(f"No value provided for required field: {field_name}")
                return False
            else:
                logger.debug(f"No value provided for optional field: {field_name}")
                return False
        
        for selector_type, selector_value in selectors:
            try:
                field = WebDriverWait(self.driver, 3).until(
                    EC.presence_of_element_located((selector_type, selector_value))
                )
                
                # Check if field already has content
                current_value = field.get_attribute('value')
                if current_value and current_value.strip():
                    logger.info(f"{field_name} already filled with: '{current_value}'")
                    return None  # Indicate field was already filled
                
                # Fill the field
                self.driver.execute_script("arguments[0].scrollIntoView(true);", field)
                time.sleep(0.5)
                
                field.click()
                field.clear()
                field.send_keys(value)
                
                # Verify
                new_value = field.get_attribute('value')
                if new_value and value in new_value:
                    logger.info(f"Successfully filled {field_name}: '{value}'")
                    return True
                else:
                    logger.warning(f"Field {field_name} may not have been filled correctly")
                    continue
                
            except TimeoutException:
                continue
            except Exception as e:
                logger.warning(f"Error filling {field_name} with {selector_type}: {str(e)}")
                continue
        
        if required:
            logger.error(f"Could not find required field: {field_name}")
            return False
        else:
            logger.debug(f"Could not find optional field: {field_name}")
            return False
    
    def _submit_form(self) -> bool:
        """Submit the form"""
        try:
            logger.info("Looking for submit button")
            
            submit_selectors = [
                (By.XPATH, "//button[contains(text(), 'Make request')]"),
                (By.XPATH, "//input[@value='Make request']"),
                (By.CSS_SELECTOR, "button[type='submit']"),
                (By.CSS_SELECTOR, "input[type='submit']"),
                (By.XPATH, "//button[contains(text(), 'Submit')]"),
                (By.XPATH, "//input[contains(@value, 'Submit')]")
            ]
            
            for selector_type, selector_value in submit_selectors:
                try:
                    submit_btn = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((selector_type, selector_value))
                    )
                    
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", submit_btn)
                    time.sleep(1)
                    
                    submit_btn.click()
                    logger.info(f"Successfully clicked submit button using: {selector_type}")
                    return True
                    
                except TimeoutException:
                    continue
                except Exception as e:
                    logger.warning(f"Failed to click submit with {selector_type}: {str(e)}")
                    continue
            
            logger.error("Could not find or click submit button")
            return False
            
        except Exception as e:
            logger.error(f"Error submitting form: {str(e)}")
            return False
    
    def _get_confirmation_info(self) -> Optional[str]:
        """Get confirmation information after submission"""
        try:
            time.sleep(3)
            
            confirmation_indicators = [
                "confirmation", "submitted", "request number", "thank you",
                "received", "successfully", "request has been", "your request"
            ]
            
            try:
                page_text = self.driver.find_element(By.TAG_NAME, "body").text.lower()
                
                for indicator in confirmation_indicators:
                    if indicator in page_text:
                        logger.info(f"Found confirmation indicator: '{indicator}'")
                        
                        lines = page_text.split('\n')
                        for line in lines:
                            if indicator in line.lower() and len(line.strip()) > 10:
                                return f"Request submitted successfully: {line.strip()}"
                        
                        return f"Request submitted successfully (found: '{indicator}')"
                
            except Exception as e:
                logger.warning(f"Could not get page text: {str(e)}")
            
            # Check URL and title for confirmation
            current_url = self.driver.current_url.lower()
            url_indicators = ['thank', 'confirm', 'success', 'submitted']
            
            for indicator in url_indicators:
                if indicator in current_url:
                    return f"Request likely submitted - URL indicates success: {self.driver.current_url}"
            
            try:
                page_title = self.driver.title.lower()
                title_indicators = ['thank', 'confirm', 'success', 'submitted']
                
                for indicator in title_indicators:
                    if indicator in page_title:
                        return f"Request submitted - page title indicates success: {self.driver.title}"
            except:
                pass
            
            return f"Form submitted. Current page: {self.driver.title} | URL: {self.driver.current_url}"
            
        except Exception as e:
            logger.error(f"Failed to get confirmation: {str(e)}")
            return "Form was submitted but confirmation status is unknown"
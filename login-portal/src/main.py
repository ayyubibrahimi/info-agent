from llm import gpt_4o
import logging
from models import LoginCredentials
from portal_agent import PortalAgent
import os
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():    
    # Portal URL
    portal_url = os.environ.get("PORTAL_URL")

    credentials = LoginCredentials(
        username= os.environ.get("USERNAME"),
        password= os.environ.get("PASSWORD")
    )
    

    # portal_url = "https://nola.nextrequest.com/"
    
    # # Credentials (optional)
    # credentials = LoginCredentials(
    #     username="",
    #     password="")

    
    # User information for requests
    user_info = {
        'first_name': 'Ayyub',
        'last_name': 'Ibrahim',
        'email': 'ayyub.ibrahimi@gmail.com',
        'phone': '555-123-4567',
        'organization': 'Independent Researcher'
    }
    
    print("\n" + "="*80)
    print("🚀 ALAMEDA COUNTY PORTAL AUTOMATION SYSTEM")
    print("="*80)
    print("Features:")
    print("  ✅ Portal access and login")
    print("  ✅ AI-powered request generation")
    print("  ✅ Automated form submission")
    print("  ✅ 🧠 Intelligent request analysis")
    print("  ✅ 🎯 Interactive request selection")
    print("  ✅ Screenshot documentation")
    print("="*80)
    
    # Run the session
    with PortalAgent(gpt_4o, headless=False) as agent:  # Using gpt_4o for better analysis
        
        # Step 1: Access portal and login
        print("\n🔐 PHASE 1: PORTAL ACCESS & LOGIN")
        print("-" * 50)
        
        results = agent.access_portal_session(
            portal_url=portal_url,
            credentials=credentials
        )
        
        # Display login results
        print(f"\n📊 LOGIN RESULTS:")
        print(f"Portal URL: {portal_url}")
        print(f"Navigation successful: {results.get('navigation', {}).get('success', False)}")
        
        if 'navigation' in results and results['navigation']['success']:
            nav = results['navigation']
            print(f"✅ Successfully accessed portal")
            print(f"Final URL: {nav['url']}")
            print(f"Page title: {nav['title']}")
            print(f"Page type: {nav['analysis'].page_type}")
            print(f"Login required: {nav['analysis'].login_required}")
            print(f"Key elements: {nav['analysis'].key_elements}")
        else:
            print(f"❌ Failed to access portal")
            if 'error' in results.get('navigation', {}):
                print(f"Error: {results['navigation']['error']}")
            return
        
        # Check login status
        login_successful = False
        if 'login' in results:
            if results['login'].get('skipped'):
                print(f"Login skipped: {results['login']['reason']}")
                login_successful = True  # Assume we're logged in if login was skipped
            else:
                success = results['login'].get('success', False)
                print(f"Login successful: {success}")
                login_successful = success
                
                if not success and 'error' in results['login']:
                    print(f"Login error: {results['login']['error']}")
        
        print(f"Total screenshots taken: {len(agent.screenshot_manager.screenshots)}")
        
        # Main menu for logged-in users
        if login_successful and agent.is_logged_in:
            while True:
                try:
                    print("\n" + "="*80)
                    print("🎯 CHOOSE YOUR ACTION")
                    print("="*80)
                    print("1. 📝 Submit a new public records request")
                    print("2. 🎯 Analyze specific requests")
                    print("3. 🚪 Exit")
                    print("-" * 80)
                    
                    choice = input("Enter your choice (1-3): ").strip()
                    
                    if choice == '1':
                        # PHASE 2: Submit new request
                        print("\n📝 PHASE 2: PUBLIC RECORDS REQUEST SUBMISSION")
                        print("-" * 50)
                        
                        user_topic = input("🔍 Enter your request topic: ").strip()
                        if not user_topic:
                            print("Please enter a topic")
                            continue
                        
                        print(f"\n🚀 Processing request for: '{user_topic}'")
                        request_result = agent.submit_public_records_request(user_topic, user_info)
                        
                        if request_result['success']:
                            print("✅ Request submitted successfully!")
                            if 'submission_result' in request_result:
                                submission = request_result['submission_result']
                                print(f"Steps completed: {', '.join(submission.get('steps_completed', []))}")
                                if 'confirmation' in submission:
                                    print(f"Confirmation: {submission['confirmation']}")
                        else:
                            print("❌ Request submission failed")
                            if 'errors' in request_result:
                                print(f"Errors: {', '.join(request_result['errors'])}")
                    
                    elif choice == '2':
                        # PHASE 3 INTERACTIVE: Choose specific requests
                        print("\n🎯 PHASE 3 INTERACTIVE: ANALYZE SPECIFIC REQUESTS")
                        print("-" * 50)
                        print("This will show you all available requests and let you choose which ones to analyze with AI...")
                        print("You'll get detailed correspondence summaries and status updates!")
                        
                        try:
                            interactive_result = agent.analyze_specific_requests()
                            
                            if interactive_result['success']:
                                print("\n✅ Interactive analysis completed successfully!")
                                
                                # Display summary based on analysis type
                                if interactive_result.get('analysis_type') == 'multi_request':
                                    total = interactive_result.get('total_requests', 0)
                                    successful = interactive_result.get('successful_analyses', 0)
                                    failed = interactive_result.get('failed_analyses', 0)
                                    
                                    print(f"📊 Analyzed {successful}/{total} requests successfully")
                                    if failed > 0:
                                        print(f"⚠️  {failed} requests failed to analyze")
                                
                            else:
                                print(f"❌ Interactive analysis failed: {interactive_result['error']}")
                                
                        except Exception as e:
                            print(f"❌ Interactive analysis error: {str(e)}")
                    
                    elif choice == '3':
                        print("👋 Goodbye! Thanks for using the Alameda County Portal Automation System!")
                        break
                    
                    else:
                        print("❌ Invalid choice. Please enter a number between 1-3.")
                        continue
                    
                    # Ask if user wants to continue
                    if choice != '3':
                        print("\n" + "="*60)
                        continue_choice = input("🔄 Return to main menu? (y/n): ").strip().lower()
                        if continue_choice != 'y':
                            print("👋 Goodbye!")
                            break
                        
                except KeyboardInterrupt:
                    print("\n\n👋 Operation cancelled. Goodbye!")
                    break
                except Exception as e:
                    print(f"\n❌ Unexpected error: {str(e)}")
                    print("Please try again or choose a different option.")
                    continue
        
        else:
            print("\n⚠️  LOGIN REQUIRED")
            print("To use the portal features, ensure login credentials are correct and try again.")
            print("The system requires authentication to access and analyze your public records requests.")
        
        # Final status
        status = agent.get_portal_status()
        print(f"\n📈 FINAL SESSION STATUS:")
        print("=" * 50)
        print(f"🔐 Logged in: {status['is_logged_in']}")
        print(f"🚀 Request functionality: {status['request_functionality_available']}")
        print(f"📸 Screenshots captured: {status['total_screenshots']}")
        print(f"🌐 Current URL: {status['current_url']}")
        print("=" * 50)
        
        print("\n📁 CHECK GENERATED FILES:")
        print("   📋 alameda_portal_session_[timestamp].json - Session data")
        print("   📄 alameda_portal_summary_[timestamp].txt - Session summary")
        print("   🎯 alameda_interactive_analysis_[timestamp].json - Interactive analysis data")
        print("   📸 Screenshots folder - All captured screenshots")
        
        print(f"\n🎉 Session completed successfully! All files saved to your project directory.")

if __name__ == "__main__":
    main()
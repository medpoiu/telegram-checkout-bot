#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
بوت تيليجرام للوصول لصفحة الدفع - يدعم جميع المنصات
Telegram Bot for Checkout Finder - Universal Platform Support
"""

import os
import time
import random
import string
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import re

# إعداد السجلات
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# البيانات العشوائية
FIRST_NAMES = ['John', 'Mike', 'David', 'James', 'Robert', 'William', 'Richard', 'Thomas', 'Charles', 'Daniel']
LAST_NAMES = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis', 'Rodriguez', 'Martinez']
CITIES = ['New York', 'Los Angeles', 'Chicago', 'Houston', 'Phoenix', 'Philadelphia', 'San Antonio', 'San Diego', 'Dallas', 'San Jose']
STREETS = ['Main St', 'Oak Ave', 'Maple Dr', 'Cedar Ln', 'Pine Rd', 'Elm St', 'Washington Blvd', 'Park Ave', 'Lake Dr', 'Hill St']


def generate_random_data():
    """توليد بيانات عشوائية"""
    return {
        'first_name': random.choice(FIRST_NAMES),
        'last_name': random.choice(LAST_NAMES),
        'email': f"{''.join(random.choices(string.ascii_lowercase, k=8))}@example.com",
        'phone': f"+1{''.join(random.choices(string.digits, k=10))}",
        'address': f"{random.randint(100, 9999)} {random.choice(STREETS)}",
        'city': random.choice(CITIES),
        'postcode': ''.join(random.choices(string.digits, k=5)),
        'country': 'US',
        'state': 'NY'
    }


class UniversalCheckoutBot:
    """بوت يدعم جميع منصات التجارة الإلكترونية"""
    
    def __init__(self):
        self.driver = None
        self.wait = None
    
    def init_driver(self):
        """تهيئة Selenium"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--disable-gpu')
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 20)
    
    def close_driver(self):
        """إغلاق المتصفح"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None
    
    def extract_price(self, text):
        """استخراج السعر من النص - محسّن"""
        if not text:
            return None
        
        # تنظيف النص
        text = text.replace(',', '').replace('\n', ' ')
        
        # أنماط متعددة للأسعار
        patterns = [
            r'\$\s*(\d+\.?\d*)',           # $50 or $ 50
            r'(\d+\.?\d*)\s*\$',           # 50$ or 50 $
            r'£\s*(\d+\.?\d*)',            # £50
            r'(\d+\.?\d*)\s*£',            # 50£
            r'€\s*(\d+\.?\d*)',            # €50
            r'(\d+\.?\d*)\s*€',            # 50€
            r'USD\s*(\d+\.?\d*)',          # USD 50
            r'(\d+\.?\d*)\s*USD',          # 50 USD
            r'(\d+\.?\d*)\s*лв',           # 50 лв
            r'(\d+\.\d{2})',               # 50.99
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    price = float(match.group(1))
                    if 0.01 < price < 100000:  # سعر معقول
                        return price
                except:
                    continue
        
        return None
    
    def find_products_universal(self, url):
        """البحث عن المنتجات - يدعم جميع المنصات"""
        logger.info(f"🔍 البحث عن منتجات في: {url}")
        
        try:
            self.driver.get(url)
            time.sleep(4)
            
            # التمرير لتحميل المنتجات
            for _ in range(3):
                self.driver.execute_script("window.scrollBy(0, 500);")
                time.sleep(1)
            
            products = []
            
            # Selectors شاملة لجميع المنصات
            product_selectors = [
                # Shopify
                '.product-card', '.product-item', '.grid-product', 
                'div[class*="product"]', 'article[class*="product"]',
                '.product-grid-item', '.product__grid-item',
                
                # WooCommerce
                '.product', 'li.product', 'article.product',
                '.woocommerce-LoopProduct-link',
                
                # Magento
                '.product-item-info', '.product-item',
                
                # PrestaShop
                '.product-miniature', '.js-product-miniature',
                
                # BigCommerce
                '.card', '.product-grid',
                
                # عام
                '[data-product]', '[data-product-id]',
                'a[href*="/product"]', 'a[href*="/products/"]'
            ]
            
            for selector in product_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    
                    if len(elements) > 2:  # على الأقل 3 عناصر
                        logger.info(f"✅ وجدت {len(elements)} عنصر بـ {selector}")
                        
                        for element in elements[:50]:  # أول 50 منتج
                            try:
                                # الرابط
                                link = None
                                try:
                                    if element.tag_name == 'a':
                                        link = element.get_attribute('href')
                                    else:
                                        link_elem = element.find_element(By.TAG_NAME, 'a')
                                        link = link_elem.get_attribute('href')
                                except:
                                    pass
                                
                                if not link or link == url or 'javascript:' in link:
                                    continue
                                
                                # السعر - selectors شاملة
                                price_selectors = [
                                    # عام
                                    '[class*="price"]', '[class*="Price"]',
                                    '[data-price]', 'span.money',
                                    
                                    # Shopify
                                    '.price__regular', '.price-item',
                                    
                                    # WooCommerce
                                    '.woocommerce-Price-amount', '.amount', 'bdi',
                                    
                                    # Magento
                                    '.price-wrapper', '.price-box',
                                    
                                    # عام
                                    'span', 'div', 'p'
                                ]
                                
                                price_text = None
                                for price_sel in price_selectors:
                                    try:
                                        price_elems = element.find_elements(By.CSS_SELECTOR, price_sel)
                                        for price_elem in price_elems:
                                            text = price_elem.text.strip()
                                            if text and len(text) < 50 and ('$' in text or '£' in text or '€' in text or re.search(r'\d+\.\d{2}', text)):
                                                price_text = text
                                                break
                                        if price_text:
                                            break
                                    except:
                                        continue
                                
                                if not price_text:
                                    continue
                                
                                # استخراج السعر
                                price = self.extract_price(price_text)
                                
                                if price:
                                    # الاسم
                                    name = 'Product'
                                    try:
                                        name_selectors = [
                                            'h2', 'h3', 'h4',
                                            '.product-title', '.product__title',
                                            '[class*="title"]', '[class*="name"]',
                                            'a'
                                        ]
                                        for name_sel in name_selectors:
                                            try:
                                                name_elem = element.find_element(By.CSS_SELECTOR, name_sel)
                                                name_text = name_elem.text.strip()
                                                if name_text and len(name_text) > 2:
                                                    name = name_text
                                                    break
                                            except:
                                                continue
                                    except:
                                        pass
                                    
                                    products.append({
                                        'name': name[:100],
                                        'price': price,
                                        'price_text': price_text,
                                        'url': link
                                    })
                            
                            except Exception as e:
                                continue
                        
                        if len(products) > 0:
                            break
                
                except Exception as e:
                    continue
            
            if not products:
                logger.warning("❌ لم يتم العثور على منتجات")
                return []
            
            # ترتيب حسب السعر - الأرخص أولاً
            products.sort(key=lambda x: x['price'])
            
            logger.info(f"✅ وجدت {len(products)} منتج بأسعار")
            logger.info(f"💰 أرخص منتج: {products[0]['name']} - {products[0]['price_text']}")
            
            return products
            
        except Exception as e:
            logger.error(f"❌ خطأ في البحث: {e}")
            return []
    
    def add_to_cart_universal(self, product_url):
        """إضافة للسلة - يدعم جميع المنصات"""
        logger.info(f"🛒 إضافة للسلة: {product_url}")
        
        try:
            self.driver.get(product_url)
            time.sleep(3)
            
            # Selectors شاملة لأزرار "Add to Cart"
            add_to_cart_selectors = [
                # Shopify
                'button[name="add"]', 'button[type="submit"][name="add"]',
                '.product-form__submit', 'button.btn--add-to-cart',
                '[data-add-to-cart]',
                
                # WooCommerce
                'button[name="add-to-cart"]', '.single_add_to_cart_button',
                'button.add_to_cart_button',
                
                # Magento
                'button#product-addtocart-button', '.action.tocart',
                
                # PrestaShop
                '.add-to-cart', 'button[data-button-action="add-to-cart"]',
                
                # BigCommerce
                'button[data-button-type="add-cart"]',
                
                # عام
                'button[class*="add"]', 'button[class*="cart"]',
                'input[type="submit"][value*="Add"]',
                'a[class*="add-to-cart"]'
            ]
            
            # محاولة النقر
            for selector in add_to_cart_selectors:
                try:
                    button = self.wait.until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
                    time.sleep(1)
                    button.click()
                    logger.info(f"✅ تم النقر على: {selector}")
                    time.sleep(3)
                    return True
                except:
                    continue
            
            # محاولة بديلة بـ XPath
            try:
                button = self.driver.find_element(By.XPATH, 
                    "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'add to cart') or contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'add to bag')]"
                )
                button.click()
                logger.info("✅ تم النقر (XPath)")
                time.sleep(3)
                return True
            except:
                pass
            
            logger.warning("⚠️ لم يتم العثور على زر Add to Cart")
            return False
            
        except Exception as e:
            logger.error(f"❌ خطأ في الإضافة للسلة: {e}")
            return False
    
    def go_to_checkout_universal(self):
        """الانتقال للدفع - يدعم جميع المنصات"""
        logger.info("💳 الانتقال لصفحة الدفع")
        
        try:
            time.sleep(2)
            
            # محاولة 1: روابط checkout
            checkout_texts = ['checkout', 'view cart', 'proceed', 'go to cart', 'cart']
            for text in checkout_texts:
                try:
                    links = self.driver.find_elements(By.XPATH, 
                        f"//a[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{text}')]"
                    )
                    for link in links[:3]:
                        try:
                            link.click()
                            time.sleep(3)
                            if 'checkout' in self.driver.current_url.lower() or 'cart' in self.driver.current_url.lower():
                                logger.info(f"✅ نقر على رابط: {text}")
                                break
                        except:
                            continue
                except:
                    continue
            
            # محاولة 2: أزرار checkout
            checkout_selectors = [
                'a[href*="checkout"]', 'button[name*="checkout"]',
                '.checkout-button', '[data-checkout]',
                'a.btn-checkout', 'button.checkout'
            ]
            
            for selector in checkout_selectors:
                try:
                    button = self.wait.until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    button.click()
                    time.sleep(3)
                    logger.info(f"✅ نقر على: {selector}")
                    break
                except:
                    continue
            
            # محاولة 3: الذهاب مباشرة
            current_url = self.driver.current_url
            base_url = '/'.join(current_url.split('/')[:3])
            
            for path in ['/checkout', '/cart/checkout', '/checkout/', '/cart']:
                try:
                    test_url = base_url + path
                    self.driver.get(test_url)
                    time.sleep(3)
                    
                    if 'checkout' in self.driver.current_url.lower():
                        logger.info(f"✅ وصلنا عبر: {test_url}")
                        return True
                except:
                    continue
            
            # التحقق النهائي - يجب أن يكون checkout وليس cart فقط
            current = self.driver.current_url.lower()
            
            # إذا كنا في cart، حاول النقر على زر checkout
            if 'cart' in current and 'checkout' not in current:
                logger.info("📍 نحن في صفحة السلة، البحث عن زر checkout...")
                checkout_buttons = [
                    "//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'checkout')]",
                    "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'checkout')]",
                    "//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'proceed')]",
                    ".wc-proceed-to-checkout a",
                    "a.checkout-button"
                ]
                
                for btn_selector in checkout_buttons:
                    try:
                        if btn_selector.startswith('//'):
                            btn = self.driver.find_element(By.XPATH, btn_selector)
                        else:
                            btn = self.driver.find_element(By.CSS_SELECTOR, btn_selector)
                        
                        if btn.is_displayed():
                            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                            time.sleep(1)
                            btn.click()
                            logger.info(f"✅ نقر على زر checkout")
                            time.sleep(4)
                            
                            if 'checkout' in self.driver.current_url.lower():
                                logger.info("✅ وصلنا لصفحة checkout!")
                                return True
                    except:
                        continue
            
            # تحقق نهائي
            current = self.driver.current_url.lower()
            if 'checkout' in current:
                logger.info("✅ نحن في صفحة checkout")
                return True
            
            logger.warning(f"⚠️ لم نصل لـ checkout. الصفحة الحالية: {self.driver.current_url}")
            return False
            
        except Exception as e:
            logger.error(f"❌ خطأ في الانتقال: {e}")
            return False
    
    def fill_billing_universal(self):
        """ملء البيانات - يدعم جميع المنصات"""
        logger.info("📝 ملء البيانات...")
        
        try:
            data = generate_random_data()
            
            # خريطة الحقول - شاملة
            field_mappings = [
                # First Name
                (['first_name', 'firstName', 'billing_first_name', 'checkout_email_or_phone'], data['first_name']),
                
                # Last Name
                (['last_name', 'lastName', 'billing_last_name'], data['last_name']),
                
                # Email
                (['email', 'billing_email', 'checkout_email'], data['email']),
                
                # Phone
                (['phone', 'telephone', 'billing_phone'], data['phone']),
                
                # Address
                (['address', 'address1', 'billing_address_1', 'street'], data['address']),
                
                # City
                (['city', 'billing_city'], data['city']),
                
                # Postcode
                (['postcode', 'zip', 'postal_code', 'billing_postcode'], data['postcode']),
            ]
            
            filled = 0
            
            for field_ids, value in field_mappings:
                for field_id in field_ids:
                    try:
                        field = None
                        
                        # محاولة بـ ID
                        try:
                            field = self.driver.find_element(By.ID, field_id)
                        except:
                            pass
                        
                        # محاولة بـ Name
                        if not field:
                            try:
                                field = self.driver.find_element(By.NAME, field_id)
                            except:
                                pass
                        
                        # محاولة بـ CSS
                        if not field:
                            try:
                                field = self.driver.find_element(By.CSS_SELECTOR, f'input[name="{field_id}"]')
                            except:
                                pass
                        
                        if field and field.is_displayed():
                            try:
                                field.clear()
                                field.send_keys(value)
                                filled += 1
                                time.sleep(0.3)
                                logger.info(f"✅ ملء: {field_id}")
                                break  # نجح، انتقل للحقل التالي
                            except:
                                pass
                    except:
                        continue
            
            logger.info(f"✅ تم ملء {filled} حقل")
            return filled > 0, data
            
        except Exception as e:
            logger.error(f"❌ خطأ في الملء: {e}")
            return False, None
    
    def get_checkout_info(self):
        """الحصول على معلومات الدفع"""
        logger.info("📊 جمع المعلومات")
        
        try:
            info = {
                'checkout_url': self.driver.current_url,
                'page_title': self.driver.title,
                'payment_methods': [],
                'total_amount': None
            }
            
            # كشف طرق الدفع
            page_source = self.driver.page_source.lower()
            
            payment_keywords = {
                'PayPal': 'paypal',
                'Stripe': 'stripe',
                'Credit Card': 'credit',
                'Apple Pay': 'apple pay',
                'Google Pay': 'google pay',
                'Braintree': 'braintree',
                'Square': 'square'
            }
            
            for method, keyword in payment_keywords.items():
                if keyword in page_source:
                    info['payment_methods'].append(method)
            
            # المبلغ
            total_selectors = [
                '.total', '.order-total', '[class*="total"]',
                '[data-total]', '.grand-total'
            ]
            
            for selector in total_selectors:
                try:
                    elems = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for elem in elems:
                        text = elem.text.strip()
                        if text and ('$' in text or '£' in text or '€' in text):
                            info['total_amount'] = text
                            break
                    if info['total_amount']:
                        break
                except:
                    continue
            
            return info
            
        except Exception as e:
            logger.error(f"❌ خطأ في جمع المعلومات: {e}")
            return {'checkout_url': self.driver.current_url}
    
    def process_website(self, url):
        """معالجة الموقع - كامل"""
        try:
            self.init_driver()
            
            # 1. البحث
            products = self.find_products_universal(url)
            if not products:
                return {'success': False, 'error': 'لم يتم العثور على منتجات'}
            
            product = products[0]  # الأرخص
            
            # 2. إضافة للسلة
            if not self.add_to_cart_universal(product['url']):
                return {'success': False, 'error': 'فشل في إضافة المنتج للسلة'}
            
            # 3. الانتقال للدفع
            if not self.go_to_checkout_universal():
                return {'success': False, 'error': 'فشل في الوصول لصفحة الدفع'}
            
            # 4. ملء البيانات
            filled, random_data = self.fill_billing_universal()
            
            # 5. جمع المعلومات
            checkout_info = self.get_checkout_info()
            
            return {
                'success': True,
                'product': product,
                'checkout_info': checkout_info,
                'filled_data': random_data if filled else None
            }
            
        except Exception as e:
            logger.error(f"❌ خطأ عام: {e}")
            return {'success': False, 'error': str(e)}
        
        finally:
            self.close_driver()


# معالجات البوت
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج /start"""
    welcome = (
        "🤖 <b>مرحباً بك في بوت الوصول لصفحة الدفع!</b>\n\n"
        "✨ <b>ماذا أفعل؟</b>\n"
        "• أبحث عن <b>أرخص منتج</b> في الموقع 🔍\n"
        "• أضيفه للسلة تلقائياً 🛒\n"
        "• أملأ بيانات الفواتير عشوائياً 📝\n"
        "• أعطيك رابط الدفع الجاهز! 🔗\n\n"
        "🌐 <b>المنصات المدعومة:</b>\n"
        "✅ Shopify\n"
        "✅ WooCommerce\n"
        "✅ Magento\n"
        "✅ BigCommerce\n"
        "✅ PrestaShop\n"
        "✅ وأي موقع تجارة إلكترونية آخر!\n\n"
        "📝 <b>كيف تستخدمني؟</b>\n"
        "فقط أرسل لي رابط الموقع:\n\n"
        "<code>https://example.com</code>"
    )
    await update.message.reply_text(welcome, parse_mode='HTML')


async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج الروابط"""
    url = update.message.text.strip()
    
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    waiting_msg = await update.message.reply_text(
        "⏳ <b>جاري التحليل...</b>\n\n"
        "🔍 البحث عن أرخص منتج\n"
        "⏱️ قد يستغرق 30-60 ثانية...",
        parse_mode='HTML'
    )
    
    bot = UniversalCheckoutBot()
    result = bot.process_website(url)
    
    if result['success']:
        product = result['product']
        checkout_info = result['checkout_info']
        filled_data = result.get('filled_data')
        
        response = (
            "✅ <b>تم بنجاح!</b>\n\n"
            f"📦 <b>المنتج:</b> {product['name'][:80]}\n"
            f"💰 <b>السعر:</b> {product['price_text']}\n\n"
            f"🔗 <b>رابط الدفع:</b>\n<code>{checkout_info['checkout_url']}</code>\n\n"
        )
        
        if checkout_info.get('total_amount'):
            response += f"💵 <b>المبلغ الإجمالي:</b> {checkout_info['total_amount']}\n"
        
        if checkout_info.get('payment_methods'):
            response += f"💳 <b>طرق الدفع:</b> {', '.join(checkout_info['payment_methods'])}\n"
        
        if filled_data:
            response += (
                f"\n📝 <b>البيانات المُدخلة (عشوائية):</b>\n"
                f"• الاسم: {filled_data['first_name']} {filled_data['last_name']}\n"
                f"• البريد: {filled_data['email']}\n"
                f"• الهاتف: {filled_data['phone']}\n"
                f"• العنوان: {filled_data['address']}, {filled_data['city']}\n"
            )
        
        response += "\n✨ <b>الرابط جاهز! افتحه وأكمل الدفع.</b>"
        
        await waiting_msg.edit_text(response, parse_mode='HTML')
    else:
        error_msg = (
            f"❌ <b>فشل التحليل</b>\n\n"
            f"السبب: {result.get('error', 'خطأ غير معروف')}\n\n"
            f"💡 جرب موقعاً آخر أو تأكد من الرابط."
        )
        await waiting_msg.edit_text(error_msg, parse_mode='HTML')


def main():
    """الدالة الرئيسية"""
    TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
    
    if not TOKEN:
        logger.error("❌ TELEGRAM_BOT_TOKEN غير موجود!")
        return
    
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
    
    logger.info("✅ البوت يعمل...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()

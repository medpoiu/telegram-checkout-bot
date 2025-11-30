#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
بوت تيليجرام للوصول لصفحة الدفع
Telegram Bot for Checkout Finder
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
        'country': 'US'
    }


class CheckoutBot:
    """فئة البوت"""
    
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
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        chrome_options.add_argument('--window-size=1920,1080')
        
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
        """استخراج السعر من النص"""
        if not text:
            return None
        
        text = text.replace(',', '')
        patterns = [
            r'(\d+\.?\d*)\s*(?:£|GBP)',
            r'(?:£|GBP)\s*(\d+\.?\d*)',
            r'(\d+\.?\d*)\s*(?:\$|USD)',
            r'(?:\$|USD)\s*(\d+\.?\d*)',
            r'(\d+\.?\d*)\s*(?:€|EUR)',
            r'(?:€|EUR)\s*(\d+\.?\d*)',
            r'(\d+\.?\d*)\s*(?:лв)',
            r'(\d+\.?\d*)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    return float(match.group(1))
                except:
                    continue
        return None
    
    def find_products(self, url):
        """البحث عن المنتجات"""
        logger.info(f"البحث عن منتجات في: {url}")
        
        self.driver.get(url)
        time.sleep(3)
        
        # التمرير لتحميل المنتجات
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
        time.sleep(2)
        
        products = []
        product_selectors = [
            '.product',
            '.woocommerce-LoopProduct-link',
            'li.product',
            '.product-item',
            'article.product',
            '.product-card'
        ]
        
        for selector in product_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    logger.info(f"وجدت {len(elements)} منتج")
                    
                    for element in elements[:30]:
                        try:
                            # الرابط
                            link = None
                            try:
                                link_elem = element.find_element(By.TAG_NAME, 'a')
                                link = link_elem.get_attribute('href')
                            except:
                                link = element.get_attribute('href')
                            
                            if not link or link == url:
                                continue
                            
                            # السعر
                            price_text = None
                            for price_sel in ['.price', '.amount', '.woocommerce-Price-amount', 'bdi']:
                                try:
                                    price_elem = element.find_element(By.CSS_SELECTOR, price_sel)
                                    price_text = price_elem.text.strip()
                                    if price_text and len(price_text) < 50:
                                        break
                                except:
                                    continue
                            
                            if not price_text:
                                continue
                            
                            price = self.extract_price(price_text)
                            
                            if price and price > 0 and price < 10000:
                                # الاسم
                                name = None
                                try:
                                    name_elem = element.find_element(By.CSS_SELECTOR, 'h2, h3, .product-title')
                                    name = name_elem.text.strip()
                                except:
                                    pass
                                
                                products.append({
                                    'name': name or 'Unknown',
                                    'price': price,
                                    'price_text': price_text,
                                    'url': link
                                })
                        except:
                            continue
                    
                    if products:
                        break
            except:
                continue
        
        products.sort(key=lambda x: x['price'])
        return products
    
    def add_to_cart(self, product_url):
        """إضافة للسلة"""
        logger.info(f"إضافة للسلة: {product_url}")
        
        self.driver.get(product_url)
        time.sleep(3)
        
        selectors = [
            'button[name="add-to-cart"]',
            '.single_add_to_cart_button',
            'button.add_to_cart_button',
            '.add-to-cart-button'
        ]
        
        for selector in selectors:
            try:
                button = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
                time.sleep(1)
                button.click()
                logger.info("تم النقر على زر إضافة للسلة")
                time.sleep(3)
                return True
            except:
                continue
        
        # محاولة بديلة
        try:
            button = self.driver.find_element(By.XPATH, 
                "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'add to cart')]"
            )
            button.click()
            time.sleep(3)
            return True
        except:
            return False
    
    def go_to_checkout(self):
        """الانتقال للدفع"""
        logger.info("الانتقال لصفحة الدفع")
        
        time.sleep(2)
        
        # محاولة النقر على روابط checkout
        checkout_texts = ['checkout', 'view cart', 'proceed to checkout']
        for text in checkout_texts:
            try:
                link = self.driver.find_element(By.XPATH, 
                    f"//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{text}')]"
                )
                link.click()
                time.sleep(3)
                break
            except:
                continue
        
        # محاولة الذهاب مباشرة
        current_url = self.driver.current_url
        base_url = '/'.join(current_url.split('/')[:3])
        
        for checkout_path in ['/checkout', '/cart/checkout', '/checkout/']:
            try:
                checkout_url = base_url + checkout_path
                self.driver.get(checkout_url)
                time.sleep(3)
                
                if 'checkout' in self.driver.current_url.lower():
                    return True
            except:
                continue
        
        return 'checkout' in self.driver.current_url.lower()
    
    def fill_billing_details(self):
        """ملء بيانات الفواتير بشكل عشوائي"""
        logger.info("ملء بيانات الفواتير...")
        
        data = generate_random_data()
        
        field_mapping = {
            'billing_first_name': data['first_name'],
            'billing_last_name': data['last_name'],
            'billing_email': data['email'],
            'billing_phone': data['phone'],
            'billing_address_1': data['address'],
            'billing_city': data['city'],
            'billing_postcode': data['postcode'],
        }
        
        filled = 0
        for field_id, value in field_mapping.items():
            try:
                field = None
                for method in [By.ID, By.NAME]:
                    try:
                        field = self.driver.find_element(method, field_id)
                        break
                    except:
                        continue
                
                if field:
                    field.clear()
                    field.send_keys(value)
                    filled += 1
                    time.sleep(0.3)
            except:
                continue
        
        logger.info(f"تم ملء {filled} حقل")
        return filled > 0, data
    
    def get_checkout_info(self):
        """الحصول على معلومات الدفع"""
        logger.info("جمع معلومات الدفع")
        
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
            'Braintree': 'braintree'
        }
        
        for method, keyword in payment_keywords.items():
            if keyword in page_source:
                info['payment_methods'].append(method)
        
        # المبلغ الإجمالي
        for selector in ['.order-total .amount', '.cart-total .amount', 'tr.order-total td']:
            try:
                total_elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                info['total_amount'] = total_elem.text.strip()
                if info['total_amount']:
                    break
            except:
                continue
        
        return info
    
    def process_website(self, url):
        """معالجة الموقع"""
        try:
            self.init_driver()
            
            # 1. البحث عن المنتجات
            products = self.find_products(url)
            if not products:
                return {'success': False, 'error': 'لم يتم العثور على منتجات'}
            
            product = products[0]
            
            # 2. إضافة للسلة
            if not self.add_to_cart(product['url']):
                return {'success': False, 'error': 'فشل في إضافة المنتج للسلة'}
            
            # 3. الانتقال للدفع
            if not self.go_to_checkout():
                return {'success': False, 'error': 'فشل في الوصول لصفحة الدفع'}
            
            # 4. ملء البيانات
            filled, random_data = self.fill_billing_details()
            
            # 5. جمع المعلومات
            checkout_info = self.get_checkout_info()
            
            return {
                'success': True,
                'product': product,
                'checkout_info': checkout_info,
                'filled_data': random_data if filled else None
            }
            
        except Exception as e:
            logger.error(f"خطأ: {e}")
            return {'success': False, 'error': str(e)}
        
        finally:
            self.close_driver()


# معالجات البوت
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج /start"""
    welcome_message = (
        "🤖 مرحباً بك في بوت الوصول لصفحة الدفع!\n\n"
        "✨ ماذا أفعل؟\n"
        "• أبحث عن أرخص منتج في الموقع\n"
        "• أضيفه للسلة تلقائياً\n"
        "• أملأ بيانات الفواتير عشوائياً\n"
        "• أعطيك رابط الدفع الجاهز!\n\n"
        "📝 كيف تستخدمني؟\n"
        "فقط أرسل لي رابط الموقع وسأقوم بالباقي!\n\n"
        "مثال:\n"
        "https://example.com"
    )
    await update.message.reply_text(welcome_message)


async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج الروابط"""
    url = update.message.text.strip()
    
    # التحقق من الرابط
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    # رسالة الانتظار
    waiting_msg = await update.message.reply_text(
        "⏳ جاري التحليل...\n"
        "قد يستغرق هذا 30-60 ثانية..."
    )
    
    # معالجة الموقع
    bot = CheckoutBot()
    result = bot.process_website(url)
    
    if result['success']:
        product = result['product']
        checkout_info = result['checkout_info']
        filled_data = result.get('filled_data')
        
        response = (
            "✅ <b>تم بنجاح!</b>\n\n"
            f"📦 <b>المنتج:</b> {product['name'][:50]}\n"
            f"💰 <b>السعر:</b> {product['price_text']}\n\n"
            f"🔗 <b>رابط الدفع:</b>\n{checkout_info['checkout_url']}\n\n"
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
        
        response += "\n✨ الرابط جاهز! افتحه وأكمل الدفع."
        
        await waiting_msg.edit_text(response, parse_mode='HTML', disable_web_page_preview=True)
    else:
        error_msg = (
            f"❌ <b>فشل التحليل</b>\n\n"
            f"السبب: {result.get('error', 'خطأ غير معروف')}\n\n"
            f"💡 جرب موقعاً آخر أو تأكد من الرابط."
        )
        await waiting_msg.edit_text(error_msg, parse_mode='HTML')


def main():
    """الدالة الرئيسية"""
    # الحصول على التوكن من المتغيرات البيئية
    TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
    
    if not TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN غير موجود!")
        return
    
    # إنشاء التطبيق
    application = Application.builder().token(TOKEN).build()
    
    # المعالجات
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
    
    # تشغيل البوت
    logger.info("البوت يعمل...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()

from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains

from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import time

from hepsiemlak_scraper import url_collect

website_urls = url_collect()

print(website_urls)
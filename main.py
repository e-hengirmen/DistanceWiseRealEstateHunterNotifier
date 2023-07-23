from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains

from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import time
import pandas as pd

from hepsiemlak_scraper import hepsiemlak_scraper


driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
wait = WebDriverWait(driver,10)
actions=ActionChains(driver)


hepsiemlak=hepsiemlak_scraper(driver,wait,actions)
website_urls = hepsiemlak.url_collect()

real_estates=[]
for url in website_urls:
    estate_data = hepsiemlak.data_collect(url)
    real_estates.append(estate_data)
    print(estate_data["title"])
    for key in estate_data:
        if key!="title":
            print("\t"+str(key)+" : "+str(estate_data[key]))

driver.quit()


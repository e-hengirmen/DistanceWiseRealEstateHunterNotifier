from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains

from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC




import time

class hepsiemlak_scraper:
    
    realEstateCSS     = "#listPage > div.list-page-wrapper.with-top-banner > div > div > main > div.list-wrap > div > div.listView > ul > li > article > div.list-view-line > div.list-view-img-wrapper > a.img-link"
    nextPageCSS       = "#listPage > div.list-page-wrapper.with-top-banner > div > div > main > div.list-wrap > div > section > div > a.he-pagination__navigate-text--next"
    
    featureListCSS    = "ul.adv-info-list > li"
    # below 2 wasnt strictly controlled just copy pasted so there might be problems later on
    estateTitleCSS    = "#__layout > div > div > section.wrapper.detail-page > div > div.det-content.cont-block.left > div.cont-inner > section:nth-child(1) > div:nth-child(1) > div.left > h1"
    neighboorhoodCSS  = "#__layout > div > div > section.wrapper.detail-page > div > div.det-content.cont-block.left > div.cont-inner > section:nth-child(1) > div.det-title-bottom > ul > li:nth-child(3)"
    priceCSS          = "p.fz24-text"

    def __init__(self,_driver,_wait,_actions):
        self.driver  = _driver
        self.wait    = _wait
        self.actions = _actions

    def url_collect(self):

        # getting previous url set
        previous_urls=set()
        with open("urlHistory.txt", "r") as urlHistory:
            for url in urlHistory.read().split():
                previous_urls.add(url)

        #################### getting new urls
        website_urls=set()
        
        ###########
        def get_urls_go_next():
            homes               =self.wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR,self.realEstateCSS)))
            pagination_next_page=self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR,self.nextPageCSS)))

            for home in homes:
                current_url=home.get_attribute('href')
                if current_url not in previous_urls:
                    website_urls.add(current_url)
            if("disabled" not in pagination_next_page.get_attribute("class")):
                self.actions.move_to_element(pagination_next_page).click(pagination_next_page).perform()
                return True
            return False
        ###########
        with open("searchURLs.txt", "r") as URLfile:
            for url in URLfile.readlines():
                self.driver.get(url)
                while(True):
                    if(get_urls_go_next()==False):
                        break
        ####################


        file=open("urlHistory.txt", "a", newline='\n') 
        for home in website_urls:
            file.write(home)
            file.write("\n")

        return website_urls

    feature_switch={
            "İlan no":"id",
            "Oda + Salon Sayısı":"room",
            "Brüt / Net M2":"m2",
            "Bulunduğu Kat":"floor",
            "Bina Yaşı":"building age",
            "Aidat":"aidat",

        }
    def translate_feature(self,feature_webelement):
        if feature_webelement.find_element(By.CSS_SELECTOR,"span:first-child").text in self.feature_switch:
            translated_feature_name=self.feature_switch[feature_webelement.find_element(By.CSS_SELECTOR,"span:first-child").text]
            feature_value=feature_webelement.find_element(By.CSS_SELECTOR,"span:nth-child(2)").text
            return translated_feature_name,feature_value
        return None,None

        





    def data_collect(self,url):
        self.driver.get(url)
        context={
            "id":None,
            "url":url,
            "title":None,
            "cost":None,
            "aidat":None,
            "m2":None,
            "room":None,
            "floor":None,
            "building age":None,
            "neighboorhood":None,
            "walk time":None,
            "public transport time":None,
            "car time":None,
            }

        features      = self.wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR,self.featureListCSS)))
        title         = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR,self.estateTitleCSS))).text
        neighboorhood = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR,self.neighboorhoodCSS))).text
        price         = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR,self.priceCSS))).text

        # setting features in the big feature list
        for feature in features:
            f_name,f_val=self.translate_feature(feature)
            if f_name:
                context[f_name]=f_val

        context["title"]         = title
        context["neighboorhood"] = neighboorhood
        context["cost"]         = price         


        return context
    
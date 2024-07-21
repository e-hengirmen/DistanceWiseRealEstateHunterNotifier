import re
import time
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs, urlencode

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options


class hepsiemlak_scraper:

    realEstateCSS = "#listPage > div.list-page-wrapper.with-top-banner > div > div > main > div.list-wrap > div > div.listView > ul > li > article > div.list-view-line > div.list-view-img-wrapper > a.img-link"
    nextPageCSS = "#listPage > div.list-page-wrapper.with-top-banner > div > div > main > div.list-wrap > div > section > div > a.he-pagination__navigate-text--next"

    featureListCSS = "ul.adv-info-list > li"
    # below 2 wasnt strictly controlled just copy pasted so there might be problems later on
    estateTitleCSS = "#__layout > div > div > section.wrapper.detail-page > div > div.det-content.cont-block.left > div.cont-inner > section:nth-child(1) > div:nth-child(1) > div.left > h1"
    neighboorhoodCSS = "#__layout > div > div > section.wrapper.detail-page > div > div.det-content.cont-block.left > div.cont-inner > section:nth-child(1) > div.det-title-bottom > ul > li:nth-child(3)"
    priceCSS = "p.fz24-text"

    info_list_css = 'ul.short-info-list > li'
    button_css = 'button[data-v-7ae19ac8]'

    soup_tag = "section"
    soup_class = "det-block realty-info"
    title_tag = 'h1'
    title_class = 'fontRB'
    price_tag = 'p'
    price_class = 'fz24-text price'
    specs_tag = 'li'
    specs_class = 'spec-item'

    def __init__(self):
        chrome_options = Options()
        chrome_options.add_argument("--start-maximized")

        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        self.wait = WebDriverWait(self.driver, 10)
        self.actions = ActionChains(self.driver)
        self.money_regex = re.compile(r'[^\d,]')

    def create_distance_matrix_url(self, origin, destination, api_key):
        base_url = "https://maps.googleapis.com/maps/api/distancematrix/json?"

        params = {
            "origins": origin,
            "destinations": destination,
            "mode": "transit",
            "key": api_key
        }

        url = base_url + urlencode(params)
        return url

    def scroll_down(self, x):
        self.driver.execute_script(f'window.scrollBy(0, {x});')

    def scrape_real_estate_data(self, url):
        self.driver.get(url)
        info_list = self.wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, self.info_list_css)))
        destination_address = ' '.join([info.text.strip() for info in info_list[:3]])
        self.scroll_down(90)
        buttons = self.wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, self.button_css)))
        maps_button = None
        for button in buttons:
            if "Yol Tarifi" in button.text:
                maps_button = button
                break

        if maps_button:
            # self.driver.execute_script("arguments[0].scrollIntoView(true);", maps_button)
            self.wait.until(EC.element_to_be_clickable(maps_button))
            maps_button.click()
            self.wait.until(lambda d: len(self.driver.window_handles) == 2)
            self.driver.switch_to.window(self.driver.window_handles[1])
            google_maps_url = self.driver.current_url
            parsed_url = urlparse(google_maps_url)
            if 'destination=' in parsed_url.query:
                coordinates = parse_qs(parsed_url.query).get('destination', [None])[0]
            else:
                coordinates = parsed_url.path.strip('/ ').split('/')[3]
            # if coordinates is not None:
            #     coord_x, coord_y = coordinates.split(',')
            self.driver.close()
            self.driver.switch_to.window(self.driver.window_handles[0])
        else:
            pass

        soup = BeautifulSoup(self.driver.page_source, features="lxml").find(self.soup_tag, class_=self.soup_class)
        title = soup.find(self.title_tag, class_=self.title_class).text.strip()
        price = self.money_regex.sub('', soup.find(self.price_tag, class_=self.price_class).text).split(',')[0]
        specs = soup.find_all(self.specs_tag, class_=self.specs_class)
        specs_dict = {}
        for spec in specs:
            spec_tuple = spec.find_all('span')
            if len(spec_tuple) == 1:
                specs_dict[spec_tuple[0].text.strip()] = None
            elif len(spec_tuple) == 2:
                specs_dict[spec_tuple[0].text.strip()] = spec_tuple[1].text.strip()
            elif len(spec_tuple) > 2:
                specs_dict[spec_tuple[0].text.strip()] = "".join([spec_span.text.strip() for spec_span in spec_tuple[1:]])

        return title, price, coordinates, specs_dict

        # Example usage # TODO
        origin_address_list = [
            "METU Department of Computer Engineering",
            "ODTÜ TEKNOKENT MET YERLEŞKESİ, Mustafa Kemal Mah. Dumlupınar Bulvarı No:280 E Blok 2/A, 06510 Çankaya/Ankara",
        ]
        api_key = "YOUR_API_KEY"

        for origin_address in origin_address_list[:1]:
            url = self.create_distance_matrix_url(origin_address, destination_address, api_key)
            print(url)
        return 3






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
    
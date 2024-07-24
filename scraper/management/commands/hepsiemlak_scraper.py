import re
import time
import googlemaps
import os
from random import randint
from datetime import datetime, timedelta
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

from django.core.management.base import BaseCommand
from scraper.models import OriginAdresses, RealEstate, RealEstateOriginDistances
from scraper.utils.messaging_api import send_message

class Command(BaseCommand):

    realEstateArticleCSS = 'article'
    realEstateLinkCSS = 'div.list-view-line > div.list-view-img-wrapper > a.img-link'
    realEstatePriceCSS = 'div.list-view-content > section > div.top > div > span'
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
        self.google_api_keys = os.getenv('google_api_key').split()
        self.google_api_index = randint(0, len(self.google_api_keys) -1)
        
        self.origin_objs = []
        self.origins = []
        for origin in OriginAdresses.objects.all():
            self.origin_objs.append(origin)
            self.origins.append(origin.address)

        departure_time = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0)
        self.departure_time_timestamp = int(departure_time.timestamp())
    
    def get_gkey(self):
        if len(self.google_api_keys) == 0:
            print('No api key remaining')
            return None
        gkey = self.google_api_keys[self.google_api_index]
        self.google_api_index = (self.google_api_index + 1) % len(self.google_api_keys)
        return gkey
    
    def failed_gkey_removal(self):
        previous_index = (self.google_api_index - 1) % len(self.google_api_keys)
        self.google_api_keys.pop(previous_index)
        self.google_api_index = (self.google_api_index - 1) % len(self.google_api_keys)
        
    def get_distances(self, destinations):
        gmaps = googlemaps.Client(key=self.get_gkey())
        ValueError
        # origins = [
        #     'METU Department of Computer Engineering',
        #     'ODTÜ TEKNOKENT MET YERLEŞKESİ, Mustafa Kemal Mah. Dumlupınar Bulvarı No:280 E Blok 2/A, 06510 Çankaya/Ankara',
        # ]
        try:
            result = gmaps.distance_matrix(origins=self.origins, destinations=destinations, mode='transit', departure_time=self.departure_time_timestamp)
        except Exception as e:
            self.failed_gkey_removal()
            return None, None
        duration_lists = []
        for row in result['rows']:
            durations = []
            duration_lists.append(durations)
            for element in row['elements']:
                try:
                    distance = element['distance']['text']
                except:
                    distance = None
                try:
                    duration = element['duration']['value']
                except:
                    duration = None
                durations.append(duration)
        return duration_lists


    def scroll_down(self, x):
        self.driver.execute_script(f'window.scrollBy(0, {x});')

    def scrape_real_estate_data(self, url):
        self.driver.get(url)
        # info_list = self.wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, self.info_list_css)))
        # destination_address = ' '.join([info.text.strip() for info in info_list[:3]])
        self.scroll_down(180)
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
            coordinates = None

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






    def url_collect(self):

        website_urls = []
        
        def get_urls_go_next():
            homes = self.wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR,self.realEstateArticleCSS)))
            pagination_next_page = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR,self.nextPageCSS)))
            real_estates = {
                real_estate.url: real_estate
                for real_estate in RealEstate.objects.all()
            }
            for home in homes:
                try:
                    price_element = home.find_element(By.CSS_SELECTOR, self.realEstatePriceCSS)
                    price = self.money_regex.sub('', price_element.text).split(',')[0]
                except:
                    price = None
                print(price)
                link = home.find_element(By.CSS_SELECTOR, self.realEstateLinkCSS)
                current_url = link.get_attribute('href')
                if url not in real_estates:
                    website_urls.append(current_url)
                else:
                    real_estate = real_estates[url]
                    old_price = real_estate.price
                    if price is not None and old_price != price:
                        real_estate.price = price
                        real_estate.save()
                        if old_price > price:
                            self.send_message_telegram(real_estate)
            if("disabled" not in pagination_next_page.get_attribute("class")):
                self.actions.move_to_element(pagination_next_page).click(pagination_next_page).perform()
                return True
            return False

        with open("searchURLs.txt", "r") as URLfile:
            for url in URLfile.readlines():
                url = url.strip()
                if url.strip():
                    self.driver.get(url)
                    while(True):
                        if(get_urls_go_next()==False):
                            break

        return website_urls

    def send_message_telegram(self,real_estate):
        m_list = [
            real_estate.title,
            str(real_estate.price),
            real_estate.url,
            '',
        ]
        for key,spec in real_estate.specs_dict.items():
            m_list.append(f'{key}: {spec}')
        message = '\n'.join(m_list)
        send_message(message)

    def handle(self, *args, **options):
        website_urls = self.url_collect()
        # old_real_estates = {real_estate.url:real_estate for real_estate in RealEstate.objects.all()}
        print(website_urls)
    
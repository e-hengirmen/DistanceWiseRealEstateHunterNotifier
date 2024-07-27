import re
from time import sleep
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

from django.utils import timezone
from django.core.management.base import BaseCommand
from scraper.models import OriginAdresses, RealEstate, RealEstateOriginDistances, HepsiEmlakScraperLogs
from scraper.utils.messaging_api import send_message
from scraper.utils.request_handler import get_soup, create_link_from_href
import random

def random_sleep():
    sleep(random.uniform(1, 5))

class CaptchaWantedException(Exception):
    pass

class Command(BaseCommand):

    realEstateArticleCSS = 'article'
    realEstateLinkCSS = 'div.list-view-line > div.list-view-img-wrapper > a.img-link'
    realEstatePriceCSS = 'div.list-view-content > section > div.top > div > span'
    nextPageCSS = "a.he-pagination__navigate-text--next"
    nextPageDisabledClass= 'he-pagination__navigate-text--disabled'

    featureListCSS = "ul.adv-info-list > li"
    # below 2 wasnt strictly controlled just copy pasted so there might be problems later on
    estateTitleCSS = "#__layout > div > div > section.wrapper.detail-page > div > div.det-content.cont-block.left > div.cont-inner > section:nth-child(1) > div:nth-child(1) > div.left > h1"
    neighboorhoodCSS = "#__layout > div > div > section.wrapper.detail-page > div > div.det-content.cont-block.left > div.cont-inner > section:nth-child(1) > div.det-title-bottom > ul > li:nth-child(3)"
    priceCSS = "p.fz24-text"

    info_list_css = 'ul.short-info-list > li'
    button_css = 'section > div.det-title-upper.det-title-middle > div.left > ul > li'
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
        
        self.old_real_estates = {
            real_estate.url: real_estate
            for real_estate in RealEstate.objects.all()
        }

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
        if len(self.google_api_keys) == 0:
            raise Exception('No api keys remaining')
        
    def get_distances(self, destinations):
        if not destinations or not self.origins:
            return []
        gmaps = googlemaps.Client(key=self.get_gkey())
        try:
            print(self.origins)
            print(destinations)
            result = gmaps.distance_matrix(origins=self.origins, destinations=destinations, mode='transit', departure_time=self.departure_time_timestamp)
            with open('gmaps_res.txt', 'w') as gmap_file:
                gmap_file.write(str(result))
        except googlemaps.exceptions.ApiError as e:
            print(e)
            try:
                self.failed_gkey_removal()
            except Exception as e:
                print(e)
                print('DURATION ERROR OCCURRED')
                return None
            return self.get_distances(destinations)
        except Exception as e:
            with open('errors.log', 'a') as error_file:
                error_file.write(f'{e}\n\n')

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
        self.counter += 1
        print(f'here {self.counter}/{self.to_be_scraped_count}', flush=True)
        print('after sleep', flush=True)
        try:
            recapthcha=self.wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, '#recaptcha'))) # waits for 5 seconds unless failure solving random sleep
        except:
            recapthcha = None
        if recapthcha:
            raise CaptchaWantedException()
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






    def url_collect_old_selenium(self):

        website_urls = []
        
        def get_urls_go_next():
            homes = self.wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR,self.realEstateArticleCSS)))
            try:
                pagination_next_page = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR,self.nextPageCSS)))
            except:
                pagination_next_page = None
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
                link = home.find_element(By.CSS_SELECTOR, self.realEstateLinkCSS)
                real_estate_url = link.get_attribute('href')
                if real_estate_url not in real_estates:
                    website_urls.append(real_estate_url)
                else:
                    real_estate = real_estates[real_estate_url]
                    old_price = real_estate.price
                    if price is not None and old_price != price:
                        real_estate.price = price
                        real_estate.save()
                        if old_price > price:
                            self.send_message_telegram(real_estate)
            if pagination_next_page and ("disabled" not in pagination_next_page.get_attribute("class")):
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
    
    def url_collect(self):
        website_urls = []
        
        def get_urls_go_next(url):
            soup = get_soup(url, cloudflare=True)
            random_sleep()  # so that we dont get 429
            for listing in soup.find_all(self.realEstateArticleCSS):
                link_href = listing.select_one(self.realEstateLinkCSS)['href']
                real_estate_url = create_link_from_href(url, link_href)
                try:
                    price_element = listing.select_one(self.realEstatePriceCSS)
                    price = self.money_regex.sub('', price_element.text).split(',')[0]
                except:
                    price = None
                if real_estate_url not in self.old_real_estates:
                    website_urls.append(real_estate_url)
                else:
                    real_estate = self.old_real_estates[real_estate_url]
                    old_price = real_estate.price
                    if price is not None and old_price != price:
                        real_estate.price = price
                        real_estate.save()
                        if old_price > price:
                            self.send_message_telegram(real_estate)
            try:
                pagination_next_page_element = soup.select_one(self.nextPageCSS)
                if self.nextPageDisabledClass in pagination_next_page_element.get('class'):
                    pagination_next_page_url = None
                else:
                   pagination_next_page_url = create_link_from_href(url, pagination_next_page_element['href'])
            except:
                pagination_next_page_url = None
            if pagination_next_page_url:
                get_urls_go_next(pagination_next_page_url)

        with open("searchURLs.txt", "r") as URLfile:
            for url in URLfile.readlines():
                url = url.strip()
                if url.strip():
                    get_urls_go_next(url)

        return website_urls
    
    def send_message_telegram(self,real_estate):  # add aditional conditionals here if you want
        send = True
        for distance_obj in RealEstateOriginDistances.objects.filter(destination=real_estate):
            if distance_obj.duration is None:
                send = False
                break
            if 2760 < distance_obj.duration:
                if not (
                    3600 > distance_obj.duration and
                    16500 >= real_estate.price
                ):
                    send = False
                    break
        if send:
            self.send_message_telegram_messager(real_estate)

    def send_message_telegram_messager(self,real_estate):
        distances = " - ".join(['distances:'] + [
            f'{rel.duration // 3600}h {(rel.duration % 3600) // 60}m {rel.duration % 60}s'
            for rel in RealEstateOriginDistances.objects.filter(
                destination=real_estate
            ).order_by('origin_id')
        ])
        m_list = [
            real_estate.title,
            str(real_estate.price),
            real_estate.url,
            '',
            distances,
        ]
        for key,spec in real_estate.specs_dict.items():
            m_list.append(f'{key}: {spec}')
        message = '\n'.join(m_list)
        send_message(message)

    def process(self, *args, **options):
        new_website_urls = self.url_collect()
        self.to_be_scraped_count = len(new_website_urls)
        self.counter = 0
        print('new website count:', len(new_website_urls))
        print()
        real_estate_list = []
        real_estate_with_coord_list = []
        destinations = []
        for url in new_website_urls:
            try:
                title, price, coordinates, specs_dict = self.scrape_real_estate_data(url)
                real_estate = RealEstate(
                    url=url,
                    title=title,
                    price=price,
                    coordinates=coordinates,
                    specs_dict=specs_dict
                )
                real_estate.save()
                if real_estate.coordinates:
                    real_estate_with_coord_list.append(real_estate)
                    destinations.append(real_estate.coordinates)
                real_estate_list.append(real_estate)
            except CaptchaWantedException:
                with open('errors.log', 'a') as error_file:
                    error_file.write(f'Error: Captcha wanted\n\n')
                break
            except Exception as e:
                with open('errors.log', 'a') as error_file:
                    error_file.write(f'{e}\n\n')
        duration_lists = self.get_distances(destinations)
        if duration_lists:
            for origin_obj, duration_list in zip(self.origin_objs, duration_lists):
                for real_estate, duration in zip(real_estate_with_coord_list, duration_list):
                    RealEstateOriginDistances(
                        origin=origin_obj,
                        destination=real_estate,
                        duration=duration,
                    ).save()
        for real_estate in real_estate_list:
            self.send_message_telegram(real_estate)

    def handle(self, *args, **options):
        start_time = timezone.now()
        self.process(*args, **options)
        end_time = timezone.now()
        HepsiEmlakScraperLogs(
            duration=end_time-start_time,
            realestate_count=self.counter,
            relation_count=3,
        ).save()

        
        

                            
    
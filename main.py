from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains

from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC




import time




start = time.time()
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
wait = WebDriverWait(driver,10)
actions=ActionChains(driver)


# getting previous url set
previous_urls=set()
with open("urlHistory.txt", "r") as urlHistory:
    for url in urlHistory.read().split():
        previous_urls.add(url)

#################### getting new urls
website_urls=set()
realEstateCSS="#listPage > div.list-page-wrapper.with-top-banner > div > div > main > div.list-wrap > div > div.listView > ul > li > article > div.list-view-line > div.list-view-img-wrapper > a.img-link"
nextPageCSS  ="#listPage > div.list-page-wrapper.with-top-banner > div > div > main > div.list-wrap > div > section > div > a.he-pagination__navigate-text--next"
###########
def get_urls_go_next():
    homes               =wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR,realEstateCSS)))
    pagination_next_page=wait.until(EC.presence_of_element_located((By.CSS_SELECTOR,nextPageCSS)))

    for home in homes:
        current_url=home.get_attribute('href')
        if current_url not in previous_urls:
            website_urls.add(current_url)
    if("disabled" not in pagination_next_page.get_attribute("class")):
        actions.move_to_element(pagination_next_page).click(pagination_next_page).perform()
        return True
    return False
###########
with open("searchURLs.txt", "r") as URLfile:
    for url in URLfile.readlines():
        driver.get(url)
        while(True):
            if(get_urls_go_next()==False):
                break
####################


file=open("urlHistory.txt", "a") 
for home in website_urls:
    file.write(home)
    file.write("\n")

print(website_urls)
print(previous_urls)

driver.quit()
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time


def load_products(driver):
    print("Looking to load more products")

    # Clear cookie consent message first
    cookies_box = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "onetrust-reject-all-handler"))
    )
    if cookies_box:
        cookies_box.click()
    while True:
        try:
            more_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".pager__item a.button"))
            )
            print(more_button) if more_button else print("I dont see anything")
            ActionChains(driver).move_to_element(more_button).perform()
            more_button.click()

            WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".coh-row-visible-xl")))
            time.sleep(2)
        except Exception as e:
            print(f"No more 'More' button found or all products loaded: {str(e)}")
            break

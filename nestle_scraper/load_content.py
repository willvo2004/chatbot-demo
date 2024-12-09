from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def load_products(driver):
    while True:
        try:
            more_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".pager__item a.button"))
            )
            ActionChains(driver).move_to_element(more_button).perform()
            more_button.click()

            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".views-field-title"))
            )
        except Exception:
            print("No more 'More' button found or all products loaded.")
            break

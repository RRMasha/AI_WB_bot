from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time


def get_product_link(search_query):

    driver = None
    try:
        # Настройка браузера
        options = webdriver.ChromeOptions()
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--window-size=1200,800")

        # Фоновый режим
        # options.add_argument("--headless")

        driver = webdriver.Chrome(options=options)

        # Открываем главную страницу
        driver.get("https://www.wildberries.ru")
        time.sleep(3)

        # Поиск поисковой строки
        search_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input#searchInput.search-catalog__input")))

        # Очистка и ввод запроса
        search_input.clear()
        for char in search_query:
            search_input.send_keys(char)
            time.sleep(0.1)

        # Нажимаем кнопку поиска
        search_button = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button#applySearchBtn.search-catalog__btn--search")))
        search_button.click()
        time.sleep(2)

        # Ожидаем загрузки результатов
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "article.product-card.j-card-item")))

        # Получаем ссылку на первый товар
        first_product = driver.find_element(
            By.CSS_SELECTOR, "article.product-card.j-card-item")
        product_link = first_product.find_element(
            By.CSS_SELECTOR, "a.product-card__link.j-card-link").get_attribute("href")

        # Очищаем ссылку от параметров
        clean_link = product_link.split('?')[0]

        return clean_link

    except Exception as e:
        print(f"Ошибка при поиске товара: {e}")
        return "Ошибка"

    finally:
        if driver:
            driver.quit()

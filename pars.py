from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from datetime import datetime
import os
import pandas as pd


# Глобальная переменная для драйвера
# driver = None
# Глобальные переменные для хранения состояния авторизации
# auth_in_progress = False
# current_phone = None


user_drivers = {}
user_auth_states = {}

""" Для для глобального драйвера
def init_driver():
    global driver
    if driver is None:
        options = webdriver.ChromeOptions()
        options.add_argument("--start-maximized")
        options.add_argument("--disable-blink-features=AutomationControlled")
        driver = webdriver.Chrome(options=options)
    return driver
"""


def cleanup_user(user_id):
    if user_id in user_drivers:
        try:
            user_drivers[user_id].quit()
        except:
            pass
        del user_drivers[user_id]
    if user_id in user_auth_states:
        del user_auth_states[user_id]


def init_driver(user_id):
    if user_id not in user_drivers or user_drivers[user_id] is None:
        options = webdriver.ChromeOptions()
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--window-size=1200,800")
        user_drivers[user_id] = webdriver.Chrome(options=options)

        # Важные настройки таймаутов
        user_drivers[user_id].set_page_load_timeout(30)
        user_drivers[user_id].implicitly_wait(5)
    return user_drivers[user_id]


def save_to_csv(purchases, user_id):
    try:
        os.makedirs('data/user_data', exist_ok=True)
        if not purchases:
            return None

        csv_path = f"data/user_data/{user_id}.csv"

        if os.path.exists(csv_path):
            os.remove(csv_path)

        pd.DataFrame(purchases).to_csv(
            csv_path,
            index=False,
            encoding='utf-8-sig'
        )
        return csv_path
    except Exception as e:
        print(f"Ошибка при сохранении CSV: {e}")
        return None


def open_browser():
    global driver
    try:
        init_driver()
        driver.get("https://www.wildberries.ru/lk/myorders/archive")
        print("Браузер открыт, пожалуйста авторизуйтесь")
        return True
    except Exception as e:
        print(f"Ошибка при открытии браузера: {e}")
        return False


##########################################################
def start_phone_auth(user_id, phone):
    """Начинает процесс авторизации по номеру телефона"""
    # global driver, auth_in_progress, current_phone

    try:
        #
        driver = init_driver(user_id)
        user_auth_states[user_id] = {'phone': phone, 'status': 'started'}
        #
        if driver is None:
            init_driver()

        # Переходим на страницу входа
        driver.get("https://www.wildberries.ru/lk")
        time.sleep(3)

        # Находим поле для ввода телефона
        phone_input = WebDriverWait(driver, 3).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input.input-item[type='text'")))

        # Вводим номер телефона
        phone_input.clear()
        for char in phone:
            phone_input.send_keys(char)
            time.sleep(0.1)

        # Нажимаем кнопку "Получить код"
        get_code_btn = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button#requestCode"))
        )
        get_code_btn.click()

        auth_in_progress = True
        current_phone = phone
        return True

    except Exception as e:
        print(f"Ошибка при начале авторизации: {e}")
        return False


def complete_phone_auth(user_id: int, phone: str, code: str) -> bool:
    """Завершает авторизацию с кодом подтверждения"""
    global driver, auth_in_progress, current_phone

    try:
        if user_id not in user_auth_states:
            return False

        driver = init_driver(user_id)

        ''' Для глобального
        if not auth_in_progress or phone != current_phone:
            return False
        '''
        # Находим поле для ввода кода (6 цифр)
        code_inputs = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, "input.char-input__item"))
        )

        if len(code_inputs) != 6:
            raise Exception("Не найдены все 6 полей для ввода кода")

        # Вводим код посимвольно
        for i, digit in enumerate(code):
            code_inputs[i].send_keys(digit)
            time.sleep(0.1)

        # Ждем авторизации (перенаправления на страницу профиля)
        time.sleep(5)

        if "lk" in driver.current_url:
            user_auth_states[user_id]['status'] = 'completed'
            # Сохраняем драйвер для последующего использования
            user_auth_states[user_id]['driver'] = driver
            return True
        return False
        '''
        # Проверяем, что авторизация прошла успешно
        if "lk" in driver.current_url:
            auth_in_progress = False
            current_phone = None
            return True
        else:
            return False
        '''
    except Exception as e:
        print(f"Ошибка при завершении авторизации: {e}")
        return False
##########################################################


def pars_data(user_id):
    # global driver
    """ Для глобал
    if driver is None:
        raise Exception(
            "Браузер не инициализирован. Сначала вызовите open_browser() и авторизуйтесь")
    """
    try:
        # Проверяем, что пользователь авторизован
        if user_id not in user_auth_states or user_auth_states[user_id].get('status') != 'completed':
            raise Exception(
                "Требуется авторизация. Сначала выполните вход в аккаунт.")

        driver = init_driver(user_id)
        # Проверяем, что мы на нужной странице
        if "myorders/archive" not in driver.current_url:
            driver.get("https://www.wildberries.ru/lk/myorders/archive")
            time.sleep(3)

        '''
        # Даем время на авторизацию
        time.sleep(15)
        driver.refresh()  # Обновляем страницу после авторизации
        time.sleep(5)
        '''

        # Скроллим страницу до конца
        print("Скроллим страницу...")
        last_height = driver.execute_script(
            "return document.body.scrollHeight")
        while True:
            driver.execute_script(
                "window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            new_height = driver.execute_script(
                "return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

        # Собираем все заказы
        orders = driver.find_elements(By.CLASS_NAME, "archive-item")
        if not orders:
            raise Exception(
                "Не найдено заказов. Возможно, вы не авторизовались")

        order_data = []
        last_valid_date = datetime.now().strftime("%d-%m-%Y")

        for order in orders:
            try:
                # Название товара
                full_name = order.find_element(
                    By.CLASS_NAME, "archive-item__brand").text
                name = full_name.split('/')[-1].strip()

                # Цена
                price = order.find_element(
                    By.CLASS_NAME, "archive-item__price").text
                price = price.replace('₽', '').replace(' ', '').strip()

                # Дата покупки
                try:
                    date_element = order.find_element(
                        By.XPATH, ".//div[@class='archive-item__hidden-block']//p[contains(@class, 'archive-item__receive-date')]//span[last()]"
                    )
                    date = date_element.text.strip()
                    last_valid_date = date
                except:
                    try:
                        status = order.find_element(
                            By.XPATH, ".//p[@class='archive-item__status']").text
                        if "Возврат" in status or "Отмена" in status:
                            date = last_valid_date if last_valid_date else "Дата неизвестна"
                        else:
                            date = "Дата неизвестна"
                    except:
                        date = last_valid_date if last_valid_date else "Дата неизвестна"

                # Обработка даты
                try:
                    if "Дата неизвестна" in date:
                        formatted_date = date
                    else:
                        date_parts = date.split()
                        day = date_parts[0]
                        month_ru = date_parts[1].lower()
                        months = {
                            'января': '01', 'февраля': '02', 'марта': '03',
                            'апреля': '04', 'мая': '05', 'июня': '06',
                            'июля': '07', 'августа': '08', 'сентября': '09',
                            'октября': '10', 'ноября': '11', 'декабря': '12'
                        }
                        year = datetime.now().year
                        if len(date_parts) == 3:
                            year = date_parts[2]
                        formatted_date = f"{day.zfill(2)}-{months.get(month_ru, '00')}-{year}"
                        last_valid_date = formatted_date
                except Exception as e:
                    formatted_date = date

                date = formatted_date

                # Категории товара (основная и дополнительная)
                main_category = "нет категории"
                sub_category = "нет категории"

                try:
                    # 1. Открываем мини-карточку товара
                    product_link = order.find_element(
                        By.CLASS_NAME, "j-open-product-popup")
                    ActionChains(driver).move_to_element(
                        product_link).click().perform()
                    time.sleep(1)

                    # 2. Открываем полную карточку товара
                    WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".product__header.j-product-title")))

                    title_link = driver.find_element(
                        By.CSS_SELECTOR, ".product__header.j-product-title")
                    driver.execute_script("arguments[0].click();", title_link)
                    time.sleep(2)

                    # 3. Собираем хлебные крошки (категории)
                    breadcrumbs = driver.find_elements(
                        By.XPATH, "//ul[contains(@class, 'breadcrumbs__list')]/li[position()>1]//span")

                    if len(breadcrumbs) >= 1:
                        main_category = breadcrumbs[0].text
                    if len(breadcrumbs) >= 2:
                        sub_category = breadcrumbs[1].text

                    # 4. Возвращаемся назад
                    driver.back()
                    time.sleep(1)
                except Exception as e:
                    print(f"Ошибка при сборе категорий: {e}")

                # Сохраняем данные о товаре
                order_data.append(
                    [name, price, date, main_category, sub_category])
                print(
                    f"Товар: {name} | Цена: {price} | Дата: {date} | Категория: {main_category} | Подкатегория: {sub_category}")

            except Exception as e:
                print(f"Ошибка при парсинге заказа: {e}")
                continue

        if not order_data:
            raise Exception("Не удалось собрать данные ни по одному заказу")

        # Формируем итоговые данные
        purchases = [
            {
                "Дата получения": item[2],
                "Категория": item[3],          # Основная категория
                "Доп. категория": item[4],     # Дополнительная категория
                "Товар": item[0],
                "Цена": int(item[1]) if str(item[1]).isdigit() else 0
            }
            for item in order_data
        ]

        return save_to_csv(purchases, user_id)

    except Exception as e:
        print(f"Ошибка в pars_data: {e}")
        raise
    finally:
        cleanup_user(user_id)  # Очищаем только этого пользователя

    """ Для глобального драйвера
    finally:
        if driver:
            driver.quit()
            global auth_in_progress, current_phone
            auth_in_progress = False
            current_phone = None
"""

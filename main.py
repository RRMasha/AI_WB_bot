import json
import os
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.client.default import DefaultBotProperties
from recommendations import RecommendationEngine
import asyncio
import pars
from product_search import get_product_link
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup


####################
class AuthStates(StatesGroup):
    waiting_for_phone = State()
    waiting_for_code = State()
######################


# Инициализация бота
bot = Bot(token="8027678125:AAGJUE9QJW8KNYUkl_8BDWah9ngJr9zVkmQ",
          default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

# Клавиатура с основными действиями

###############################################################


@dp.message(lambda message: message.text == "🔄 Собрать данные")
async def handle_parse(message: types.Message, state: FSMContext):
    await message.answer(
        "Чтобы создать рекомендации, нам нужно получить доступ к вашим покупкам на Wildberries.\n\n"
        "1. Введите ваш номер телефона, привязанный к Wildberries (в формате 79991234567)\n"
        "2. Вам придет SMS с кодом подтверждения - введите его в бот\n"
        "3. После успешной авторизации нажмите /pars для сбора данных\n\n"
        "❗️Бот не хранит ваши данные и собирает историю покупок только для обучения."
    )
    await state.set_state(AuthStates.waiting_for_phone)

# Обработчик ввода номера телефона


@dp.message(AuthStates.waiting_for_phone)
async def process_phone(message: types.Message, state: FSMContext):
    phone = message.text.strip()
    if not phone.isdigit() or len(phone) != 11:
        await message.answer("❌ Неверный формат номера. Введите 11 цифр без пробелов и других символов (например: 79991234567)")
        return

    try:
        await state.update_data(phone=phone)
        await message.answer(f"🔑 Номер {phone} принят. Теперь введите код подтверждения из SMS:")
        await state.set_state(AuthStates.waiting_for_code)

        # Здесь можно сразу начать процесс авторизации в фоновом режиме
        asyncio.create_task(start_wb_auth(message.from_user.id, phone))
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")
        await state.clear()

# Обработчик ввода кода подтверждения


@dp.message(AuthStates.waiting_for_code)
async def process_code(message: types.Message, state: FSMContext):
    code = message.text.strip()
    if not code.isdigit() or len(code) != 6:
        await message.answer("❌ Код должен состоять из 6 цифр. Попробуйте еще раз:")
        return

    try:
        user_data = await state.get_data()
        phone = user_data.get('phone')
        user_id = message.from_user.id

        # Сохраняем код для использования в парсере
        await state.update_data(auth_code=code)

        # Уведомляем пользователя
        await message.answer(
            "✅ Код принят! Идет авторизация на Wildberries...\n\n"
            "Как только авторизация завершится, вы получите уведомление. "
            "После этого нажмите /pars для сбора данных о ваших покупках."
        )

        # Запускаем процесс авторизации
        asyncio.create_task(complete_wb_auth(user_id, phone, code))

    except Exception as e:
        await message.answer(f"❌ Ошибка при обработке кода: {str(e)}")
    finally:
        await state.clear()


async def start_wb_auth(user_id: int, phone: str):
    """Запускает процесс авторизации на Wildberries"""
    try:
        # Здесь вызываем функцию из pars.py для начала авторизации
        # success = pars.start_phone_auth(phone) Для глобального драйвера
        success = pars.start_phone_auth(user_id, phone)
        if not success:
            await bot.send_message(user_id, "❌ Не удалось начать процесс авторизации. Попробуйте еще раз.")
    except Exception as e:
        await bot.send_message(user_id, f"❌ Ошибка при авторизации: {str(e)}")


async def complete_wb_auth(user_id: int, phone: str, code: str):
    """Завершает процесс авторизации на Wildberries с кодом подтверждения"""
    try:
        success = pars.complete_phone_auth(user_id, phone, code)
        # success = pars.complete_phone_auth(phone, code)
        if success:
            await bot.send_message(user_id, "✅ Авторизация прошла успешно! Теперь вы можете нажать /pars для сбора данных.")
        else:
            await bot.send_message(user_id, "❌ Неверный код подтверждения или истек срок действия. Попробуйте снова.")
    except Exception as e:
        await bot.send_message(user_id, f"❌ Ошибка при подтверждении кода: {str(e)}")

######################################################################


def get_main_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.add(types.KeyboardButton(text="🔄 Собрать данные"))
    builder.add(types.KeyboardButton(text="🌟 Получить рекомендации"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)


# Команда /start


@dp.message(Command("start"))
async def start_command(message: types.Message):
    await message.answer(
        "👋 <b>Привет!</b>\n\n"
        "Этот бот создан для умных рекомендаций на маркетплейсе Wildberries. "
        "Он анализирует твои покупки и создает уникальную модель, которая становится твоим личным помощником.\n\n"
        "Это только первая версия бота, и некоторые функции работают медленно. Прояви терпения и дождись ответных сообщений, они точно придут.\n\n"
        "Для каждого пользователя, который совершил больше 50 покупок на Wildberries, доступно создание уникальной модели, которая рекомендует товары на основе только ваших предпочтений. Если у тебя еще не набралось 50 покупок — не расстраивайся, тебе тоже доступны умные рекомендации от глобальной модели.\n"
        "Совершайте покупки, обновляйте сбор данных, так модель всегда будет знать, что вам сегодня рекомендовать.\n\n"
        "Для начала работы нажми кнопку «Собрать данные».\n\n"
        "🚀 <b>Начни прямо сейчас!</b>",
        reply_markup=get_main_keyboard()
    )

# Обработчик кнопки "Собрать данные" Без номера телефона

"""
@dp.message(lambda message: message.text == "🔄 Собрать данные")
async def handle_parse(message: types.Message):
    await message.answer(
        "Чтобы создать рекомендации для вас нам нужно посмотреть покупки которые вы уже совершали.\n\n"
        "1. Нажмите /open - на вашем устройстве откроется Wildberries\n"
        "2. Войдите в свой аккаунт\n"
        "3. Вернитесь в бот и нажмите /pars\n\n"
        "Изучение ваших покупок может занять некоторое время, не закрывайте браузер.\n"
        "После успешного завершения вы получите уведомление."
    )
    
"""

# Команда /open - открывает Wildberries


@dp.message(Command("open"))
async def open_wildberries(message: types.Message):
    try:
        if pars.open_browser():
            await message.answer(
                "🌐 Браузер открыт. Пожалуйста:\n"
                "1. Войдите в свой аккаунт Wildberries\n"
                "2. Дождитесь полной загрузки страницы\n"
                "3. Затем нажмите /pars в боте"
            )
        else:
            await message.answer("❌ Не удалось открыть браузер")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")


@dp.message(Command("pars"))
async def parse_user_data(message: types.Message):
    user_id = message.from_user.id
    await message.answer("🔍 Начинаю анализ ваших покупок... Это может занять несколько минут.")

    try:
        csv_path = pars.pars_data(user_id)
        if csv_path:
            await message.answer(
                "✅ Данные успешно собраны!\n"
                "Теперь вы можете получить рекомендации, нажав кнопку '🌟 Получить рекомендации'."
            )
        else:
            await message.answer("❌ Не удалось собрать данные. Попробуйте еще раз.")
    except Exception as e:
        error_msg = (
            "❌ Произошла ошибка при сборе данных:\n"
            f"{str(e)}\n\n"
            "Попробуйте:\n"
            "1. Убедиться, что вы авторизовались\n"
            "2. Проверить, есть ли заказы в архиве\n"
            "3. Попробовать снова через 2-3 минуты"
        )
        await message.answer(error_msg)

# Обработчик кнопки "Получить рекомендации"


@dp.message(lambda message: message.text == "🌟 Получить рекомендации")
async def handle_recommendations(message: types.Message):
    user_id = message.from_user.id
    csv_path = f"data/user_data/{user_id}.csv"

    if not os.path.exists(csv_path):
        await message.answer("❌ Файл с данными не найден. Сначала соберите данные.")
        return

    try:
        # Инициализация и получение рекомендаций
        engine = RecommendationEngine()
        result = engine.get_recommendations(str(user_id))

        if result['status'] == 'error':
            await message.answer(f"❌ Ошибка: {result['message']}")
            return

        # 1. Отправляем первые два сообщения в неизменном виде
        model_type_message = (
            f"🔮 <b>Сейчас для рекомендаций используется:</b> {result['model_type']} модель\n\n"
            f"📅 Дата рекомендаций: {result['date']}"
        )
        await message.answer(model_type_message, parse_mode="HTML")

        categories = [rec['category'] for rec in result['recommendations']]
        categories_message = (
            "🛍️ <b>Сегодня рекомендуем вам товары из категорий:</b>\n"
            f"• {categories[0]}\n"
            f"• {categories[1]}"
        )
        await message.answer(categories_message, parse_mode="HTML")

        # 2. Сообщение о подборе товаров
        await message.answer("🔎 <b>Подбираем для вас товары...</b>", parse_mode="HTML")

        # 3. Получаем и отправляем товары по рекомендациям по одному
        all_subcategories = []
        for rec in result['recommendations']:
            for sub in rec['subcategories']:
                all_subcategories.append((rec['category'], sub['name']))

        for i, (category, subcategory) in enumerate(all_subcategories[:6], 1):
            # Формируем поисковый запрос
            search_query = f"{category} {subcategory}"

            # Ищем товар
            product_link = get_product_link(search_query)

            # Отправляем результат сразу
            if product_link and product_link != "Ошибка":
                await message.answer(
                    f"<b>{category}, {subcategory}</b>\n"
                    f"<a href='{product_link}'>Смотреть товар</a>",
                    parse_mode="HTML",
                    disable_web_page_preview=False
                )
            else:
                await message.answer(
                    f"<b>{category}, {subcategory}</b>\n"
                    "Не удалось найти товар",
                    parse_mode="HTML"
                )

            # Небольшая пауза между запросами
            await asyncio.sleep(1)

        # 4. Финальное сообщение
        await message.answer(
            "🎉 <b>На сегодня это все рекомендации!</b>\n\n"
            "Ваш личный помощник советует обратить внимание на эти товары. "
            "Если вам нужны дополнительные рекомендации, просто запросите их снова позже.",
            parse_mode="HTML"
        )

    except Exception as e:
        await message.answer(f"⚠️ Ошибка: {str(e)}")

# Запуск бота


async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

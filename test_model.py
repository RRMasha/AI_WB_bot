import joblib
import json
from datetime import datetime
import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder


def load_global_model():
    """Загрузка модели и кодировщиков"""
    model = joblib.load("data/models/global_model.pkl")
    with open("data/models/global_encoders.json", 'r') as f:
        encoders = json.load(f)
    return model, encoders


def get_top_categories(model, X, encoders, top_n=2):
    """Получение топ-N категорий с вероятностями"""
    probas = model['category'].predict_proba(X)[0]
    top_indices = np.argsort(probas)[-top_n:][::-1]
    return [(encoders['category'][i], f"{probas[i]:.2f}") for i in top_indices]


def get_top_subcategories(model, X_combined, encoders, top_n=3):
    """Получение топ-N подкатегорий с вероятностями"""
    probas = model['subcategory'].predict_proba(X_combined)[0]
    top_indices = np.argsort(probas)[-top_n:][::-1]
    return [(encoders['subcategory'][i], f"{probas[i]:.2f}") for i in top_indices]


def predict_for_date(input_date, top_categories=2, top_subcategories=3):
    """Предсказание с топ-N категориями и подкатегориями"""
    try:
        model, encoders = load_global_model()

        # Подготовка даты
        date_obj = datetime.strptime(input_date, "%d-%m-%Y")
        X = pd.DataFrame([{
            'День недели_номер': date_obj.weekday(),
            'Сезон_код': get_season(date_obj.month),
            'Праздник_код': int(date_obj.strftime('%d-%m') in holidays)
        }])[['День недели_номер', 'Сезон_код', 'Праздник_код']]

        # Получаем топ-2 категории
        top_cats = get_top_categories(model, X, encoders, top_categories)

        recommendations = []
        for cat, cat_prob in top_cats:
            # Подготовка комбинированных признаков
            cat_code = encoders['category'].index(cat)
            category_encoded = model['category_encoder'].transform([
                                                                   [cat_code]])
            X_combined = np.hstack([X.values, category_encoded])

            # Получаем топ-3 подкатегории для категории
            top_subs = get_top_subcategories(
                model, X_combined, encoders, top_subcategories)
            recommendations.append((cat, cat_prob, top_subs))

        return recommendations

    except Exception as e:
        print(f"Ошибка: {str(e)}")
        return []

# Вспомогательные функции


def get_season(month):
    if month in [12, 1, 2]:
        return 0
    elif month in [3, 4, 5]:
        return 1
    elif month in [6, 7, 8]:
        return 2
    else:
        return 3


holidays = ['01-01', '07-01', '23-02', '08-03',
            '01-05', '09-05', '12-06', '04-11']

if __name__ == "__main__":
    test_date = "15-05-2024"

    recommendations = predict_for_date(
        test_date, top_categories=2, top_subcategories=3)

    if recommendations:
        print(f"\nРекомендации на {test_date}:")
        for i, (cat, cat_prob, subcats) in enumerate(recommendations, 1):
            print(f"\n{i}. Основная категория: {cat} (вероятность: {cat_prob})")
            print("   Топ-3 подкатегории:")
            for j, (subcat, subcat_prob) in enumerate(subcats, 1):
                print(f"   {j}. {subcat} (вероятность: {subcat_prob})")
    else:
        print("Не удалось получить рекомендации.")

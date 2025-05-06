from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder, OneHotEncoder
import pandas as pd
import joblib
import json
import os
import numpy as np


def get_season(month):
    """Определение сезона по месяцу"""
    if month in [12, 1, 2]:
        return 0
    elif month in [3, 4, 5]:
        return 1
    elif month in [6, 7, 8]:
        return 2
    else:
        return 3


def prepare_subcategory_features(X, y_category, category_encoder=None, fit=False):
    """
    Подготовка комбинированных признаков для подкатегорий
    fit=True - для обучения кодировщика
    """
    if fit:
        category_encoded = category_encoder.fit_transform(
            y_category.values.reshape(-1, 1))
    else:
        category_encoded = category_encoder.transform(
            y_category.values.reshape(-1, 1))
    return np.hstack([X.values, category_encoded])


def train_global_model():
    """Основная функция обучения глобальной модели"""
    # 1. Загрузка и фильтрация данных
    try:
        data = pd.read_csv("for_lern_model.csv")
        data = data[(data['Категория'] != 'нет категории') &
                    (data['Доп. категория'] != 'нет категории')]

        if len(data) == 0:
            raise ValueError(
                "Нет данных для обучения после фильтрации 'нет категории'")
    except Exception as e:
        print(f"Ошибка загрузки данных: {e}")
        return

    # 2. Подготовка признаков
    data['Дата получения'] = pd.to_datetime(
        data['Дата получения'], format='%d-%m-%Y', errors='coerce')
    data = data.dropna(subset=['Дата получения'])

    data['День недели_номер'] = data['Дата получения'].dt.weekday
    data['Месяц'] = data['Дата получения'].dt.month
    data['Сезон_код'] = data['Месяц'].apply(get_season)

    holidays = ['01-01', '07-01', '23-02', '08-03',
                '01-05', '09-05', '12-06', '04-11']
    data['Праздник_код'] = data['Дата получения'].dt.strftime(
        '%d-%m').isin(holidays).astype(int)

    # 3. Кодирование категорий
    le_category = LabelEncoder()
    le_subcategory = LabelEncoder()
    data['Категория_код'] = le_category.fit_transform(data['Категория'])
    data['Доп.категория_код'] = le_subcategory.fit_transform(
        data['Доп. категория'])

    # 4. Разделение данных
    X = data[['День недели_номер', 'Сезон_код', 'Праздник_код']]
    y_category = data['Категория_код']
    # 
    y_subcategory = data['Доп.категория_код']

    X_train, X_test, y_train, y_test = train_test_split(
        X, y_category, test_size=0.3, random_state=42
    )
    _, _, y_train_sub, y_test_sub = train_test_split(
        X, y_subcategory, test_size=0.3, random_state=42
    )

    # 5. Обучение модели категорий
    params = {
        'bootstrap': True,
        'criterion': 'entropy',
        'max_depth': None,
        'max_features': 'sqrt',
        'min_samples_leaf': 1,
        'min_samples_split': 2,
        'n_estimators': 20
    }

    category_model = RandomForestClassifier(**params)
    category_model.fit(X_train, y_train)

    # 6. Подготовка данных для подкатегорий (каскад)
    category_encoder = OneHotEncoder(sparse_output=False)

    # ОБЯЗАТЕЛЬНО передаем fit=True для обучения кодировщика
    X_train_combined = prepare_subcategory_features(
        X_train, y_train, category_encoder, fit=True  
    )
    X_test_combined = prepare_subcategory_features(
        X_test, y_test, category_encoder, fit=False
    )

    # 7. Обучение модели подкатегорий
    subcategory_model = RandomForestClassifier(**params)
    subcategory_model.fit(X_train_combined, y_train_sub)

    # 8. Проверка точности
    '''
    print("\n=== Результаты обучения ===")
    print("Категории:")
    print(
        f"Train: {accuracy_score(y_train, category_model.predict(X_train)):.3f}")
    print(f"Test: {accuracy_score(y_test, category_model.predict(X_test)):.3f}")

    print("\nПодкатегории (каскад):")
    print(
        f"Train: {accuracy_score(y_train_sub, subcategory_model.predict(X_train_combined)):.3f}")
    print(
        f"Test: {accuracy_score(y_test_sub, subcategory_model.predict(X_test_combined)):.3f}")
    '''
    # 9. Сохранение моделей
    os.makedirs("data/models", exist_ok=True)

    joblib.dump({
        'category': category_model,
        'subcategory': subcategory_model,
        'category_encoder': category_encoder
    }, "data/models/global_model.pkl")

    with open("data/models/global_encoders.json", 'w') as f:
        json.dump({
            'category': list(le_category.classes_),
            'subcategory': list(le_subcategory.classes_)
        }, f)

    print("\nМодель успешно сохранена в data/models/")


if __name__ == "__main__":
    train_global_model()

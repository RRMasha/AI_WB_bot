import os
import pandas as pd
import joblib
import json
import numpy as np
from datetime import datetime
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder, OneHotEncoder


class RecommendationEngine:
    def __init__(self):
        self.global_model_path = "data/models/global_model.pkl"
        self.global_encoders_path = "data/models/global_encoders.json"
        self.user_models_dir = "data/models/user_models"
        self.user_data_dir = "data/user_data"

        os.makedirs(self.user_models_dir, exist_ok=True)
        os.makedirs(self.user_data_dir, exist_ok=True)

    def get_recommendations(self, user_id):
        """Основной метод для получения рекомендаций"""
        try:
            # Загрузка или создание модели
            model, encoders, model_type = self._load_user_model(user_id)

            # Текущая дата для рекомендаций
            current_date = datetime.now().strftime("%d-%m-%Y")
 ##########################
            # current_date = "10-05-2025"

            # Формирование рекомендаций
            return self._generate_recommendations(model, encoders, current_date, model_type)

        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }

    def _load_user_model(self, user_id):
        """Загружает или создает модель для пользователя"""
        user_csv = f"{self.user_data_dir}/{user_id}.csv"

        if not os.path.exists(user_csv):
            raise FileNotFoundError("Файл с данными пользователя не найден")

        num_purchases = len(pd.read_csv(user_csv))
        user_model_path = f"{self.user_models_dir}/{user_id}.pkl"
        user_encoders_path = f"{self.user_models_dir}/{user_id}_encoders.json"

        # Всегда возвращаем tuple из 3 элементов
        if num_purchases > 50 and os.path.exists(user_model_path):
            model = joblib.load(user_model_path)
            with open(user_encoders_path, 'r') as f:
                encoders = json.load(f)
            return model, encoders, "Персональная модель"

        elif num_purchases > 50:
            model, encoders = self._train_personal_model(user_id)
            return model, encoders, "Персональная модель (новая)"

        else:
            model = joblib.load(self.global_model_path)
            with open(self.global_encoders_path, 'r') as f:
                encoders = json.load(f)
            return model, encoders, "Глобальная модель"

    def _train_personal_model(self, user_id):
        """Обучает персональную модель"""
        data = pd.read_csv(f"{self.user_data_dir}/{user_id}.csv")
        data = data[(data['Категория'] != 'нет категории') &
                    (data['Доп. категория'] != 'нет категории')]

        # Подготовка данных
        data['Дата получения'] = pd.to_datetime(
            data['Дата получения'], format='%d-%m-%Y')
        data['День недели_номер'] = data['Дата получения'].dt.weekday
        data['Месяц'] = data['Дата получения'].dt.month
        data['Сезон_код'] = data['Месяц'].apply(self._get_season)
        data['Праздник_код'] = data['Дата получения'].dt.strftime(
            '%d-%m').isin(self._get_holidays()).astype(int)

        # Кодирование
        le_category = LabelEncoder()
        le_subcategory = LabelEncoder()
        data['Категория_код'] = le_category.fit_transform(data['Категория'])
        data['Доп.категория_код'] = le_subcategory.fit_transform(
            data['Доп. категория'])

        # Обучение моделей
        X = data[['День недели_номер', 'Сезон_код', 'Праздник_код']]
        y_category = data['Категория_код']
        y_subcategory = data['Доп.категория_код']

        params = {
            'bootstrap': True,
            'criterion': 'entropy',
            'max_depth': None,
            'max_features': 'sqrt',
            'min_samples_leaf': 1,
            'min_samples_split': 2,
            'n_estimators': 20
        }

        # Модель категорий
        category_model = RandomForestClassifier(**params)
        category_model.fit(X, y_category)

        # Модель подкатегорий
        category_encoder = OneHotEncoder(sparse_output=False)
        X_combined = np.hstack(
            [X.values, category_encoder.fit_transform(y_category.values.reshape(-1, 1))])
        subcategory_model = RandomForestClassifier(**params)
        subcategory_model.fit(X_combined, y_subcategory)

        # Сохранение
        model_data = {
            'category': category_model,
            'subcategory': subcategory_model,
            'category_encoder': category_encoder
        }

        joblib.dump(model_data, f"{self.user_models_dir}/{user_id}.pkl")

        with open(f"{self.user_models_dir}/{user_id}_encoders.json", 'w') as f:
            json.dump({
                'category': list(le_category.classes_),
                'subcategory': list(le_subcategory.classes_)
            }, f)

        return model_data, {
            'category': le_category.classes_,
            'subcategory': le_subcategory.classes_
        }

    def _generate_recommendations(self, model, encoders, date, model_type):
        """Генерирует рекомендации для указанной даты"""
        date_obj = datetime.strptime(date, "%d-%m-%Y")
        X = pd.DataFrame([{
            'День недели_номер': date_obj.weekday(),
            'Сезон_код': self._get_season(date_obj.month),
            'Праздник_код': int(date_obj.strftime('%d-%m') in self._get_holidays())
        }])[['День недели_номер', 'Сезон_код', 'Праздник_код']]

        # Топ-2 категории
        cat_probas = model['category'].predict_proba(X)[0]
        top_cats = [
            (encoders['category'][i], prob)
            for i, prob in sorted(enumerate(cat_probas), key=lambda x: x[1], reverse=True)[:2]
        ]

        recommendations = []
        for cat, cat_prob in top_cats:
            try:
                # Преобразуем категории в numpy массив для безопасного поиска
                categories_array = np.array(encoders['category'])

                # Находим индекс категории с проверкой
                matches = np.where(categories_array == cat)[0]
                if len(matches) == 0:
                    continue  # Пропускаем не найденные категории

                cat_code = matches[0]  # Берем первый совпадающий индекс

                # Подготовка данных для подкатегорий
                X_combined = np.hstack([
                    X.values,
                    model['category_encoder'].transform([[cat_code]])
                ])

                # Топ-3 подкатегории
                subcat_probas = model['subcategory'].predict_proba(X_combined)[
                    0]
                top_subcats = [
                    (encoders['subcategory'][i], prob)
                    for i, prob in sorted(enumerate(subcat_probas), key=lambda x: x[1], reverse=True)[:3]
                ]

                recommendations.append({
                    'category': cat,
                    'category_prob': float(cat_prob),
                    'subcategories': [
                        {'name': subcat, 'probability': float(prob)}
                        for subcat, prob in top_subcats
                    ]
                })
            except Exception as e:
                print(f"Ошибка при обработке категории {cat}: {str(e)}")
                continue

            '''
            # Топ-3 подкатегории
            # Находим индекс категории через np.where
            cat_code = np.where(encoders['category'] == cat)[0][0]
            X_combined = np.hstack([
                X.values,
                model['category_encoder'].transform([[cat_code]])
            ])

            subcat_probas = model['subcategory'].predict_proba(X_combined)[0]
            top_subcats = [
                (encoders['subcategory'][i], prob)
                for i, prob in sorted(enumerate(subcat_probas), key=lambda x: x[1], reverse=True)[:3]
            ]

            recommendations.append({
                'category': cat,
                'category_prob': float(cat_prob),
                'subcategories': [
                    {'name': subcat, 'probability': float(prob)}
                    for subcat, prob in top_subcats
                ]
            })

            '''

        return {
            'status': 'success',
            'model_type': model_type,
            'date': date,
            'recommendations': recommendations
        }

    @staticmethod
    def _get_season(month):
        if month in [12, 1, 2]:
            return 0
        elif month in [3, 4, 5]:
            return 1
        elif month in [6, 7, 8]:
            return 2
        else:
            return 3

    @staticmethod
    def _get_holidays():
        return ['01-01', '07-01', '23-02', '08-03',
                '01-05', '09-05', '12-06', '04-11']

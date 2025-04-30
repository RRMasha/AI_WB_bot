from recommendations import RecommendationEngine


def test_recommendation_for_user():
    engine = RecommendationEngine()

    user_id = "1871715831"

    print("\n" + "="*50)
    print(f"Запуск теста для пользователя: {user_id}")

    try:
        result = engine.get_recommendations(user_id)

        if result['status'] == 'error':
            print(f"\nОшибка: {result['message']}")
            return

        print(f"\nТип модели: {result['model_type']}")
        print(f"Дата рекомендаций: {result['date']}")

        print("\nРекомендации:")
        for rec in result['recommendations']:
            print(
                f"\n▪ Категория: {rec['category']} (вероятность: {float(rec['category_prob'])*100:.1f}%)")
            for sub in rec['subcategories']:
                print(
                    f"  ▸ {sub['name']} (вероятность: {float(sub['probability'])*100:.1f}%)")

    except Exception as e:
        print(f"\nКритическая ошибка: {str(e)}")


if __name__ == "__main__":
    test_recommendation_for_user()

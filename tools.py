def calculate_bmi(weight: float, height: int):
    """
    Рассчитывает индекс массы тела (ИМТ) и возвращает значение ИМТ и его категорию.
    :param weight: Вес в кг
    :param height: Рост в см
    :return: Кортеж (значение_имт, категория_имт)
    """
    if height == 0:
        return 0, "N/A"

    height_m = height / 100
    bmi = round(weight / (height_m ** 2), 1)

    if bmi < 18.5:
        category = "Недостаточный вес"
    elif 18.5 <= bmi < 25:
        category = "Нормальный вес"
    elif 25 <= bmi < 30:
        category = "Избыточный вес"
    else:
        category = "Ожирение"

    return bmi, category


def calculate_calories(gender: str, weight: float, height: int, age: int, activity_level: str):
    """
    Рассчитывает суточную норму калорий по формуле Миффлина-Сан Жеора.
    :return: Словарь с потребностями в калориях для разных целей.
    """
    if gender == "Мужской":
        bmr = (10 * weight) + (6.25 * height) - (5 * age) + 5
    else:
        bmr = (10 * weight) + (6.25 * height) - (5 * age) - 161

    activity_multipliers = {
        "Минимальная": 1.2,
        "Легкая": 1.375,
        "Средняя": 1.55,
        "Высокая": 1.725
    }
    multiplier = activity_multipliers.get(activity_level, 1.2)

    maintenance_calories = bmr * multiplier

    return {
        "Сброс веса": int(maintenance_calories * 0.85),
        "Поддержание": int(maintenance_calories),
        "Набор массы": int(maintenance_calories * 1.15)
    }
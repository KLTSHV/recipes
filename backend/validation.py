"""Строгая серверная валидация: bool не считается числом, лишние поля запрещены."""

from .errors import APIError

TEXT_FIELDS = {
    "title": ("Название", 1, 200),
    "ingredients": ("Ингредиенты", 1, 4000),
    "instructions": ("Шаги приготовления", 1, 10000),
    "category": ("Категория", 0, 50),
}
NUMBER_FIELDS = {
    "prep_time": ("Время приготовления", 1, 1440),
    "servings": ("Количество порций", 1, 50),
}
REQUIRED_FIELDS = ("title", "ingredients", "instructions", "prep_time", "servings")
ALLOWED_FIELDS = set(TEXT_FIELDS) | set(NUMBER_FIELDS) | {"is_favorite"}
DEFAULTS = {"category": "", "is_favorite": False}


def validate_recipe(payload: object, *, partial: bool = False) -> dict:
    if not isinstance(payload, dict):
        raise APIError(400, "Validation failed", ["Тело запроса должно быть JSON-объектом"])
    details = []
    result = {} if partial else DEFAULTS.copy()
    unknown = sorted(set(payload) - ALLOWED_FIELDS)
    if unknown:
        details.append("Неизвестные или недоступные для записи поля: " + ", ".join(unknown))
    if partial and not payload:
        details.append("Передайте хотя бы одно поле для изменения")
    if not partial:
        for field in REQUIRED_FIELDS:
            if field not in payload:
                details.append(f"Поле {field} обязательно для заполнения")
    for field, value in payload.items():
        if field in TEXT_FIELDS:
            label, minimum, maximum = TEXT_FIELDS[field]
            if not isinstance(value, str):
                details.append(f"{label}: ожидается строка")
                continue
            value = value.strip()
            try:
                value.encode("utf-8")
            except UnicodeEncodeError:
                details.append(f"{label}: строка содержит некорректные Unicode-символы")
                continue
            if "\x00" in value:
                details.append(f"{label}: нулевые символы недопустимы")
            elif not minimum <= len(value) <= maximum:
                details.append(f"{label}: длина должна быть от {minimum} до {maximum} символов")
            else:
                result[field] = value
        elif field in NUMBER_FIELDS:
            label, minimum, maximum = NUMBER_FIELDS[field]
            if type(value) is not int or not minimum <= value <= maximum:
                details.append(f"{label}: требуется целое число от {minimum} до {maximum}")
            else:
                result[field] = value
        elif field == "is_favorite":
            if type(value) is not bool:
                details.append("Избранное: требуется логическое значение true или false")
            else:
                result[field] = value
    if details:
        raise APIError(400, "Validation failed", details)
    return result

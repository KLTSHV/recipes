"""Необязательные демонстрационные записи; заполненная база не изменяется."""

from .database import Database
from .repository import RecipeRepository
from .validation import validate_recipe

DEMO_RECIPES = [
    {"title": "Сырники с ягодами", "ingredients": "Творог — 400 г\nЯйцо — 1 шт.\nМука — 3 ст. л.\nСахар — 2 ст. л.\nЯгоды — для подачи", "instructions": "Смешайте творог, яйцо, сахар и муку.\nСформируйте небольшие сырники.\nОбжарьте на среднем огне по 3–4 минуты с каждой стороны.\nПодавайте с ягодами.", "prep_time": 25, "servings": 2, "category": "Завтраки", "is_favorite": True},
    {"title": "Паста с томатами и базиликом", "ingredients": "Паста — 200 г\nТоматы — 350 г\nЧеснок — 2 зубчика\nОливковое масло — 2 ст. л.\nБазилик — небольшой пучок", "instructions": "Отварите пасту в подсоленной воде.\nПрогрейте чеснок в масле, добавьте нарезанные томаты.\nТушите соус 10 минут.\nСоедините с пастой и добавьте базилик.", "prep_time": 20, "servings": 2, "category": "Основные блюда", "is_favorite": False},
    {"title": "Тыквенный суп", "ingredients": "Тыква — 600 г\nЛук — 1 шт.\nОвощной бульон — 700 мл\nСливки — 100 мл\nТыквенные семечки — для подачи", "instructions": "Обжарьте нарезанный лук.\nДобавьте кубики тыквы и бульон.\nВарите около 20 минут, пока тыква не станет мягкой.\nИзмельчите блендером, влейте сливки и прогрейте.\nПосыпьте семечками перед подачей.", "prep_time": 35, "servings": 4, "category": "Супы", "is_favorite": True},
    {"title": "Салат с нутом", "ingredients": "Готовый нут — 250 г\nОгурец — 1 шт.\nПомидоры — 2 шт.\nПетрушка — 1 пучок\nЛимонный сок — 1 ст. л.\nОливковое масло — 2 ст. л.", "instructions": "Нарежьте овощи и зелень.\nДобавьте нут.\nСмешайте лимонный сок с маслом и щепоткой соли.\nЗаправьте салат и перемешайте.", "prep_time": 15, "servings": 2, "category": "Салаты", "is_favorite": False},
    {"title": "Яблочный крамбл", "ingredients": "Яблоки — 4 шт.\nМука — 150 г\nСливочное масло — 100 г\nСахар — 80 г\nКорица — 1 ч. л.", "instructions": "Разогрейте духовку до 180 °C.\nНарежьте яблоки и уложите в форму, посыпьте корицей.\nРазотрите муку, масло и сахар в крошку.\nРаспределите крошку по яблокам.\nВыпекайте 30–35 минут до золотистой корочки.", "prep_time": 45, "servings": 4, "category": "Десерты", "is_favorite": False},
    {"title": "Лимонад с мятой", "ingredients": "Лимоны — 2 шт.\nВода — 1 л\nСахар — 3 ст. л.\nМята — 5 веточек\nЛёд — для подачи", "instructions": "Выжмите сок лимонов.\nРастворите сахар в небольшом количестве тёплой воды.\nСмешайте сок, сироп и оставшуюся воду.\nДобавьте мяту и лёд.", "prep_time": 10, "servings": 4, "category": "Напитки", "is_favorite": False},
]


def seed_database(database: Database) -> bool:
    database.migrate()
    repository = RecipeRepository(database)
    if repository.list_all():
        return False
    # Весь набор добавляется одной транзакцией: при ошибке не останется половина набора.
    with database.connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        if connection.execute("SELECT 1 FROM recipes LIMIT 1").fetchone():
            return False
        for payload in DEMO_RECIPES:
            data = validate_recipe(payload)
            columns = tuple(data)
            connection.execute(
                f"INSERT INTO recipes ({', '.join(columns)}) VALUES ({', '.join('?' for _ in columns)})",
                tuple(data.values()),
            )
    return True


if __name__ == "__main__":
    from .config import Settings

    seeded = seed_database(Database(Settings.from_env().database_path))
    print("Демонстрационные рецепты добавлены" if seeded else "База уже содержит рецепты: без изменений")

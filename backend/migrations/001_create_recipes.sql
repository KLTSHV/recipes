CREATE TABLE recipes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL CHECK (length(trim(title)) BETWEEN 1 AND 200),
    ingredients TEXT NOT NULL CHECK (length(trim(ingredients)) BETWEEN 1 AND 4000),
    instructions TEXT NOT NULL CHECK (length(trim(instructions)) BETWEEN 1 AND 10000),
    prep_time INTEGER NOT NULL CHECK (typeof(prep_time) = 'integer' AND prep_time BETWEEN 1 AND 1440),
    servings INTEGER NOT NULL CHECK (typeof(servings) = 'integer' AND servings BETWEEN 1 AND 50),
    category TEXT NOT NULL DEFAULT '' CHECK (length(category) <= 50),
    is_favorite INTEGER NOT NULL DEFAULT 0 CHECK (is_favorite IN (0, 1))
);

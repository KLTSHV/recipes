// Пользовательский текст вставляется через textContent: HTML в рецепте остаётся текстом.
export function node(tag, className = "", text = "") {
  const element = document.createElement(tag);
  if (className) element.className = className;
  element.textContent = text;
  return element;
}

function action(label, actionName, id, className, title = label) {
  const button = node("button", className, label);
  button.type = "button";
  button.dataset.action = actionName;
  button.dataset.id = id;
  button.title = title;
  return button;
}

export function recipeCard(recipe) {
  const card = node("article", "recipe-card");
  const top = node("div", "card-top");
  top.append(node("span", "category", recipe.category || "Без категории"));
  const favorite = action(recipe.is_favorite ? "★" : "☆", "favorite", recipe.id, "favorite-button", recipe.is_favorite ? `Убрать «${recipe.title}» из избранного` : `Добавить «${recipe.title}» в избранное`);
  favorite.setAttribute("aria-label", favorite.title);
  favorite.setAttribute("aria-pressed", String(recipe.is_favorite));
  top.append(favorite);
  const title = node("h2", "card-title", recipe.title);
  const meta = node("div", "card-meta");
  meta.append(node("span", "", `◷ ${recipe.prep_time} мин`), node("span", "", `${recipe.servings} порц.`), node("span", "recipe-id", `№ ${recipe.id}`));
  const ingredients = node("div", "card-preview");
  ingredients.append(node("h3", "", "Ингредиенты"), node("p", "clamp-text", recipe.ingredients));
  const instructions = node("div", "card-preview");
  instructions.append(node("h3", "", "Приготовление"), node("p", "clamp-text", recipe.instructions));
  const controls = node("div", "card-actions");
  controls.append(
    action("Открыть", "view", recipe.id, "button button-small button-secondary"),
    action("Изменить", "edit", recipe.id, "button button-small button-plain"),
    action("Удалить", "delete", recipe.id, "button button-small button-danger"),
  );
  card.append(top, title, meta, ingredients, instructions, controls);
  return card;
}

export function errorContent(container, error) {
  container.replaceChildren();
  const messages = error.details?.length ? error.details : [error.message || "Не удалось выполнить запрос"];
  container.append(node("strong", "", "Не удалось выполнить действие"));
  const list = node("ul");
  for (const message of messages) list.append(node("li", "", message));
  container.append(list);
  container.hidden = false;
}

export function renderDetails(container, recipe) {
  container.replaceChildren();
  const meta = node("div", "detail-meta");
  meta.append(
    node("span", "category", recipe.category || "Без категории"),
    node("span", "", `${recipe.prep_time} минут`),
    node("span", "", `${recipe.servings} порц.`),
    node("span", "", recipe.is_favorite ? "★ В избранном" : "☆ Не в избранном"),
    node("span", "recipe-id", `Рецепт № ${recipe.id}`),
  );
  const ingredients = node("section", "detail-section");
  ingredients.append(node("h3", "", "Ингредиенты"), node("p", "preserve-lines", recipe.ingredients));
  const instructions = node("section", "detail-section");
  instructions.append(node("h3", "", "Шаги приготовления"), node("p", "preserve-lines", recipe.instructions));
  container.append(meta, ingredients, instructions);
}

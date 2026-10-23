import { api } from "./api.js";
import { node, recipeCard, errorContent, renderDetails } from "./render.js";

const $ = id => document.getElementById(id);
const state = { recipes: [], busy: false, favoritesOnly: false, editingId: null, detailId: null, deletingId: null, loaded: false };
const form = $("recipe-form");
const fields = ["title", "ingredients", "instructions", "prep_time", "servings", "category"];

function setBusy(value, text = "Загрузка…") {
  state.busy = value;
  $("loading").hidden = !value;
  $("loading-text").textContent = text;
  $("recipes").setAttribute("aria-busy", String(value));
  for (const element of document.querySelectorAll("[data-action], [data-close], #new-recipe, #empty-add, #refresh, #details-edit, #confirm-delete, #recipe-form input, #recipe-form textarea, #recipe-form button")) {
    element.disabled = value;
  }
  $("save-recipe").textContent = value && $("editor").open ? "Сохранение…" : "Сохранить рецепт";
  $("confirm-delete").textContent = value && $("delete-dialog").open ? "Удаление…" : "Удалить";
}

function notify(message) {
  $("notice").className = "notice";
  $("notice").replaceChildren(node("span", "", message));
  $("notice").hidden = false;
}

function showError(error, target = $("notice")) {
  target.className = "notice notice-error";
  errorContent(target, error);
}

function render() {
  const query = $("search").value.trim().toLocaleLowerCase("ru");
  const category = $("category-filter").value;
  const visible = state.recipes.filter(recipe =>
    (!state.favoritesOnly || recipe.is_favorite) &&
    (!category || recipe.category === category) &&
    (!query || `${recipe.title} ${recipe.ingredients} ${recipe.category}`.toLocaleLowerCase("ru").includes(query))
  );
  $("recipes").replaceChildren(...visible.map(recipeCard));
  $("recipe-count").textContent = state.loaded ? `Рецептов: ${visible.length} из ${state.recipes.length}` : "Коллекция пока не загружена";
  $("empty-state").hidden = visible.length > 0 || !state.loaded;
  const filtered = Boolean(query || category || state.favoritesOnly);
  $("empty-title").textContent = filtered ? "Рецепты не найдены" : "Здесь начинается ваша книга рецептов";
  $("empty-description").textContent = filtered ? "Попробуйте другой поиск или измените фильтры." : "Добавьте первое блюдо, которое хочется приготовить снова.";
  $("empty-add").hidden = filtered;
  $("reset-filters").hidden = !filtered;
  $("filter-all").classList.toggle("active", !state.favoritesOnly);
  $("filter-favorites").classList.toggle("active", state.favoritesOnly);
  $("filter-all").setAttribute("aria-pressed", String(!state.favoritesOnly));
  $("filter-favorites").setAttribute("aria-pressed", String(state.favoritesOnly));
  // Перерисовка при вводе поиска не должна включать кнопки во время запроса.
  if (state.busy) for (const button of $("recipes").querySelectorAll("button")) button.disabled = true;
}

async function fetchRecipes() {
  state.recipes = await api.list();
  state.loaded = true;
  const current = $("category-filter").value;
  const categories = [...new Set(state.recipes.map(recipe => recipe.category).filter(Boolean))].sort((a, b) => a.localeCompare(b, "ru"));
  $("category-filter").replaceChildren(node("option", "", "Все категории"));
  $("category-filter").firstElementChild.value = "";
  for (const category of categories) {
    const option = node("option", "", category);
    option.value = category;
    $("category-filter").append(option);
  }
  $("category-filter").value = categories.includes(current) ? current : "";
  render();
}

async function runTask(task, text = "Загрузка…", target = $("notice")) {
  if (state.busy) return;
  target.hidden = true;
  setBusy(true, text);
  try {
    await task();
  } catch (error) {
    showError(error, target);
  } finally {
    setBusy(false);
  }
}

async function refreshAfterMutation(message) {
  try {
    await fetchRecipes();
    notify(message);
  } catch (error) {
    showError({ message: error.message, details: [message, "Список не удалось обновить. Нажмите «Обновить».", ...(error.details?.length ? error.details : [error.message])] });
  }
}

function openEditor(recipe = null) {
  state.editingId = recipe?.id ?? null;
  form.reset();
  for (const field of fields) {
    $(field).value = recipe ? recipe[field] : ({ prep_time: 30, servings: 2 }[field] ?? "");
    $(field).setCustomValidity("");
  }
  $("is_favorite").checked = recipe?.is_favorite ?? false;
  $("editor-title").textContent = recipe ? "Редактировать рецепт" : "Новый рецепт";
  $("form-error").hidden = true;
  $("editor").showModal();
  // При GET перед редактированием поля включатся в finally текущего запроса.
  setTimeout(() => { if ($("editor").open) $("title").focus(); }, 0);
}

function resetFilters() {
  $("search").value = "";
  $("category-filter").value = "";
  state.favoritesOnly = false;
  render();
}

for (const id of ["new-recipe", "empty-add"]) {
  $(id).addEventListener("click", () => { if (!state.busy) openEditor(); });
}
$("refresh").addEventListener("click", () => runTask(fetchRecipes));
$("search").addEventListener("input", render);
$("category-filter").addEventListener("change", render);
$("reset-filters").addEventListener("click", resetFilters);
$("filter-all").addEventListener("click", () => { state.favoritesOnly = false; render(); });
$("filter-favorites").addEventListener("click", () => { state.favoritesOnly = true; render(); });

document.addEventListener("click", event => {
  const closeButton = event.target.closest("[data-close]");
  if (closeButton && !state.busy) $(closeButton.dataset.close).close();
});
for (const dialog of document.querySelectorAll("dialog")) {
  dialog.addEventListener("cancel", event => { if (state.busy) event.preventDefault(); });
}
for (const input of form.querySelectorAll("input, textarea")) {
  input.addEventListener("input", () => input.setCustomValidity(""));
}

form.addEventListener("submit", event => {
  event.preventDefault();
  if (state.busy) return;
  for (const name of ["title", "ingredients", "instructions"]) {
    if (!$(name).value.trim()) $(name).setCustomValidity("Заполните поле: одних пробелов недостаточно");
  }
  if (!form.reportValidity()) return;
  const payload = {
    title: $("title").value.trim(), ingredients: $("ingredients").value.trim(), instructions: $("instructions").value.trim(),
    prep_time: Number($("prep_time").value), servings: Number($("servings").value),
    category: $("category").value.trim(), is_favorite: $("is_favorite").checked,
  };
  const editing = state.editingId !== null;
  runTask(async () => {
    if (editing) await api.replace(state.editingId, payload);
    else await api.create(payload);
    $("editor").close();
    await refreshAfterMutation(editing ? "Изменения сохранены." : "Рецепт добавлен в коллекцию.");
  }, "Сохранение…", $("form-error"));
});

$("recipes").addEventListener("click", event => {
  const button = event.target.closest("button[data-action]");
  if (!button || state.busy) return;
  const id = Number(button.dataset.id);
  const recipe = state.recipes.find(item => item.id === id);
  if (!recipe) return;
  if (button.dataset.action === "favorite") {
    runTask(async () => {
      const updated = await api.patch(id, { is_favorite: !recipe.is_favorite });
      await refreshAfterMutation(updated.is_favorite ? "Рецепт добавлен в избранное." : "Рецепт убран из избранного.");
    }, "Сохранение…");
  } else if (button.dataset.action === "edit") {
    runTask(async () => openEditor(await api.get(id)));
  } else if (button.dataset.action === "view") {
    runTask(async () => {
      const fresh = await api.get(id);
      state.detailId = id;
      $("details-title").textContent = fresh.title;
      renderDetails($("details-content"), fresh);
      $("details").showModal();
    });
  } else if (button.dataset.action === "delete") {
    state.deletingId = id;
    $("delete-description").textContent = `«${recipe.title}» будет удалён из вашей коллекции. Это действие нельзя отменить.`;
    $("delete-error").hidden = true;
    $("delete-dialog").showModal();
    $("cancel-delete").focus();
  }
});

$("details-edit").addEventListener("click", () => {
  if (state.busy) return;
  const id = state.detailId;
  $("details").close();
  runTask(async () => openEditor(await api.get(id)));
});

$("confirm-delete").addEventListener("click", () => runTask(async () => {
  await api.remove(state.deletingId);
  $("delete-dialog").close();
  state.deletingId = null;
  await refreshAfterMutation("Рецепт удалён.");
}, "Удаление…", $("delete-error")));

runTask(fetchRecipes);

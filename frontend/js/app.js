"use strict";

const API_URL = "/api/tasks";
const STATUS_LABELS = {
  pending: "Pending",
  in_progress: "In progress",
  completed: "Completed",
};

const elements = {
  rows: document.querySelector("#task-rows"),
  search: document.querySelector("#search-input"),
  filter: document.querySelector("#status-filter"),
  feedback: document.querySelector("#feedback"),
  resultCount: document.querySelector("#result-count"),
  pageSize: document.querySelector("#page-size"),
  pageStatus: document.querySelector("#page-status"),
  prevPage: document.querySelector("#prev-page"),
  nextPage: document.querySelector("#next-page"),
  dialog: document.querySelector("#task-dialog"),
  form: document.querySelector("#task-form"),
  deleteDialog: document.querySelector("#delete-dialog"),
};

const state = {
  tasks: [], editingId: null, deletingId: null,
  page: 1, pageSize: Number(elements.pageSize.value), total: 0, pages: 0,
  requestId: 0, searchTimer: null,
};

async function apiRequest(path = "", options = {}) {
  const response = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (response.status === 204) return null;
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const details = payload.details
      ? Object.values(payload.details).flat().join(" ")
      : payload.message || payload.error || "The request could not be completed.";
    const error = new Error(details);
    error.status = response.status;
    throw error;
  }
  return payload;
}

function showFeedback(message, kind = "success") {
  elements.feedback.textContent = message;
  elements.feedback.className = `feedback feedback-${kind}`;
  elements.feedback.hidden = false;
}

function hideFeedback() {
  elements.feedback.hidden = true;
  elements.feedback.textContent = "";
}

function formatDate(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Date unavailable";
  return new Intl.DateTimeFormat("en-GB", {
    day: "2-digit", month: "short", year: "numeric",
    hour: "2-digit", minute: "2-digit", hour12: false,
  }).format(date);
}

function isOverdue(task) {
  return task.status !== "completed" && new Date(task.due_at).getTime() < Date.now();
}

function makeElement(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}

function createStatusSelect(task) {
  const select = document.createElement("select");
  select.className = "inline-status";
  select.setAttribute("aria-label", `Update status for ${task.title}`);
  Object.entries(STATUS_LABELS).forEach(([value, label]) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = label;
    option.selected = task.status === value;
    select.append(option);
  });
  select.addEventListener("change", async () => {
    select.disabled = true;
    try {
      await apiRequest(`/${task.id}/status`, {
        method: "PATCH", body: JSON.stringify({ status: select.value }),
      });
      showFeedback(`Status updated: ${task.title}`);
      await refreshTasks();
    } catch (error) {
      showFeedback(error.message, "error");
      select.value = task.status;
    } finally {
      select.disabled = false;
    }
  });
  return select;
}

function renderTask(task) {
  const row = document.createElement("tr");
  const taskCell = document.createElement("td");
  const title = makeElement("div", "task-title", task.title);
  const description = makeElement("div", "task-description", task.description || "No description provided");
  taskCell.append(title, description);

  const statusCell = document.createElement("td");
  statusCell.append(createStatusSelect(task));

  const dueCell = document.createElement("td");
  const due = makeElement("div", `due-date${isOverdue(task) ? " overdue" : ""}`, formatDate(task.due_at));
  dueCell.append(due);
  if (isOverdue(task)) dueCell.append(makeElement("span", "overdue-label", "Overdue"));

  const actionsCell = makeElement("td", "row-actions");
  const editButton = makeElement("button", "text-action", "Edit");
  editButton.type = "button";
  editButton.addEventListener("click", () => openEditDialog(task));
  const deleteButton = makeElement("button", "text-action text-action-danger", "Delete");
  deleteButton.type = "button";
  deleteButton.addEventListener("click", () => openDeleteDialog(task.id));
  actionsCell.append(editButton, deleteButton);
  row.append(taskCell, statusCell, dueCell, actionsCell);
  return row;
}

function hasActiveFilters() {
  return Boolean(elements.search.value.trim()) || elements.filter.value !== "all";
}

function renderTasks() {
  elements.rows.replaceChildren();
  if (!state.tasks.length) {
    const filtered = hasActiveFilters();
    const row = document.createElement("tr");
    const cell = makeElement("td", "empty-state");
    cell.colSpan = 4;
    const heading = makeElement("strong", "", filtered ? "No matching tasks" : "Your task list is clear");
    const copy = makeElement("p", "", filtered ? "Try a different search or status filter." : "Create a task to start organising your workload.");
    cell.append(heading, copy);
    row.append(cell);
    elements.rows.append(row);
  } else {
    state.tasks.forEach((task) => elements.rows.append(renderTask(task)));
  }
  renderPagination();
}

function renderPagination() {
  const offset = (state.page - 1) * state.pageSize;
  elements.resultCount.textContent = state.total
    ? `Showing ${offset + 1}–${offset + state.tasks.length} of ${state.total} task${state.total === 1 ? "" : "s"}`
    : "No tasks to show";
  elements.pageStatus.textContent = `Page ${state.page} of ${Math.max(state.pages, 1)}`;
  elements.prevPage.disabled = state.page <= 1;
  elements.nextPage.disabled = state.page >= state.pages;
}

async function loadTasks() {
  const requestId = ++state.requestId;
  elements.prevPage.disabled = true;
  elements.nextPage.disabled = true;
  elements.rows.replaceChildren();
  const row = document.createElement("tr");
  const cell = makeElement("td", "loading-cell", "Loading tasks…");
  cell.colSpan = 4;
  row.append(cell);
  elements.rows.append(row);
  const params = new URLSearchParams({ page: state.page, page_size: state.pageSize });
  const search = elements.search.value.trim();
  if (search) params.set("search", search);
  if (elements.filter.value !== "all") params.set("status", elements.filter.value);
  try {
    const payload = await apiRequest(`?${params}`);
    // Ignore responses that were overtaken by a newer page, search or filter request.
    if (requestId !== state.requestId) return;
    // The current page can disappear after a delete or status change; fall back to the last page.
    if (!payload.items.length && payload.total && state.page > payload.pages) {
      state.page = payload.pages;
      await loadTasks();
      return;
    }
    state.tasks = payload.items;
    state.total = payload.total;
    state.pages = payload.pages;
    renderTasks();
  } catch (error) {
    if (requestId !== state.requestId) return;
    elements.rows.replaceChildren();
    const errorRow = document.createElement("tr");
    const errorCell = makeElement("td", "empty-state", `Unable to load tasks. ${error.message}`);
    errorCell.colSpan = 4;
    errorRow.append(errorCell);
    elements.rows.append(errorRow);
    elements.resultCount.textContent = "Tasks unavailable";
    showFeedback("Could not connect to the task service. Please try again.", "error");
  }
}

async function loadSummary() {
  const counts = { "#count-all": "total", "#count-pending": "pending", "#count-progress": "in_progress", "#count-completed": "completed" };
  let summary = null;
  try {
    summary = await apiRequest("/summary");
  } catch {
    // loadTasks reports connection problems; show placeholders rather than stale counts.
  }
  Object.entries(counts).forEach(([selector, key]) => {
    document.querySelector(selector).textContent = summary ? summary[key] : "—";
  });
}

function refreshTasks() {
  return Promise.all([loadTasks(), loadSummary()]);
}

function goToPage(page) {
  state.page = page;
  loadTasks();
}

function toLocalInputValue(value) {
  const date = value ? new Date(value) : new Date(Date.now() + 60 * 60 * 1000);
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 16);
}

function openCreateDialog() {
  state.editingId = null;
  elements.form.reset();
  document.querySelector("#dialog-eyebrow").textContent = "CREATE TASK";
  document.querySelector("#dialog-title").textContent = "Add a task";
  document.querySelector("#save-task").textContent = "Save task";
  document.querySelector("#task-due").value = toLocalInputValue();
  clearFormErrors();
  elements.dialog.showModal();
  document.querySelector("#task-title").focus();
}

function openEditDialog(task) {
  state.editingId = task.id;
  elements.form.reset();
  document.querySelector("#dialog-eyebrow").textContent = "EDIT TASK";
  document.querySelector("#dialog-title").textContent = "Update task";
  document.querySelector("#save-task").textContent = "Save changes";
  document.querySelector("#task-title").value = task.title;
  document.querySelector("#task-description").value = task.description || "";
  document.querySelector("#task-status").value = task.status;
  document.querySelector("#task-due").value = toLocalInputValue(task.due_at);
  clearFormErrors();
  elements.dialog.showModal();
  document.querySelector("#task-title").focus();
}

function clearFormErrors() {
  document.querySelector("#title-error").textContent = "";
  document.querySelector("#due-error").textContent = "";
  document.querySelector("#form-error").textContent = "";
}

async function saveTask(event) {
  event.preventDefault();
  clearFormErrors();
  const titleInput = document.querySelector("#task-title");
  const dueInput = document.querySelector("#task-due");
  const title = titleInput.value.trim();
  if (!title) {
    document.querySelector("#title-error").textContent = "Enter a task title.";
    titleInput.focus();
    return;
  }
  if (!dueInput.value) {
    document.querySelector("#due-error").textContent = "Choose a due date and time.";
    dueInput.focus();
    return;
  }
  const data = {
    title,
    description: document.querySelector("#task-description").value.trim() || null,
    status: document.querySelector("#task-status").value,
    due_at: new Date(dueInput.value).toISOString(),
  };
  const saveButton = document.querySelector("#save-task");
  saveButton.disabled = true;
  saveButton.textContent = "Saving…";
  try {
    if (state.editingId === null) {
      await apiRequest("", { method: "POST", body: JSON.stringify(data) });
      showFeedback("Task created successfully.");
    } else {
      await apiRequest(`/${state.editingId}`, { method: "PATCH", body: JSON.stringify(data) });
      showFeedback("Task updated successfully.");
    }
    elements.dialog.close();
    await refreshTasks();
  } catch (error) {
    if (error.status === 409) {
      document.querySelector("#title-error").textContent = error.message;
      titleInput.focus();
    } else {
      document.querySelector("#form-error").textContent = error.message;
    }
  } finally {
    saveButton.disabled = false;
    saveButton.textContent = state.editingId === null ? "Save task" : "Save changes";
  }
}

function openDeleteDialog(taskId) {
  state.deletingId = taskId;
  elements.deleteDialog.showModal();
}

async function deleteTask() {
  if (state.deletingId === null) return;
  const button = document.querySelector("#confirm-delete");
  button.disabled = true;
  try {
    await apiRequest(`/${state.deletingId}`, { method: "DELETE" });
    elements.deleteDialog.close();
    showFeedback("Task deleted.");
    state.deletingId = null;
    await refreshTasks();
  } catch (error) {
    showFeedback(error.message, "error");
  } finally {
    button.disabled = false;
  }
}

document.querySelector("#open-create").addEventListener("click", openCreateDialog);
document.querySelector("#close-dialog").addEventListener("click", () => elements.dialog.close());
document.querySelector("#cancel-dialog").addEventListener("click", () => elements.dialog.close());
document.querySelector("#cancel-delete").addEventListener("click", () => elements.deleteDialog.close());
document.querySelector("#confirm-delete").addEventListener("click", deleteTask);
document.querySelector("#refresh-tasks").addEventListener("click", () => { hideFeedback(); refreshTasks(); });
elements.form.addEventListener("submit", saveTask);
elements.search.addEventListener("input", () => {
  clearTimeout(state.searchTimer);
  state.searchTimer = setTimeout(() => goToPage(1), 300);
});
elements.filter.addEventListener("change", () => goToPage(1));
elements.pageSize.addEventListener("change", () => {
  state.pageSize = Number(elements.pageSize.value);
  goToPage(1);
});
elements.prevPage.addEventListener("click", () => goToPage(state.page - 1));
elements.nextPage.addEventListener("click", () => goToPage(state.page + 1));
refreshTasks();

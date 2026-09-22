'use strict';

/*
 * Shared progress tracker for the CyberSafe Learning System.
 * Persists to sessionStorage so results survive navigation between pages
 * but never leak between different visitors/tabs on a shared computer -
 * sessionStorage is isolated per browser tab session and is cleared when
 * that tab/session ends.
 */
const CyberSafeProgress = (() => {
  const KEY = 'cybersafe_progress_v1';

  function emptyState() {
    return {
      // meta describes the current shape of each activity's content, so the
      // Achievements page can show accurate totals without duplicating the
      // lesson/scenario/quiz data that already lives on each page.
      meta: { lessons: null, scenarios: null, mythsTotal: null },
      lessons: {},   // { [lessonId]: { correct, total } }
      scenarios: {}, // { [scenarioId]: { correct, total } }
      myths: null,   // { correct, total } | null
    };
  }

  function load() {
    try {
      const raw = sessionStorage.getItem(KEY);
      if (!raw) return emptyState();
      const parsed = JSON.parse(raw);
      const base = emptyState();
      return {
        ...base,
        ...parsed,
        meta: { ...base.meta, ...(parsed.meta || {}) },
        lessons: parsed.lessons || {},
        scenarios: parsed.scenarios || {},
      };
    } catch (e) {
      return emptyState();
    }
  }

  function save(state) {
    try {
      sessionStorage.setItem(KEY, JSON.stringify(state));
    } catch (e) {
      /* sessionStorage unavailable (private mode, quota, etc.) - progress
         just won't persist for this visit. */
    }
  }

  function registerLessonsMeta(lessons) {
    const state = load();
    state.meta.lessons = lessons; // [{ id, totalQuestions }]
    save(state);
  }

  function registerScenariosMeta(scenarioIds) {
    const state = load();
    state.meta.scenarios = scenarioIds; // [id, ...]
    save(state);
  }

  function registerMythsMeta(total) {
    const state = load();
    state.meta.mythsTotal = total;
    save(state);
  }

  function recordLesson(lessonId, correct, total) {
    const state = load();
    state.lessons[lessonId] = { correct, total };
    save(state);
  }

  function recordScenario(scenarioId, correct, total) {
    const state = load();
    state.scenarios[scenarioId] = { correct, total };
    save(state);
  }

  function recordMyths(correct, total) {
    const state = load();
    state.myths = { correct, total };
    save(state);
  }

  function reset() {
    try {
      sessionStorage.removeItem(KEY);
    } catch (e) {
      /* ignore */
    }
  }

  return {
    load,
    reset,
    registerLessonsMeta,
    registerScenariosMeta,
    registerMythsMeta,
    recordLesson,
    recordScenario,
    recordMyths,
  };
})();

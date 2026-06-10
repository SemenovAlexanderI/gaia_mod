# GAIA Pipeline — Inspect AI с поддержкой техник и breakpoints

Модифицированная реализация бенчмарка [GAIA](https://huggingface.co/papers/2311.12983) на базе [Inspect AI](https://inspect.aisi.org.uk/), расширенная системой **breakpoints** — точек вмешательства в пайплайн для подключения и комбинирования техник улучшения качества.

## Мотивация

Стандартный `inspect_evals.gaia` запускает `react()` agent как монолитный solver. Задача — разбить пайплайн на явные точки, в которых можно подключить внешние техники (rollback, sampling, CoT injection и др.) без изменения ядра inspect.

***

## Архитектура

```
gaia_modified/
├── pipeline/
│   ├── agent.py          # instrumented_agent — solver с 4 breakpoints
│   ├── breakpoints.py    # BP enum + BPContext dataclass
│   ├── registry.py       # TechniqueRegistry — регистрация и запуск техник
│   └── technique.py      # Базовый класс Technique
├── techniques/
│   └── logging_probe.py  # Пример техники: логирование состояния на каждом BP
├── task.py               # build_gaia_task() — сборка Task с кастомным solver
├── run.py                # Entry point
└── test_pipeline.py      # Минимальный тест pipeline без GAIA датасета
```

### Breakpoints

Пайплайн разбит на 4 точки вмешательства:

| ID | Имя | Момент срабатывания |
|----|-----|---------------------|
| 0 | `BP.BEFORE_GENERATE` | Контекст получен, до первого generate |
| 1 | `BP.AFTER_TOOL_CALL` | Модель вернула tool_call, до исполнения |
| 2 | `BP.AFTER_TOOL_RESULT` | Tool вернул результат, до следующего generate |
| 3 | `BP.AFTER_FINAL_ANSWER` | Финальный ответ сформирован |

### Как работает техника

Каждая техника наследует `Technique` и определяет:
- `entry_points: list[BP]` — на каких точках активируется
- `apply(ctx: BPContext) -> BPContext` — логика вмешательства
- `should_apply(ctx: BPContext) -> bool` — условное применение (опционально)

```python
class MyTechnique(Technique):
    entry_points = [BP.AFTER_TOOL_CALL, BP.AFTER_FINAL_ANSWER]

    async def apply(self, ctx: BPContext) -> BPContext:
        # читаем и модифицируем ctx.state (TaskState)
        # ctx.meta — словарь для передачи сигналов между техниками
        return ctx
```

### TechniqueRegistry

Регистрация техник с указанием точек:

```python
from pipeline.registry import TechniqueRegistry
from pipeline.breakpoints import BP
from techniques.logging_probe import LoggingProbe

registry = (
    TechniqueRegistry()
    .register(LoggingProbe(verbose=True))               # все entry_points техники
    .register(MyTechnique(), bps=[BP.AFTER_TOOL_CALL])  # только конкретная точка
)
```

Техники на одной точке применяются **последовательно** в порядке регистрации. Параллельный запуск через `registry.trigger_parallel(bp, state)` возвращает список `TaskState` для агрегации.

***

## Запуск

### Требования

- Docker (для sandbox `aisiuk/inspect-tool-support`)
- [Ollama](https://ollama.com/) с загруженной моделью
- Python-окружение с зависимостями

```bash
pip install inspect-ai inspect-evals
ollama pull qwen3.5:9b
```

### Быстрый старт

```bash
# Тест pipeline на одном сэмпле (без GAIA датасета)
python test_pipeline.py

# Полный запуск на 5 сэмплах GAIA validation
python run.py
```

### Конфигурация в `run.py`

```python
registry = (
    TechniqueRegistry()
    .register(LoggingProbe(verbose=True))
)

task = build_gaia_task(registry=registry, split="validation")
eval(task, model="ollama/qwen3.5:9b", limit=5)
```

***

## Инструменты

В отличие от оригинального `default_solver`, который использует `react()` с `web_browser()`, наш solver использует:
- `bash(timeout=180)` — выполнение bash команд в sandbox
- `python(timeout=180)` — выполнение Python кода в sandbox
- `web_browser()` — браузер через Docker sandbox (не требует API ключей)

Всё выполняется внутри Docker контейнера `aisiuk/inspect-tool-support`.

***

## Что реализовано

- [x] 4 breakpoint-а в цикле tool use
- [x] `TechniqueRegistry` — регистрация техник на конкретные BP
- [x] Последовательное применение нескольких техник на одной точке
- [x] Параллельный запуск через `trigger_parallel()`
- [x] `BPContext.meta` — словарь для передачи сигналов между техниками
- [x] `should_apply()` — условное применение техники
- [x] `LoggingProbe` — пример техники для наблюдения за состоянием
- [x] Интеграция с `inspect_evals.gaia` датасетом и scorer
- [x] Поддержка Ollama моделей

## Что ещё нужно сделать

- [ ] **Priority при регистрации** — явный порядок техник через `priority=N` вместо порядка вызовов `.register()`
- [ ] **Exclusive режим** — механизм "техника взяла управление, остальные пропускаются" через `ctx.meta["handled"] = True`
- [ ] **Rollback-сигнал** — техника пишет `ctx.meta["rollback"] = N`, `agent.py` откатывает `state.messages` на N шагов и повторяет generate
- [ ] **Интерфейс Task 2** — подключить UI из параллельной задачи команды
- [ ] **Реализация техник**: rollback, parallel sampling, CoT injection, best-of-N
- [ ] **Тесты** для `TechniqueRegistry` и каждой техники отдельно

***

## Пример: добавить свою технику

1. Создать файл `techniques/my_technique.py`:

```python
from pipeline.technique import Technique
from pipeline.breakpoints import BP, BPContext

class MyTechnique(Technique):
    entry_points = [BP.BEFORE_GENERATE]

    async def apply(self, ctx: BPContext) -> BPContext:
        # Например, инжектировать дополнительный контекст в messages
        from inspect_ai.model._chat_message import ChatMessageUser
        ctx.state.messages.append(
            ChatMessageUser(content="Think step by step before using tools.")
        )
        return ctx
```

2. Зарегистрировать в `run.py`:

```python
from techniques.my_technique import MyTechnique
registry = TechniqueRegistry().register(MyTechnique())
```

***

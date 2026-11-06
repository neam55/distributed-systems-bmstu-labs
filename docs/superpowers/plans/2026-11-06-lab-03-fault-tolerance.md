# ЛР 3: Fault Tolerance — план реализации

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** добавить отказоустойчивость Hotels Booking System, вариант `v2`, сохранив работающее поведение ЛР 2.

**Architecture:** Gateway управляет Circuit Breaker, сборкой частичных ответов, компенсациями и очередью повторов. Reservation, Payment и Loyalty сохраняют собственные данные и не вызывают друг друга. Для лабораторной достаточно очереди в памяти одного процесса Gateway; PostgreSQL используется для бизнес-данных и ключей идемпотентности.

**Tech Stack:** Python 3.12, FastAPI, Pydantic 2, httpx, SQLAlchemy async + asyncpg, PostgreSQL, pytest + pytest-asyncio, Docker Compose, GitHub Actions, Newman 6.2.1. Сохранить существующие версии из `requirements*.txt`, Redis/RabbitMQ не добавлять.

**Spec:** требования пользователя к ЛР 3 и варианту Hotels Booking System, конкретизированные ниже в разделе «Контракт». План подготовлен 2026-11-06 по локальному коду и материалам шаблона; реализация завершена; результаты приведены в конце документа.

## Исходное состояние

- Ветка `lab_03` создана непосредственно от `lab_02`, исходный commit: `29af7121a142ccf665994ea0ebc8d32e83790f11`.
- Уже существуют четыре сервиса, Dockerfile для каждого, Compose, pytest, ruff/mypy и workflow `.github/workflows/classroom.yml`.
- `GET /manage/health` уже подключён во всех сервисах через `libs/common/health.py`; Compose и `scripts/wait-script.sh` используют этот адрес.
- `libs/common/http.py` превращает сетевые ошибки и все HTTP 4xx/5xx в один `UpstreamError`; общий обработчик возвращает `503`.
- `services/gateway/service.py`: чтения прекращаются при любой ошибке; создание брони не компенсируется; отмена сначала меняет Reservation, затем Payment, затем Loyalty.
- Loyalty уже атомарно обрабатывает `operationUid`: таблица `loyalty_operation` и блокировка строки пользователя защищают от повторного уменьшения счётчика.
- `scripts/check-regressions.cjs` проверяет повторную и конкурентную отмену, параллельные бронирования и `page=0`. Эти проверки нужно сохранить.
- В `v2/postman/collection.json` лежит коллекция ЛР 2; `scripts/test-script.sh` пока отсутствует.
- Обязательные hotel и `Test Max / 25 / GOLD / 10` уже есть в SQL seed. `.gitignore` игнорирует `*.md`; для этого плана добавлено точечное исключение.

## Global Constraints

- Вариант — `v2`; имена Compose: `gateway`, `reservation-service`, `payment-service`, `loyalty-service`.
- Порты: Gateway `8080`, Reservation `8070`, Payment `8060`, Loyalty `8050`.
- Circuit Breaker покрывает все исходящие GET Gateway, включая чтения внутри POST/DELETE-сценариев; `/manage/health` локальный и не обращается к соседям.
- Статистика Circuit Breaker хранится в памяти. Очередь повторов не эмулировать таблицей PostgreSQL.
- Повтор отложенной операции — через `10` секунд после неудачной попытки, до успешного выполнения; это интервал, а не срок жизни задания.
- При отказе некритичного источника сохранять успешные части ответа; при отказе критичного источника не выдавать фиктивный успех.
- Публичные DTO сохраняют camelCase, проверку `X-User-Name`, правила дат, цены и разграничение доступа из ЛР 2.
- Gateway запускается одним Uvicorn worker: очередь и breaker не разделяются между процессами.

## Контракт и решения

### Противоречие в HTTP-кодах

В тексте задания требуется `500` при отказе критичного источника. Однако [официальная коллекция ЛР 3](https://raw.githubusercontent.com/bmstu-rsoi/lab3-template/master/v2/postman/collection.json) проверяет `503` и точное сообщение `Loyalty Service unavailable` для отказа Loyalty. Это несовместимые ожидания для одного запроса.

Решение при реализации: для совместимости с неизменённой официальной приёмкой критические отказы дают `503`, тело — `{"message": "<Name> Service unavailable"}`. Перед реализацией этапа 1 зафиксировать в проекте, какой контракт принимает преподаватель. Если источником приёмки будет неизменённая официальная коллекция, выбрать `503` для отказов зависимостей и синхронно изменить ожидаемые коды в собственных тестах и документации. Не подгонять приложение по User-Agent и не ослаблять официальные проверки скрытно. До разрешения расхождения нельзя обещать прохождение исходной коллекции.

### Матрица чтений

| Внешняя операция | Критичный источник | Некритичный источник и fallback |
| --- | --- | --- |
| `GET /api/v1/hotels` | Reservation → `500` при отказе | Нет |
| `GET /api/v1/loyalty` | Loyalty → `500` при отказе | Нет |
| `GET /api/v1/reservations` | Reservation → `500` при отказе | Payment → `payment: {}` у каждой брони |
| `GET /api/v1/reservations/{uid}` | Reservation → `500` при отказе; неизвестная/чужая бронь → `404` | Payment → `payment: {}` |
| `GET /api/v1/me` | Reservation → `500` при отказе | Payment → `payment: {}`; Loyalty → `loyalty: {}`; оба могут отказать одновременно |

При реализации коды `500` в черновой матрице трактуются как `503` согласно принятому контракту официальной приёмки. Fallback — пустой JSON-объект, не `null`, не отсутствие поля и не выдуманная цена/скидка. Успешное отсутствие бронирований остаётся `[]`. Пропавший отдельный платёж также даёт `{}` только для соответствующей брони. `/me` не должен использовать строгое поведение публичного `/loyalty` без обработки отказа.

### Circuit Breaker

- Один экземпляр на upstream-сервис, общий для его GET; не создавать breaker на каждый входящий запрос или username.
- Настройки по умолчанию, выбранные для лабораторной: `CB_FAILURE_THRESHOLD=3`, `CB_RECOVERY_TIMEOUT=5`, `REQUEST_TIMEOUT=2`. Все значения положительные и задаются через настройки Gateway/Compose.
- `CLOSED`: считать последовательные транспортные ошибки, timeout и HTTP 5xx. Успешный ответ обнуляет счётчик. После третьего отказа перейти в `OPEN`; четвёртый последовательный запрос не отправлять в сеть.
- `OPEN`: до истечения 5 секунд сразу возбуждать типизированный отказ. Оркестратор выбирает fallback или ошибку по матрице. Проверять состояние реальным бизнес-GET, не успешным health-check вместо него.
- `HALF_OPEN`: после timeout разрешить только один пробный GET. Остальные конкурентные запросы получают немедленный отказ. Успех → `CLOSED`, ошибка → снова `OPEN` с новым timeout.
- Использовать `time.monotonic`, короткую `asyncio.Lock` для переходов состояния, не держать её во время HTTP. Защититься от запоздалых ответов старого поколения запросов; отменённая coroutine не оставляет breaker навечно в `HALF_OPEN`.
- HTTP 400/404 не считать отказом доступности. Существующее `not_found_ok=True` сохраняет смысл `None`. Не превращать ошибки пользовательского ввода и чужую бронь в fallback.
- POST/PATCH/DELETE не блокируются состоянием breaker и не повторяются автоматически HTTP-клиентом. Worker должен иметь возможность восстановить Loyalty, даже когда GET-breaker открыт.

### Бронирование: компенсация

Сохранить порядок существующего успешного сценария: проверка отеля → чтение действительной скидки → создание оплаты → создание брони → увеличение Loyalty. Если Loyalty недоступен уже при чтении скидки, завершить запрос до создания оплаты; нулевую скидку не подставлять.

При ошибке после создания оплаты отменять оплату. Если бронь уже создана, также переводить её в `CANCELED`; не оставлять активную бронь после неуспешного POST. Компенсации независимы: сбой отмены Reservation не отменяет попытку отменить Payment. Ошибку основного сценария не заменять ошибкой первой компенсации. Пользователю вернуть ошибку, успешный POST повторно не ставить в очередь.

Если компенсация временно не прошла, поставить именно компенсационную команду в очередь. Статус `CANCELED` и сохранённая история допустимы как бизнес-откат; физически удалять платежи и брони не нужно. Упоминание Ticket Service в условии трактовать как Payment Service варианта Hotels.

Timeout записи неоднозначен: сервер мог сохранить изменение, но ответ потерян. Поэтому для полного покрытия добавить внутренние ключи операций на создание Payment/Reservation и компенсируемое изменение Loyalty, как описано в этапе 5. Нельзя объявлять откат завершённым только на основании отсутствия ответа.

### Отмена: успешный ответ и повтор

1. Прочитать бронь с проверкой владельца. При отсутствии → `404`, Payment не вызывать.
2. Отменить Payment; при его недоступности вернуть ошибку, не менять Reservation/Loyalty.
3. Отменить Reservation идемпотентно. Если этот шаг временно не выполнен после успешной отмены оплаты, запланировать завершение отмены и вернуть ошибку; успех только при отказе Loyalty предусмотрен отдельным правилом ниже.
4. Уменьшить Loyalty с `operationUid=reservationUid`.
5. При временном отказе Loyalty сначала зарегистрировать задание, затем вернуть `204` без тела. Worker повторяет только незавершённую часть, не создаёт новую оплату/бронь.
6. Повторный DELETE и повтор после потерянного ответа Loyalty также дают `204`; счётчик уменьшается ровно один раз. Не пропускать восстановление только потому, что Reservation уже `CANCELED`.

### Очередь и её границы

Выбор для лабораторной — `asyncio.Queue` и worker в FastAPI lifespan. Задания содержат тип действия, username, UUID ресурсов/операции, число попыток; не хранить HTTP Request, DB session или coroutine. Ключ задания — тип действия + пользователь + UUID операции. Набор pending-ключей включает задания в обработке и ожидании повтора.

После неудачи планировать повтор через 10 секунд отдельно от worker: одна отложенная команда не должна задерживать остальные готовые задания. Учесть таймеры/задачи повторов при shutdown. В тестах внедрять часы и ожидание; unit-тесты не должны спать 5/10 секунд. При 4xx, означающем ошибку команды, логировать отдельный terminal failure; не маскировать его под доступность и не устраивать бесконечный горячий цикл.

При старте создать очередь/worker, при остановке отменить worker и отложенные повторы, дождаться их завершения и затем закрыть HTTP-клиенты. Логировать service, action, operationUid, attempt и переходы breaker; не добавлять публичные административные endpoint'ы ради тестов.

Ограничение выбранного решения: при аварийном рестарте Gateway очередь и breaker теряются; гарантии относятся к остановке/запуску зависимых сервисов при живом Gateway. Если требуется переживать его падение, отдельное расширение — внешняя долговечная очередь; это не входит в минимальную ЛР.

## Карта файлов

| Файл / область | Изменение и ответственность |
| --- | --- |
| `services/gateway/circuit_breaker.py` — новый | Машина состояний, допуск пробного запроса, статистика |
| `libs/common/http.py`, `libs/common/errors.py` | Классификация transport/5xx/4xx; подключаемая защита GET; стабильный внешний ErrorResponse |
| `services/gateway/config.py`, `dependencies.py`, `main.py` | Настройки, общие экземпляры breaker/очереди, lifespan и DI |
| `services/gateway/schemas.py`, `service.py`, `clients.py` | Fallback DTO, композиция чтений, исправленная оркестрация записей |
| `services/gateway/retry_queue.py` — новый | Команды, дедупликация и lifecycle очереди |
| `services/gateway/recovery.py` — новый | Выполнение типизированных компенсаций и завершения отмены |
| `services/payment/{api,schemas,service,repository,models}.py` | Внутренние идемпотентные создание/отмена по заранее известному paymentUid |
| `services/reservation/{api,schemas,service,repository,models}.py` | Внутренние идемпотентные создание/отмена по reservationUid |
| `services/loyalty/{api,schemas,service,repository,models}.py` | Идемпотентное обратимое увеличение счётчика |
| `postgres/scripts/{payments,reservations,loyalties}.sql` | Согласованные схемы для защиты от поздней записи/повтора |
| `tests/common/test_http.py` — новый | HTTP-классификация, отсутствие повторов записей |
| `tests/gateway/test_{circuit_breaker,fallbacks,retry_queue,recovery}.py` — новые | Отказы, восстановление, worker, компенсации |
| Существующие `tests/{gateway,payment,reservation,loyalty}/` | Обновить фейки, сигнатуры и регрессии |
| `tests/integration/test_idempotency.py` — новый | Реальные PostgreSQL-транзакции, гонки и tombstone |
| `scripts/test-script.sh` — новый; `v2/postman/` | Приёмочные сценарии ЛР 3 с реальным stop/start |
| `scripts/check-fault-tolerance.sh` — новый | Stop/start Payment и Reservation для дополнительных сценариев Newman |
| `v2/postman/fault-tolerance.collection.json` — новый | Дополнительные проверки Payment/Reservation, недостающие в шаблоне |
| `.github/workflows/classroom.yml`, `.github/classroom/autograding.json`, `docker-compose.yml` | Сборка, unit/integration, Newman, параметры варианта |

## Review Focus

1. Конкурентное восстановление breaker и запоздалые ответы: один probe, отсутствие ложного закрытия; этап 2.
2. Одновременный отказ двух некритичных источников: `/me` сохраняет брони и возвращает два корректных fallback; этап 3.
3. Повтор/потерянный ответ изменения Loyalty: ровно одно изменение, в том числе при конкурентных DELETE; этапы 4–6.
4. Ошибка самой компенсации и поздняя запись после timeout: задание не теряется, отменённая операция не становится снова активной; этапы 5–6.
5. Завершение приложения с заданиями и последующий запуск: worker закрыт, тесты изолированы, health Gateway не зависит от Loyalty; этапы 4 и 7.

## Этапы выполнения

Каждый этап: сначала тесты соответствующего поведения → запуск и ожидаемый FAIL → минимальная реализация → PASS и проверки качества → отдельный commit. Команды ниже выполняются из корня; Bash-сценарии на Windows запускать через WSL/Git Bash с доступным Docker. Ниже сохранена исходная последовательность работ; фактический статус и принятые отклонения приведены в разделе результатов. Реализация сохранена общим коммитом, а не отдельным коммитом на каждый этап.

### 1. Зафиксировать контракт отказов и health

**Файлы:** `libs/common/errors.py`, `libs/common/http.py`, `tests/common/test_errors.py`, новый `tests/common/test_http.py`, `tests/*/test_api.py`.

**Интерфейсы:** расширить `UpstreamError(service: str, detail: str, *, status_code: int | None = None, retryable: bool = True)`. Сетевой отказ/5xx — retryable; 4xx — отдельная ветка с сохранением HTTP-статуса для бизнес-обработки. `detail` оставить для логов, публичное сообщение стабильно.

- [ ] Зафиксировать решение по `500/503` из раздела «Противоречие»; проверить доступную для курса версию OpenAPI. Ссылка на OpenAPI была дана в условии, но её содержимое при подготовке плана получить не удалось.
- [ ] Написать `test_upstream_failure_contract` с точным кодом и `message`; через `httpx.MockTransport` проверить timeout, connect error, 500, 404 и отсутствие автоматического повтора POST.
- [ ] Запустить `pytest tests/common -v`, увидеть падение новых проверок; реализовать классификацию и обработчик.
- [ ] Параметризованно проверить health всех четырёх приложений: `200`, `{"status":"UP"}`; Gateway health остаётся `200` при сломанных HTTP-зависимостях.
- [ ] Запустить `pytest tests/common tests/gateway/test_api.py tests/payment/test_api.py tests/reservation/test_api.py tests/loyalty/test_api.py -v`; commit `test: define lab03 failure contracts`.

### 2. Реализовать Circuit Breaker для всех GET

**Файлы:** новый `services/gateway/circuit_breaker.py`, `libs/common/http.py`, `services/gateway/{config,dependencies}.py`, новый `tests/gateway/test_circuit_breaker.py`, `tests/common/test_http.py`.

**Интерфейсы:** в common объявить узкий `ReadGuard` Protocol с `async call(self, request: Callable[[], Awaitable[httpx.Response]]) -> httpx.Response`. Gateway реализует его классом `CircuitBreaker`; `ServiceClient(..., read_guard: ReadGuard | None = None)` вызывает guard только для GET. Common не импортирует Gateway. Конструктор breaker принимает threshold, recovery_timeout и `clock: Callable[[], float]`; открытый breaker возбуждает retryable `UpstreamError` без HTTP.

- [ ] Написать тесты `test_fourth_request_skips_transport_after_three_failures`, `test_success_resets_failures`, `test_only_one_half_open_probe`, `test_probe_failure_reopens`, `test_404_does_not_open`, `test_cancelled_probe_releases_slot`, `test_stale_success_does_not_close_new_generation`.
- [ ] Запустить `pytest tests/gateway/test_circuit_breaker.py tests/common/test_http.py -v`, подтвердить FAIL, реализовать состояния и подключение.
- [ ] На MockTransport проверить покрытие каждого GET-метода трёх HTTP-клиентов, в том числе чтения перед book/cancel; POST/PATCH/DELETE проходят при открытом breaker.
- [ ] В `dependencies.py` хранить три breaker рядом с долгоживущими клиентами; в тестах создавать свежие экземпляры. Проверить независимость Payment/Loyalty/Reservation.
- [ ] Повторить команду тестов до PASS; commit `feat: protect gateway reads with circuit breakers`.

### 3. Добавить fallback-ответы

**Файлы:** `services/gateway/{schemas,service}.py`, `tests/gateway/{fakes,conftest}.py`, новый `tests/gateway/test_fallbacks.py`, `tests/gateway/test_api.py`.

**Интерфейсы:** новый пустой DTO `EmptyInfo` с запретом extra-полей. `ReservationResponse.payment: PaymentInfo | EmptyInfo`; `UserInfoResponse.loyalty: LoyaltyInfoResponse | EmptyInfo`. Успешный DTO не меняется. `BookingService.get_loyalty` остаётся строгим; внутри `get_user_info` отдельно обрабатывать недоступность Loyalty.

- [ ] Создать параметризованные API-тесты всех строк матрицы: проверять статус, тело, camelCase и наличие успешных полей, отдельно transport timeout и 5xx.
- [ ] Добавить `test_me_preserves_reservations_when_payment_and_loyalty_fail`, `test_missing_payment_only_degrades_matching_reservation`, `test_foreign_reservation_still_returns_404`, `test_empty_reservations_skip_payment_lookup`.
- [ ] Запустить `pytest tests/gateway/test_fallbacks.py -v`, получить FAIL; реализовать fallback только для retryable отказов, без широкого `except Exception`.
- [ ] Проверить обе ветви HTTP и открытого breaker через API: результат одинаковый, при OPEN транспорт не вызывается.
- [ ] Запустить `pytest tests/gateway -v`; commit `feat: return partial responses for optional dependencies`.

### 4. Создать очередь восстановления

**Файлы:** новые `services/gateway/{retry_queue,recovery}.py`, `services/gateway/{config,dependencies,main}.py`, новые `tests/gateway/{test_retry_queue,test_recovery}.py`.

**Интерфейсы:** frozen dataclass `RetryJob(kind: RecoveryKind, username: str, operation_uid: UUID, payment_uid: UUID | None = None, reservation_uid: UUID | None = None)`. `RecoveryKind`: `CANCEL_PAYMENT`, `CANCEL_RESERVATION`, `REVERSE_BOOKING_LOYALTY`, `COMPLETE_CANCELLATION`. `RetryQueue.enqueue(job: RetryJob) -> None` — async; `start() -> None` — sync; `stop() -> None` — async. `RecoveryHandler.execute(job: RetryJob) -> None` — async; очередь получает этот callable через DI.

`COMPLETE_CANCELLATION` повторно отменяет Reservation и применяет Loyalty `-1` с прежним reservationUid; Payment к этому моменту уже отменён. Все команды идемпотентны на стороне владельца данных. `attempt` — служебное состояние очереди, не часть ключа дедупликации.

- [ ] Написать тесты: постановка/дедупликация, повтор не ранее 10 секунд, удаление pending только после успеха, потерянный ответ, обработка других готовых jobs во время ожидания, permanent 4xx и shutdown.
- [ ] Запустить `pytest tests/gateway/test_retry_queue.py tests/gateway/test_recovery.py -v`, получить FAIL; реализовать очередь с управляемым ожиданием и обработчик команд.
- [ ] Подключить lifecycle: очередь запускается один раз на приложение, тесты lifespan не используют глобальный worker; остановка не висит при неработающем upstream.
- [ ] Повторить проверки до PASS; commit `feat: add gateway recovery queue with delayed retries`.

### 5. Обеспечить идемпотентность и компенсируемые записи

**Файлы:** `services/{payment,reservation,loyalty}/{api,schemas,service,repository,models}.py`, SQL-файлы из карты, `services/gateway/clients.py`, соответствующие фейки/тесты; новый `tests/integration/test_idempotency.py`.

**Интерфейсы:** сохранить старые внутренние create-маршруты совместимыми, добавить передаваемые Gateway необязательные `paymentUid` и `reservationUid`. Клиенты: `create(price: int, *, payment_uid: UUID | None = None) -> PaymentData`; `create_reservation(..., reservation_uid: UUID | None = None) -> ReservationData`. UID генерируются до HTTP. Повтор с тем же UID и данными возвращает тот же ресурс, с другими данными — конфликт, а не второй ресурс.

Для каждого ресурса отмена с заранее известным UID должна атомарно запрещать позднюю активацию: локальная запись намерения отмены/tombstone и проверка при create в одной транзакционной модели. Это бизнес-состояние операции, не очередь. Для Reservation tombstone привязан к владельцу; публичная отмена неизвестной/чужой брони по-прежнему `404`, внутренний compensation-маршрут отделён от неё. Внутренние маршруты: `POST /api/v1/payments/{payment_uid}/compensate` и `POST /api/v1/reservations/{reservation_uid}/compensate`, ответ `204`. Reservation получает `X-User-Name`; повтор команды безопасен, в том числе до завершения create. В клиентах добавить async `compensate(payment_uid: UUID) -> None` и `compensate(reservation_uid: UUID, username: str) -> None` соответственно. Recovery-команды `CANCEL_PAYMENT`/`CANCEL_RESERVATION` используют эти маршруты, обычная пользовательская отмена — существующие cancel-маршруты.

Для Loyalty добавить `POST /api/v1/loyalty/operations/{operation_uid}/reverse` и `LoyaltyServiceClient.reverse_increment(username: str, operation_uid: UUID) -> LoyaltyData`. Запись операции хранит delta и состояние `APPLIED/REVERSED`. Reverse атомарно отменяет ранее применённый `+1`; если increment ещё не пришёл, сохраняет REVERSED-маркер без изменения счётчика. Поздний increment с тем же UID становится no-op. Повтор reverse не уменьшает счётчик второй раз. Существующая отмена `-1` остаётся идемпотентной по `(username, reservationUid)`; для booking increment использовать отдельный UUID.

- [ ] Написать тесты повторных create, конфликта payload, create после cancel-tombstone, reverse до/после increment и повторного reverse; сначала подтвердить FAIL на unit-тестах.
- [ ] Реализовать транзакционные правила с уникальными ключами и блокировками. Изменить SQL и ORM согласованно; для существующих volumes описать миграцию, init-скрипты не запускаются повторно автоматически.
- [ ] Проверить настоящую гонку create/cancel и increment/reverse на PostgreSQL в integration-тестах, а не только на Python-фейках. Независимо от порядка завершения не должно остаться PAID-ресурса после завершённой компенсации или лишнего `+1`.
- [ ] Команды: `pytest tests/payment tests/reservation tests/loyalty -v`; затем `pytest tests/integration/test_idempotency.py -v` с URL тестовых БД в env. Результат — PASS, повтор не создаёт второй ресурс и не меняет счётчик дважды.
- [ ] Commit `feat: make internal writes safe for retries and compensation`.

### 6. Исправить book/cancel и подключить recovery

**Файлы:** `services/gateway/service.py`, `services/gateway/{dependencies,recovery}.py`, `tests/gateway/{test_booking,fakes,conftest,test_recovery,test_api}.py`.

**Интерфейсы:** `BookingService(reservations, payments, loyalty, recovery: RetryQueue)`; внешние сигнатуры `book` и `cancel` сохранить. Компенсационные вызовы используют UID из этапа 5; при временном отказе ставят команды из этапа 4.

- [ ] В тестах book поочерёдно ломать чтение отеля, чтение скидки, создание Payment, создание Reservation, increment Loyalty; проверять вызовы, состояния всех трёх систем и отсутствие успешного ответа.
- [ ] Добавить `test_booking_rolls_back_payment_and_reservation_on_loyalty_500`, `test_booking_compensates_committed_write_after_lost_response`, `test_all_compensations_are_attempted`, `test_failed_compensation_is_queued_and_eventually_completes`. Для потерянного ответа сначала применить изменение в fake, затем выбросить transport error.
- [ ] Запустить `pytest tests/gateway/test_booking.py tests/gateway/test_recovery.py -v`, подтвердить FAIL; реализовать компенсацию, не перехватывая ошибки валидации до начала записей.
- [ ] В cancel сначала получить бронь/владельца, затем отменить Payment. Проверить: при его отказе бронь PAID и Loyalty не изменён; при отказе Loyalty ответ `204`, job зарегистрирован до возврата, после восстановления счётчик уменьшается один раз.
- [ ] Обновить существующий `test_cancel_retry_after_lost_loyalty_response_does_not_decrement_twice`: теперь первая попытка не бросает ошибку пользователю, а ставит retry. Сохранить тесты повторных и конкурентных DELETE, включая случай CANCELED с незавершённым Loyalty.
- [ ] Запустить `pytest tests/gateway tests/loyalty -v` и `node scripts/check-regressions.cjs` на поднятой системе; commit `feat: compensate bookings and retry cancellation completion`.

### 7. Подключить приёмку ЛР 3, Compose и CI

**Файлы:** `scripts/test-script.sh`, `scripts/wait-script.sh`, новый `scripts/check-fault-tolerance.sh`, `v2/postman/collection.json`, `v2/postman/environment.json`, новая `v2/postman/fault-tolerance.collection.json`, `.github/{workflows/classroom.yml,classroom/autograding.json}`, `docker-compose.yml`, `pyproject.toml`, `tests/integration/conftest.py`.

**Интерфейсы:** `scripts/test-script.sh v2 loyalty-service 8050`; также поддержать `VARIANT=v2`, `SERVICE_NAME=loyalty-service`, `PORT_NUMBER=8050`. Запуск из корня. Включить PostgreSQL integration-тесты отдельным pytest marker/env, чтобы обычные unit-тесты оставались без сети.

- [ ] Перенести [сценарий stop/start из шаблона](https://raw.githubusercontent.com/bmstu-rsoi/lab3-template/master/scripts/test-script.sh) и коллекцию ЛР 3 с папками `success`, `failover/step1`…`step4`. Сохранять environment между этапами: UUID созданной брони нужен последующей отмене. Обеспечить провал команды при любой ошибке Newman и восстановление остановленного сервиса в cleanup.
- [ ] Учесть выбранный контракт `500/503` явно: оригинал коллекции сохранять проверяемым, любое согласованное отличие кодов документировать. Не запускать всю коллекцию одним Newman-вызовом без управления контейнерами.
- [ ] В `autograding.json` заменить команду ЛР 2 на `newman ... --folder success ... v2/postman/...`; регрессии сохранить отдельной проверкой. Полный failover-сценарий запускать отдельным шагом CI один раз, не дублировать его ещё раз внутри runner.
- [ ] В Compose добавить настройки breaker/timeout/retry для Gateway. Сохранить четыре Dockerfile, health-check всех сервисов и один worker Gateway. Не связывать health Gateway с доступностью соседей и не пересоздавать PostgreSQL volume между stop/start Loyalty.
- [ ] В CI сохранить `ruff check .`, `mypy libs services`, `pytest -v` для unit; затем build → Compose up → wait health → PostgreSQL integration → Newman success/failover → дополнительные регрессии. Интеграционные тесты использовать с отдельными пользователями/UUID, не менять seed `Test Max`.
- [ ] Задать env варианта и сервиса в workflow, проверять из корня `./scripts/test-script.sh v2 loyalty-service 8050`. Значение `serviceName`/Heroku из текста задания для локального Compose не требуется: фактическое имя — `loyalty-service`.
- [ ] В `scripts/check-fault-tolerance.sh` организовать stop/start Payment и Reservation, а в дополнительной коллекции — папки `setup`, `payment-down`, `reservation-down`, `recovered`. После каждого сценария восстанавливать контейнер, проверять health и давать breaker пройти recovery timeout перед проверкой полного ответа; сохранять environment между Newman-вызовами. Скрипт завершать с ненулевым кодом при любой ошибке, восстанавливать контейнеры через trap. Факт немедленного отказа breaker доказывать unit-тестами числа HTTP-вызовов; не полагаться только на нестабильный замер latency.
- [ ] В job интеграции задать достаточный timeout, например 10 минут: у официальной коллекции есть паузы восстановления. На failure — `docker compose ps`/логи; `docker compose down -v` только в изолированном CI/test-окружении в `always()`. Для локальных пользовательских данных обычный `down` без `-v`.
- [ ] Commit `ci: run lab03 fault tolerance scenarios` после полного PASS.

## Итоговая проверка

```bash
python -m pip install -r requirements-dev.txt
ruff check .
mypy libs services
pytest -v -m "not integration"
docker compose config --quiet
docker compose build
docker compose up -d
WAIT_PORTS=8080,8070,8060,8050 bash scripts/wait-script.sh
# Для integration задать тестовые DATABASE_URL по fixture этапа 7.
pytest tests/integration -v -m integration
npm install --global newman@6.2.1
bash scripts/test-script.sh v2 loyalty-service 8050
bash scripts/check-fault-tolerance.sh
node scripts/check-regressions.cjs
docker compose down
```

Команды integration требуют выделенных тестовых БД и явного разрешающего env в fixture; никогда не очищать пользовательские БД для тестов. Unit job может выполнять существующее `pytest -v`, если integration-тесты по умолчанию пропускаются без этих настроек.

### Критерии готовности

- [x] Все пять публичных GET работают по матрице; circuit breaker защищает каждое upstream-чтение.
- [x] При N=3 четвёртый запрос не вызывает транспорт; через 5 секунд успешный одиночный probe восстанавливает чтение.
- [x] `/manage/health` каждого приложения возвращает `200` и используется скриптами/Compose.
- [x] Неудачное бронирование не оставляет активных оплаты/брони или прибавленного счётчика после завершения компенсаций; timeout и отказ самой компенсации проверены.
- [x] Отказ Payment при отмене не меняет бронь/Loyalty; отказ Loyalty после отмены возвращает `204` и восстанавливается через очередь.
- [x] Повторная доставка, параллельная отмена и потерянный ответ не удваивают изменения Loyalty.
- [x] Обязательные seed-данные сохранены; PostgreSQL не используется как очередь.
- [x] pytest, ruff, mypy, Docker build и Newman success/failover/regressions завершаются успешно на выбранном контракте ошибок.
- [x] CI запускается для `lab_03`; дальнейшие commit/push выполняются при реализации. Текущий результат — ветка и этот план.

## Источники

- [Шаблон ЛР 3](https://github.com/bmstu-rsoi/lab3-template) и формулировка пользователя.
- [OpenAPI Hotels Booking System](https://github.com/bmstu-rsoi/lab3-template/blob/master/v2/%5Binst%5D%5Bv2%5D%20Hotels%20Booking%20System.yml) — ссылка из условия; сверить при реализации, содержимое при подготовке плана недоступно.
- [Официальная Postman-коллекция](https://raw.githubusercontent.com/bmstu-rsoi/lab3-template/master/v2/postman/collection.json), [stop/start-скрипт](https://raw.githubusercontent.com/bmstu-rsoi/lab3-template/master/scripts/test-script.sh), [Classroom workflow](https://raw.githubusercontent.com/bmstu-rsoi/lab3-template/master/.github/workflows/classroom.yml), [autograding](https://raw.githubusercontent.com/bmstu-rsoi/lab3-template/master/.github/classroom/autograding.json).


## Реализация: принятые решения и проверка

- Реализованы Circuit Breaker, fallback `{}`, очередь с задержкой 10 секунд, компенсации, идемпотентность записей, миграции старых БД и CI/Newman сценарии.
- Для официальной приёмки принят HTTP `503` вместо `500` из текстового условия. Официальная коллекция не ослаблена.
- Миграции для старого volume находятся в `postgres/migrations/003-payments.sql`, `003-reservations.sql`, `003-loyalties.sql`; применять каждую к соответствующей БД до запуска новой версии. Новые БД инициализируются обновлёнными SQL автоматически.
- Unit-тесты запускаются без PostgreSQL. Для настоящих гонок задать `INTEGRATION_DATABASE_URL=postgresql+asyncpg://...`; fixture создаёт и удаляет только собственную случайную schema.
- Независимое ревью выявило повторное уменьшение Loyalty при отмене компенсированной неудачной брони; исправление исключает такие брони из обычных чтений/отмены, сохраняя видимость обычных отмен.
- Очередь остаётся process-local: после аварийного рестарта Gateway задания теряются. Это осознанное ограничение лабораторного решения.

Проверка после исправления ревью: 117 pytest passed, 3 PostgreSQL integration skipped без БД; ruff — PASS, mypy — PASS (48 source files), git diff --check — PASS. Регрессия скрытия компенсированных броней проверена RED→GREEN.

Полная приёмка GitHub Actions: https://github.com/neam55/distributed-systems-bmstu-labs/actions/runs/42257450017 — completed/success. Успешны unit/lint/mypy, Docker build, PostgreSQL concurrency, Newman success, Loyalty stop/start и Payment/Reservation fault tolerance. Локально PostgreSQL integration: 3/3 PASS; официальный сценарий success/step1–4: PASS. Для Windows добавлены необязательные BASE_URL, PAYMENT_PORT, RESERVATION_PORT, стандартные порты CI сохранены.

Итог локальной проверки: pytest — 120 passed без skips (включая 3 PostgreSQL race tests); Docker build — 4/4; официальный Newman — 20 requests / 20 assertions PASS; дополнительные отказы — 14 requests / 14 assertions PASS; JS concurrency/pagination regressions — 3/3 PASS. Изолированный тестовый стек остановлен без удаления volumes; исходный volume ЛР2 сохранён.

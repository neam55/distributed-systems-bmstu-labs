-- Схема Loyalty Service.

CREATE TABLE loyalty
(
    id                SERIAL PRIMARY KEY,
    username          VARCHAR(80) NOT NULL UNIQUE,
    reservation_count INT         NOT NULL DEFAULT 0,
    status            VARCHAR(80) NOT NULL DEFAULT 'BRONZE'
        CHECK (status IN ('BRONZE', 'SILVER', 'GOLD')),
    discount          INT         NOT NULL
);

-- Тестовые данные: пользователь приёмочной коллекции с золотым статусом.
INSERT INTO loyalty (username, reservation_count, status, discount)
VALUES ('Test Max', 25, 'GOLD', 10);

GRANT ALL ON ALL TABLES IN SCHEMA public TO program;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO program;

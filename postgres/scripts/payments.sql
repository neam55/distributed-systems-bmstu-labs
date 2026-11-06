-- Схема Payment Service.
-- payment_uid объявлен UNIQUE: это публичный идентификатор платежа, по нему идёт поиск.

CREATE TABLE payment
(
    id          SERIAL PRIMARY KEY,
    payment_uid uuid        NOT NULL UNIQUE,
    status      VARCHAR(20) NOT NULL
        CHECK (status IN ('PAID', 'CANCELED')),
    price       INT         NOT NULL
);

CREATE TABLE payment_cancellation
(
    payment_uid uuid PRIMARY KEY
);

GRANT ALL ON ALL TABLES IN SCHEMA public TO program;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO program;

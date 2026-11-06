-- Схема Reservation Service: сервис владеет и бронированиями, и справочником отелей
-- (в схеме варианта reservation.hotel_id ссылается на hotels.id).
-- hotels создаётся первой, так как на неё ссылается reservation.

CREATE TABLE hotels
(
    id        SERIAL PRIMARY KEY,
    hotel_uid uuid         NOT NULL UNIQUE,
    name      VARCHAR(255) NOT NULL,
    country   VARCHAR(80)  NOT NULL,
    city      VARCHAR(80)  NOT NULL,
    address   VARCHAR(255) NOT NULL,
    stars     INT,
    price     INT          NOT NULL
);

CREATE TABLE reservation
(
    id              SERIAL PRIMARY KEY,
    reservation_uid uuid UNIQUE NOT NULL,
    username        VARCHAR(80) NOT NULL,
    payment_uid     uuid        NOT NULL,
    hotel_id        INT REFERENCES hotels (id),
    status          VARCHAR(20) NOT NULL
        CHECK (status IN ('PAID', 'CANCELED')),
    start_date      TIMESTAMP WITH TIME ZONE,
    end_date        TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_reservation_username ON reservation (username);

-- Тестовые данные. Первый отель обязателен: его hotelUid зашит в приёмочную коллекцию.
INSERT INTO hotels (hotel_uid, name, country, city, address, stars, price)
VALUES ('049161bb-badd-4fa8-9d90-87c9a82b0668', 'Ararat Park Hyatt Moscow', 'Россия', 'Москва',
        'Неглинная ул., 4', 5, 10000),
       ('6ce14b26-6ea0-4b53-9bba-4f0b9fcd2c6f', 'Radisson Slavyanskaya', 'Россия', 'Москва',
        'пл. Европы, 2', 4, 8000),
       ('f1b7d4a3-5c2e-4f6a-8d9b-1e3c5a7b9d0f', 'Astoria', 'Россия', 'Санкт-Петербург',
        'Большая Морская ул., 39', 5, 12000),
       ('2a9c8f71-3d4e-4b6a-9f1c-7e5d2b8a4c63', 'Grand Hotel Europe', 'Россия', 'Санкт-Петербург',
        'Михайловская ул., 1/7', 5, 15000),
       ('c3e5a917-8b42-4d6f-a1c7-9e2b4d6f8a05', 'Hilton Garden Inn', 'Россия', 'Казань',
        'ул. Петербургская, 1', 4, 6000);

CREATE TABLE reservation_cancellation
(
    reservation_uid uuid PRIMARY KEY,
    username VARCHAR(80) NOT NULL
);

GRANT ALL ON ALL TABLES IN SCHEMA public TO program;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO program;

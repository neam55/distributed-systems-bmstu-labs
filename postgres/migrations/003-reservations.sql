-- Apply to the reservations database before running lab_03 against an existing volume.
CREATE TABLE IF NOT EXISTS reservation_cancellation
(
    reservation_uid uuid PRIMARY KEY,
    username VARCHAR(80) NOT NULL
);
GRANT ALL ON reservation_cancellation TO program;

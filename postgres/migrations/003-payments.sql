-- Apply to the payments database before running lab_03 against an existing volume.
CREATE TABLE IF NOT EXISTS payment_cancellation (payment_uid uuid PRIMARY KEY);
GRANT ALL ON payment_cancellation TO program;

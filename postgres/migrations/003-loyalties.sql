-- Lab 2 recorded operationUid only for cancellation (delta=-1).
-- The default applies to old rows only; new application writes supply delta explicitly.
ALTER TABLE loyalty_operation ADD COLUMN IF NOT EXISTS delta INT NOT NULL DEFAULT -1;
ALTER TABLE loyalty_operation ADD COLUMN IF NOT EXISTS state VARCHAR(20) NOT NULL DEFAULT 'APPLIED';
ALTER TABLE loyalty_operation ALTER COLUMN delta SET DEFAULT 0;

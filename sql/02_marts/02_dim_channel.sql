-- Acquisition channels.
CREATE OR REPLACE TABLE marts.dim_channel AS
SELECT channel, channel_name, channel_group, is_paid, cost_model, sort_order
FROM reference.channels;

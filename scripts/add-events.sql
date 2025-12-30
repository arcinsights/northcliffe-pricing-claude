-- Add events to boost pricing on specific dates
-- Replace YOUR-PROJECT-ID with your actual GCP project ID

-- UK Public Holidays 2025
INSERT INTO `YOUR-PROJECT-ID.pricing.events` (event_date, event_name, event_type, expected_impact, source)
VALUES
  ('2025-01-01', 'New Years Day', 'holiday', 'high', 'manual'),
  ('2025-04-18', 'Good Friday', 'holiday', 'medium', 'manual'),
  ('2025-04-21', 'Easter Monday', 'holiday', 'medium', 'manual'),
  ('2025-05-05', 'Early May Bank Holiday', 'holiday', 'medium', 'manual'),
  ('2025-05-26', 'Spring Bank Holiday', 'holiday', 'high', 'manual'),
  ('2025-08-25', 'Summer Bank Holiday', 'holiday', 'high', 'manual'),
  ('2025-12-25', 'Christmas Day', 'holiday', 'high', 'manual'),
  ('2025-12-26', 'Boxing Day', 'holiday', 'high', 'manual'),
  ('2025-12-31', 'New Years Eve', 'holiday', 'high', 'manual')
;

-- Add your local events here
-- Examples:

-- INSERT INTO `YOUR-PROJECT-ID.pricing.events` (event_date, event_name, event_type, expected_impact, source)
-- VALUES
--   ('2025-07-15', 'Local Music Festival', 'concert', 'high', 'manual'),
--   ('2025-08-20', 'Football Match - Wembley', 'sports', 'medium', 'manual'),
--   ('2025-09-10', 'Tech Conference', 'conference', 'medium', 'manual')
-- ;

INSERT INTO challenges
(name, description, start_date, end_date, rules)
VALUES
(
 'Wyzwanie Biegowe Marzec',
 'Liczą się tylko biegi powyżej 5km',
 '2026-03-01',
 '2026-03-31',
 '{
   "allowed_activity_types": ["bieganie_teren","bieganie_bieznia"],
   "min_distance_km": 5,
   "points_per_km": 10,
   "bonus_above_10km": 50
 }'
);
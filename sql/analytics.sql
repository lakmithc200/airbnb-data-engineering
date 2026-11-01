-- Run against ONE snapshot database. Currency is in snapshot_metadata.
-- Price coverage and ward comparisons; unknown/zero prices excluded from medians.
SELECT neighbourhood, COUNT(*) AS listings,
       COUNT(*) FILTER (WHERE price > 0) AS positive_price_listings,
       MEDIAN(price) FILTER (WHERE price > 0) AS median_nightly_price
FROM dim_listing GROUP BY neighbourhood ORDER BY median_nightly_price DESC;

-- Segmented pricing avoids comparing different accommodation types blindly.
SELECT neighbourhood, room_type, COUNT(*) AS n,
       MEDIAN(price) AS median_nightly_price
FROM dim_listing WHERE price > 0
GROUP BY neighbourhood, room_type HAVING COUNT(*) >= 5
ORDER BY neighbourhood, room_type;

-- State availability; never label the complement as actual occupancy.
SELECT month, COUNT(*) AS calendar_rows, COUNT(available) AS known_states,
       AVG(CAST(available AS INTEGER)) AS available_share
FROM fact_calendar GROUP BY month ORDER BY month;

-- Share of local supply controlled by the largest 10% of observed hosts.
WITH ranked AS (
  SELECT host_id, COUNT(*) AS listings,
         ROW_NUMBER() OVER (ORDER BY COUNT(*) DESC, host_id) AS rank,
         COUNT(*) OVER () AS total_hosts
  FROM dim_listing GROUP BY host_id
)
SELECT SUM(listings) FILTER (WHERE rank <= CEIL(total_hosts * 0.1)) * 1.0 /
       SUM(listings) AS top_decile_supply_share FROM ranked;

-- Review activity, NOT bookings. Latest month may be incomplete.
SELECT DATE_TRUNC('month', date) AS review_month, COUNT(*) AS reviews
FROM fact_review GROUP BY review_month ORDER BY review_month;

-- Demonstrate the fact-to-dimension join without listing/day fanout.
SELECT l.room_type, COUNT(*) AS listing_days,
       AVG(CAST(c.available AS INTEGER)) AS available_share
FROM fact_calendar c JOIN dim_listing l ON c.listing_id=l.id
GROUP BY l.room_type;

-- name: q01_acts_per_year_growth
-- Techniques: CTE, LAG window function.
-- Question: how did legislative activity change year over year since independence?
WITH yearly AS (
    SELECT adopted_year AS year, COUNT(*) AS acts
    FROM act
    WHERE adopted_year IS NOT NULL
    GROUP BY adopted_year
)
SELECT year,
       acts,
       LAG(acts) OVER (ORDER BY year) AS prev_year_acts,
       ROUND(100.0 * (acts - LAG(acts) OVER (ORDER BY year)) / LAG(acts) OVER (ORDER BY year), 1) AS yoy_pct
FROM yearly
WHERE year >= 1991
ORDER BY year;

-- name: q02_repealed_share_by_body
-- Techniques: JOIN over many-to-many link, GROUP BY/HAVING, CTE, RANK window function.
-- Question: which adopting bodies have the highest share of repealed acts (bodies with >= 500 acts)?
WITH per_body AS (
    SELECT b.name AS body,
           COUNT(*) AS acts,
           SUM(a.is_repealed) AS repealed
    FROM act a
    JOIN act_body ab ON ab.law_id = a.law_id
    JOIN body b ON b.body_id = ab.body_id
    GROUP BY b.body_id
    HAVING COUNT(*) >= 500
)
SELECT body,
       acts,
       repealed,
       ROUND(100.0 * repealed / acts, 1) AS repealed_pct,
       RANK() OVER (ORDER BY 1.0 * repealed / acts DESC) AS rank_by_share
FROM per_body
ORDER BY rank_by_share
LIMIT 15;

-- name: q03_top_areas_per_decade
-- Techniques: two CTEs, JOIN through link table, ROW_NUMBER with PARTITION BY.
-- Question: which regulation areas dominate each decade?
WITH decade_area AS (
    SELECT (a.adopted_year / 10) * 10 AS decade,
           la.name AS area,
           COUNT(*) AS acts
    FROM act a
    JOIN act_area aa ON aa.law_id = a.law_id
    JOIN legal_area la ON la.area_id = aa.area_id
    WHERE a.adopted_year >= 1990
    GROUP BY decade, la.area_id
),
ranked AS (
    SELECT decade, area, acts,
           ROW_NUMBER() OVER (PARTITION BY decade ORDER BY acts DESC) AS rn
    FROM decade_area
)
SELECT decade, rn AS position, area, acts
FROM ranked
WHERE rn <= 3
ORDER BY decade, rn;

-- name: q04_text_coverage_by_status
-- Techniques: LEFT JOIN, CTE with per-act flags, conditional aggregation.
-- Question: for which acts do we have a Mendeley full text, split by repealed or in force?
WITH flags AS (
    SELECT a.law_id,
           a.is_repealed,
           COALESCE(MAX(t.lang = 'ru'), 0) AS has_ru,
           COALESCE(MAX(t.lang = 'kk'), 0) AS has_kk
    FROM act a
    LEFT JOIN text_file t ON t.law_id = a.law_id
    GROUP BY a.law_id
)
SELECT CASE is_repealed WHEN 1 THEN 'repealed' ELSE 'in force' END AS status,
       COUNT(*) AS acts,
       SUM(has_ru) AS with_ru_text,
       SUM(has_kk) AS with_kk_text,
       SUM(has_ru AND has_kk) AS with_both,
       SUM(NOT has_ru AND NOT has_kk) AS without_text,
       ROUND(100.0 * SUM(has_ru OR has_kk) / COUNT(*), 1) AS any_text_pct
FROM flags
GROUP BY is_repealed;

-- name: q05_link_quality_by_match_type
-- Techniques: GROUP BY, window SUM over a partition for percentages.
-- Question: how reliable is the linking of text files to acts?
SELECT lang,
       match_type,
       COUNT(*) AS files,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY lang), 1) AS pct_of_lang,
       ROUND(AVG(size_bytes) / 1024.0, 1) AS avg_size_kb
FROM text_file
GROUP BY lang, match_type
ORDER BY lang, files DESC;

-- name: q06_missing_kazakh_titles_by_decade
-- Techniques: LEFT JOIN with a filtered subquery, GROUP BY, conditional sums (data-quality audit).
-- Question: in which decades are Kazakh titles missing or replaced by a captcha placeholder?
SELECT (a.adopted_year / 10) * 10 AS decade,
       COUNT(*) AS acts,
       SUM(kk.law_id IS NULL) AS no_kk_title,
       COALESCE(SUM(kk.is_placeholder), 0) AS captcha_title,
       ROUND(100.0 * (SUM(kk.law_id IS NULL) + COALESCE(SUM(kk.is_placeholder), 0)) / COUNT(*), 2) AS unusable_pct
FROM act a
LEFT JOIN (SELECT law_id, is_placeholder FROM act_title WHERE lang = 'kk') kk
       ON kk.law_id = a.law_id
WHERE a.adopted_year IS NOT NULL
GROUP BY decade
ORDER BY decade;

-- name: q07_title_group_sizes
-- Techniques: nested aggregation (subquery in FROM), CASE bucketing, window SUM OVER ().
-- Question: how many acts share an identical Russian title with others (a retrieval ambiguity measure)?
SELECT CASE WHEN n = 1 THEN '1 (unique)'
            WHEN n <= 5 THEN '2-5'
            WHEN n <= 50 THEN '6-50'
            ELSE '51+' END AS acts_with_same_title,
       COUNT(*) AS distinct_titles,
       SUM(n) AS acts,
       ROUND(100.0 * SUM(n) / SUM(SUM(n)) OVER (), 1) AS pct_of_acts
FROM (SELECT title, COUNT(*) AS n FROM act_title WHERE lang = 'ru' GROUP BY title) sizes
GROUP BY acts_with_same_title
ORDER BY MIN(n);

-- name: q08_most_repeated_titles
-- Techniques: JOIN, GROUP BY/HAVING, aggregates over dates.
-- Question: which Russian titles are reused most often, and over what period?
SELECT t.title,
       COUNT(*) AS acts,
       MIN(a.adopted_date) AS first_adopted,
       MAX(a.adopted_date) AS last_adopted,
       SUM(a.is_repealed) AS repealed
FROM act_title t
JOIN act a ON a.law_id = t.law_id
WHERE t.lang = 'ru'
GROUP BY t.title
HAVING COUNT(*) >= 100
ORDER BY acts DESC
LIMIT 10;

-- name: q09_cumulative_acts_top_regions
-- Techniques: IN-subquery, CTE, running total with SUM OVER (PARTITION BY ... ORDER BY).
-- Question: how does the stock of acts grow in the five largest regions since 2000?
WITH reg AS (
    SELECT r.name AS region, a.adopted_year AS year, COUNT(*) AS acts
    FROM act a
    JOIN region r ON r.region_id = a.region_id
    WHERE a.adopted_year >= 2000
      AND r.region_id IN (SELECT region_id FROM act GROUP BY region_id ORDER BY COUNT(*) DESC LIMIT 5)
    GROUP BY r.region_id, a.adopted_year
)
SELECT region, year, acts,
       SUM(acts) OVER (PARTITION BY region ORDER BY year) AS cumulative_acts
FROM reg
ORDER BY region, year;

-- name: q10_areas_per_act_by_form
-- Techniques: correlated subquery, JOIN, GROUP BY/HAVING.
-- Question: which act forms touch the most regulation areas at once?
SELECT f.name AS form,
       COUNT(*) AS acts,
       ROUND(AVG(s.n_areas), 2) AS avg_areas_per_act
FROM (
    SELECT af.form_id,
           a.law_id,
           (SELECT COUNT(*) FROM act_area x WHERE x.law_id = a.law_id) AS n_areas
    FROM act a
    JOIN act_form af ON af.law_id = a.law_id
) s
JOIN form f ON f.form_id = s.form_id
GROUP BY f.form_id
HAVING COUNT(*) >= 1000
ORDER BY avg_areas_per_act DESC
LIMIT 10;

-- name: q11_largest_texts_vs_form_average
-- Techniques: multi-table JOIN, window AVG over a partition, CTE.
-- Question: which Russian texts are far larger than the typical text of their act form?
WITH ru_texts AS (
    SELECT tf.file_id, tf.size_bytes, f.name AS form, ti.title, a.adopted_year
    FROM text_file tf
    JOIN act a ON a.law_id = tf.law_id
    JOIN act_form af ON af.law_id = a.law_id
    JOIN form f ON f.form_id = af.form_id
    JOIN act_title ti ON ti.law_id = a.law_id AND ti.lang = 'ru'
    WHERE tf.lang = 'ru'
),
with_avg AS (
    SELECT *, AVG(size_bytes) OVER (PARTITION BY form) AS form_avg_bytes
    FROM ru_texts
)
SELECT title, form, adopted_year,
       ROUND(size_bytes / 1024.0) AS size_kb,
       ROUND(size_bytes / form_avg_bytes, 1) AS times_form_average
FROM with_avg
ORDER BY size_bytes DESC
LIMIT 10;

-- name: q12_codes_with_most_articles
-- Techniques: three-table JOIN across text, passage and title layers, GROUP BY/HAVING, COUNT DISTINCT.
-- Question: which acts are real codes, judged by how many distinct articles were detected in their text?
SELECT t.title,
       COUNT(DISTINCT p.article_no) AS articles,
       COUNT(*) AS article_passages,
       ROUND(AVG(p.n_chars)) AS avg_passage_chars
FROM passage p
JOIN text_file tf ON tf.file_id = p.file_id AND tf.lang = 'ru'
JOIN act_title t ON t.law_id = tf.law_id AND t.lang = 'ru'
WHERE p.article_no IS NOT NULL
GROUP BY tf.law_id
HAVING COUNT(DISTINCT p.article_no) >= 100
ORDER BY articles DESC
LIMIT 10;

-- name: q13_passage_mix_by_kind
-- Techniques: CASE classification, window SUM over a partition.
-- Question: how much of the searchable text is article prose, other prose, or table-like content?
SELECT tf.lang,
       CASE WHEN p.article_no IS NOT NULL THEN 'article'
            WHEN p.is_table = 1 THEN 'table-like'
            ELSE 'other prose' END AS kind,
       COUNT(*) AS passages,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY tf.lang), 1) AS pct_of_lang,
       ROUND(AVG(p.n_chars)) AS avg_chars
FROM passage p
JOIN text_file tf ON tf.file_id = p.file_id
GROUP BY tf.lang, kind
ORDER BY tf.lang, passages DESC;

old structure:
WITH broker_details AS (
    SELECT
        call_id,
        broker_name,
        'intrinsics' AS type,
        bi.criteria AS criteria,
        bi.score AS score,
        bi.reason AS reason
    FROM broker_intrinsics bi
    UNION ALL
    SELECT
        call_id,
        broker_name,
        'adherence' AS type,
        ba.criteria AS criteria,
        ba.score AS score,
        ba.reason AS reason
    FROM broker_adherence ba
)
SELECT bs.broker_summary_id,
    bs.call_id,
    bs."timestamp",
    bs.broker_name,
    bs.role,
    bs.talk_time,
    bs.positives,
    bs.opportunities,
    bs.summary,
    bd.type, 
    bd.criteria,
    bd.score,
    bd.reason
FROM broker_summary bs
LEFT JOIN broker_details bd ON bs.call_id = bd.call_id and bs.broker_name = bd.broker_name

new structure:
WITH broker_details AS (
    SELECT
        bi.call_id,
        bi.broker_id,
        bi.broker_name,
        bi.role,
        bi.timestamp,
        'intrinsics' AS type,
        bi.criteria,
        bi.score,
        bi.reason
    FROM public.broker_intrinsics bi
    UNION ALL
    SELECT
        ba.call_id,
        ba.broker_id,
        ba.broker_name,
        ba.role,
        ba.timestamp,
        'adherence' AS type,
        ba.criteria,
        ba.score,
        ba.reason
    FROM public.broker_adherence ba
)
SELECT
    bs.broker_summary_id,
    bs.call_id,
    bs.timestamp,
    bs.broker_id,
    bs.broker_name,
    bs.role,
    bs.duration,
    bs.broker_talktime,
    bs.customer_talktime,
    bs.positives,
    bs.opportunities,
    bs.broker_overarching_summary,
    bd.type,
    bd.criteria,
    bd.score,
    bd.reason
FROM public.broker_summary bs
LEFT JOIN broker_details bd
    ON bs.call_id = bd.call_id
    AND bs.broker_id = bd.broker_id
WITH lead_details_union AS (
        SELECT
            ld.lead_id,
            ld.lead_details_id,
            ld.lead_name,
            ld.call_id,
            ld.timestamp AS details_timestamp,
            ld.duration,
            ld.durationInSecs,
            ld.criteria,
            ld.score,
            ld.reason
        FROM public.lead_details ld
    )

    SELECT
        ls.lead_summary_id,
        ls.lead_id,
        ls.call_id,
        ls.timestamp,
        ls.lead_name,
        ls.status,
        ls.lead_score_by_broker,
        ls.total_contact_attempts,
        ls.lead_affiliate_level_category,
        ls.audio_call_type,
        ls.audio_call_type_reason,
        ls.lead_type,
        ls.lead_type_reason,
        ls.lead_intrinsic_avg,
        ls.concern_type,
        ls.concern_type_reason,
        ls.dollar_amount,
        ls.account_type,
        ls.lead_qualification,
        ls.lead_qualification_reason,
        ls.summary,
        ld.lead_details_id,
        ld.details_timestamp,
        ld.duration,
        ld.durationInSecs,
        ld.criteria,
        ld.score,
        ld.reason
    FROM public.lead_summary ls
    LEFT JOIN lead_details_union ld 
        ON ls.lead_id = ld.lead_id
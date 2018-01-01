# This script runs on Fudul's PostgreSQL-based production server to
# update retention CSV statistics.  It is far more efficient to use
# raw SQL to calculate the retention rather than Django-based
# queryset.

ROOT_DIR=`dirname $(dirname $0)`
INDICATOR_FILE=$ROOT_DIR/privileged_files/indicators/retention.csv
D_USERNAME="fudul_django"
D_NAME="fudul_django"

psql -d $D_USERNAME $D_NAME -c  "COPY(
    SELECT active_days, current_cumulative_sum, older_cumulative_sum FROM (
        SELECT current_cumulative.active_days, current_cumulative_sum, older_cumulative_sum, MAX(current_cumulative_sum) OVER () as max_sum FROM (
            SELECT active_days, SUM(total_count) OVER (ORDER BY active_days DESC) as current_cumulative_sum FROM (
                SELECT active_days, count(*) as total_count FROM (
                    SELECT count(distinct date_trunc('day', submission_date)) as active_days FROM (
                        SELECT auth_user.id, exams_answer.submission_date FROM exams_answer
                        INNER JOIN exams_session ON (exams_answer.session_id = exams_session.id)
                        INNER JOIN auth_user ON (exams_session.submitter_id=auth_user.id)
                        UNION
                        SELECT auth_user.id, exams_session.submission_date FROM exams_session
                        INNER JOIN auth_user ON (exams_session.submitter_id=auth_user.id)
                    ) as current_unique_dates GROUP BY id
                ) as current_totals GROUP BY active_days
            ) as current_uncumulative
        ) as current_cumulative INNER JOIN (
            SELECT active_days, SUM(total_count) OVER (ORDER BY active_days DESC) as older_cumulative_sum FROM (
                SELECT active_days, count(*) as total_count FROM (
                    SELECT count(distinct date_trunc('day', submission_date)) as active_days FROM (
                        SELECT auth_user.id, exams_answer.submission_date FROM exams_answer
                        INNER JOIN exams_session ON (exams_answer.session_id = exams_session.id)
                        INNER JOIN auth_user ON (exams_session.submitter_id=auth_user.id)
                        WHERE exams_answer.submission_date <= date_trunc('day', NOW() - interval '1 month')
                        UNION
                        SELECT auth_user.id, exams_session.submission_date FROM exams_session
                        INNER JOIN auth_user ON (exams_session.submitter_id=auth_user.id)
                        WHERE exams_session.submission_date <= date_trunc('day', NOW() - interval '1 month')
                    ) as older_unique_dates GROUP BY id
                ) as older_totals GROUP BY active_days
            ) as older_uncumulative
        ) as older_cumulative ON (older_cumulative.active_days = current_cumulative.active_days)
    ) as top_totals WHERE current_cumulative_sum >= (max_sum * 0.05) ORDER BY active_days
) To STDOUT With CSV HEADER;" > $INDICATOR_FILE

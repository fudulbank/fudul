# This script runs on Fudul's PostgreSQL-based production server to
# update retention CSV statistics.  It is far more efficient to use
# raw SQL to calculate the retention rather than Django-based
# queryset.

ROOT_DIR=`dirname $(dirname $0)`
INDICATOR_FILE=$ROOT_DIR/privileged_files/indicators/retention.csv
D_USERNAME="fudul_django"
D_NAME="fudul_django"

psql -d $D_USERNAME $D_NAME -c  "COPY(
    SELECT active_days, cumulative_sum FROM (
        SELECT active_days, cumulative_sum, MAX(cumulative_sum) OVER () as max_sum FROM (
            SELECT active_days, SUM(total_count) OVER (ORDER BY active_days DESC) as cumulative_sum FROM (
                SELECT active_days, count(*) as total_count FROM (
                    SELECT count(distinct date_trunc('day', submission_date)) as active_days FROM (
                        SELECT auth_user.id, exams_answer.submission_date FROM exams_answer
                        INNER JOIN exams_session ON (exams_answer.session_id = exams_session.id)
                        INNER JOIN auth_user ON (exams_session.submitter_id=auth_user.id)
                        UNION
                        SELECT auth_user.id, exams_session.submission_date FROM exams_session
                        INNER JOIN auth_user ON (exams_session.submitter_id=auth_user.id)
                    ) as unique_dates GROUP BY id
                ) as totals GROUP BY active_days
            ) as uncumulative
        ) as cumulative
    ) as top_totals WHERE cumulative_sum >= (max_sum * 0.05) ORDER BY active_days
) To STDOUT With CSV HEADER;" > $INDICATOR_FILE

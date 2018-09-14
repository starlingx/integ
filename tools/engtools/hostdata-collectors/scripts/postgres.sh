#!/bin/bash
# Usage:  postgres.sh [-p <period_mins>] [-i <interval_seconds>] [-c <cpulist>] [-h]
TOOLBIN=$(dirname $0)

# Initialize tools environment variables, and define common utility functions
. ${TOOLBIN}/engtools_util.sh
tools_init
if [ $? -ne 0 ]; then
    echo "FATAL, tools_init - could not setup environment"
    exit $?
fi

# Enable use of INTERVAL_SEC sample interval
OPT_USE_INTERVALS=1

# Print key networking device statistics
function print_postgres {
    print_separator
    TOOL_HIRES_TIME

  # postgressql command: set user, disable pagination, and be quiet
    PSQL="sudo -u postgres psql --pset pager=off -q"

  # List postgres databases
    db_list=( $(${PSQL} -t -c "SELECT datname FROM pg_database WHERE datistemplate = false;") )
    ${ECHO} "# postgres databases"
    echo "db_list = ${db_list[@]}"
    ${ECHO}

  # List sizes of all postgres databases (similar to "\l+")
    ${ECHO} "# postgres database sizes"
    ${PSQL} -c "
SELECT
    pg_database.datname,
    pg_database_size(pg_database.datname),
    pg_size_pretty(pg_database_size(pg_database.datname))
FROM pg_database
ORDER BY pg_database_size DESC;
"

  # For each database, list tables and their sizes (similar to "\dt+")
    for db in "${db_list[@]}"; do
    ${ECHO} "# postgres database: ${db}"
    ${PSQL} -d ${db} -c "
SELECT
    table_schema,
    table_name,
    pg_size_pretty(table_size) AS table_size,
    pg_size_pretty(indexes_size) AS indexes_size,
    pg_size_pretty(total_size) AS total_size,
    live_tuples,
    dead_tuples
FROM (
    SELECT
        table_schema,
        table_name,
        pg_table_size(table_name) AS table_size,
        pg_indexes_size(table_name) AS indexes_size,
        pg_total_relation_size(table_name) AS total_size,
        pg_stat_get_live_tuples(table_name::regclass) AS live_tuples,
        pg_stat_get_dead_tuples(table_name::regclass) AS dead_tuples
    FROM (
        SELECT
            table_schema,
            table_name
        FROM information_schema.tables
        WHERE table_schema='public'
        AND table_type='BASE TABLE'
    ) AS all_tables
    ORDER BY total_size DESC
) AS pretty_sizes;
"

    ${ECHO} "# postgres database vacuum: ${db}"
    ${PSQL} -d ${db} -c "
SELECT
    relname,
    n_live_tup,
    n_dead_tup,
    last_vacuum,
    last_autovacuum,
    last_analyze,
    last_autoanalyze
FROM pg_stat_user_tables;
"
    done

  # Specific table counts (This is very SLOW, look at "live tuples" instead)
  # Number of keystone tokens
  #${ECHO} "# keystone token count"

  # Number of postgres connections
    ${ECHO} "# postgres database connections"
    CONN=$(ps -C postgres -o cmd= | wc -l)
    CONN_T=$(ps -C postgres -o cmd= | awk '/postgres: / {print $3}' | awk '{for(i=1;i<=NF;i++) a[$i]++} END {for(k in a) print k, a[k]}' | sort -k 2 -nr )
    ${ECHO} "connections total = ${CONN}"
    ${ECHO}
    ${ECHO} "connections breakdown:"
    ${ECHO} "${CONN_T}"
    ${ECHO}

    ${ECHO} "connections breakdown (query):"
    ${PSQL} -c "SELECT datname,state,count(*) from pg_stat_activity group by datname,state;"
    ${ECHO}

    ${ECHO} "connections idle age:"
    ${PSQL} -c "SELECT datname,age(now(),state_change) from pg_stat_activity where state='idle';"
    ${ECHO}
}

#-------------------------------------------------------------------------------
# MAIN Program:
#-------------------------------------------------------------------------------
# Parse input options
tools_parse_options "${@}"

# Set affinity of current script
CPULIST=""
set_affinity ${CPULIST}

LOG "collecting ${TOOLNAME} for ${PERIOD_MIN} minutes, with ${INTERVAL_SEC} second sample intervals."

# Print tools generic tools header
tools_header

# Calculate number of sample repeats based on overall interval and sampling interval
((REPEATS = PERIOD_MIN * 60 / INTERVAL_SEC))

for ((rep=1; rep <= REPEATS ; rep++)); do
    print_postgres
    sleep ${INTERVAL_SEC}
done
print_postgres
LOG "done"

# normal program exit
tools_cleanup 0
exit 0

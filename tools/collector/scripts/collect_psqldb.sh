#! /bin/bash
#
# Copyright (c) 2013-2014 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#


# Loads Up Utilities and Commands Variables
source /usr/local/sbin/collect_parms
source /usr/local/sbin/collect_utils

# postgres database commands
PSQL_CMD="sudo -u postgres psql --pset pager=off -q"
PG_DUMP_CMD="sudo -u postgres pg_dump"

SERVICE="database"
DB_DIR="${extradir}/database"
LOGFILE="${extradir}/database.info"
echo    "${hostname}: Database Info .....: ${LOGFILE}"

function is_service_active()
{
    active=`sm-query service postgres | grep "enabled-active"`
    if [ -z "$active" ] ; then
        return 0
    else
        return 1
    fi
}

###############################################################################
# All node types
###############################################################################
mkdir -p ${DB_DIR}

function log_database()
{
    db_list=( $(${PSQL_CMD} -t -c "SELECT datname FROM pg_database WHERE datistemplate = false;") )
    for db in "${db_list[@]}"
    do
        echo "postgres database: ${db}"
        ${PSQL_CMD} -d ${db} -c "
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
    done >> ${1}
}



DB_EXT=db.sql.txt
function database_dump()
{
    mkdir -p ${DB_DIR}
    db_list=( $(${PSQL_CMD} -t -c "SELECT datname FROM pg_database WHERE datistemplate = false;") )
    for DB in "${db_list[@]}"
    do
        if [ "$DB" != "keystone" -a "$DB" != "ceilometer" ] ; then
            echo "${hostname}: Dumping Database ..: ${DB_DIR}/$DB.$DB_EXT"
            (cd ${DB_DIR} ; sudo -u postgres pg_dump $DB > $DB.$DB_EXT)
        fi
    done
}

###############################################################################
# Only Controller
###############################################################################

if [ "$nodetype" = "controller" ] ; then
    is_service_active
    if [ "$?" = "0" ] ; then
        exit 0
    fi

    # postgres DB sizes
    delimiter ${LOGFILE} "formatted ${PSQL_CMD} -c"
    ${PSQL_CMD} -c "
    SELECT
        pg_database.datname,
        pg_database_size(pg_database.datname),
        pg_size_pretty(pg_database_size(pg_database.datname))
        FROM pg_database
        ORDER BY pg_database_size DESC;
    " >> ${LOGFILE}

    # Number of postgres connections
    delimiter ${LOGFILE} "ps -C postgres -o cmd="
    ps -C postgres -o cmd= >> ${LOGFILE} 2>>${COLLECT_ERROR_LOG}

    delimiter ${LOGFILE} "call to log_database"
    log_database ${LOGFILE}

    database_dump
fi

exit 0

def get_sqlfunctions():
    return {
        'fun_getjobneed': """
                    -- FUNCTION: public.fun_getjobneed(bigint, bigint, bigint)

                    -- DROP FUNCTION IF EXISTS public.fun_getjobneed(bigint, bigint, bigint);

                    CREATE OR REPLACE FUNCTION public.fun_getjobneed(
                        _peopleid bigint,
                        _buid bigint,
                        _clientid bigint)
                        RETURNS TABLE(id bigint, jobdesc character varying, plandatetime timestamp with time zone, expirydatetime timestamp with time zone, gracetime integer, receivedonserver timestamp with time zone, starttime timestamp with time zone, endtime timestamp with time zone, gpslocation geography, remarks text, cdtz timestamp with time zone, mdtz timestamp with time zone, pgroup_id bigint, asset_id bigint, cuser_id bigint, frequency character varying, job_id bigint, jobstatus character varying, jobtype character varying, muser_id bigint, performedby_id bigint, priority character varying, qset_id bigint, scantype character varying, people_id bigint, attachmentcount integer, identifier character varying, parent_id bigint, bu_id bigint, client_id bigint, seqno smallint, ticketcategory_id bigint, ctzoffset integer, multifactor numeric, uuid uuid, istimebound text, ticket_id bigint, remarkstype_id bigint) 
                        LANGUAGE 'plpgsql'
                        COST 100
                        VOLATILE PARALLEL UNSAFE
                        ROWS 1000

                    AS $BODY$
                                        DECLARE 
                                            groupids        TEXT;
                                        BEGIN 
                                            SELECT ARRAY(SELECT pgbelonging.pgroup_id as pg_id FROM pgbelonging WHERE pgbelonging.people_id=_peopleid AND pgbelonging.pgroup_id <> -1)::TEXT INTO groupids;

                                            RETURN QUERY
                                            SELECT jn.id, jn.jobdesc, jn.plandatetime, jn.expirydatetime, jn.gracetime, jn.receivedonserver, jn.starttime, jn.endtime, jn.gpslocation, 
                                                jn.remarks, jn.cdtz, jn.mdtz, jn.pgroup_id,jn.asset_id, jn.cuser_id, jn.frequency, jn.job_id, jn.jobstatus, jn.jobtype, jn.muser_id, jn.performedby_id, 
                                                jn.priority, jn.qset_id, jn.scantype, jn.people_id, jn.attachmentcount, jn.identifier, jn.parent_id,  
                                                jn.bu_id, jn.client_id, jn.seqno, jn.ticketcategory_id, jn.ctzoffset, jn.multifactor, jn.uuid, jn.other_info ->> 'istimebound' as istimebound,
                                                jn.ticket_id,jn.remarkstype_id
                                            FROM jobneed jn
                                            WHERE (( jn.plandatetime + INTERVAL '1 MINUTE' * jn.ctzoffset)::DATE BETWEEN (current_date) AND (current_date + 1) 
                                                OR (now() BETWEEN jn.plandatetime AND jn.expirydatetime)) 
                                            AND jn.bu_id = _buid AND jn.client_id = _clientid
                                            AND (jn.identifier NOT IN ('TICKET','EXTERNALTOUR'))
                                            AND (jn.people_id = _peopleid OR jn.cuser_id=_peopleid OR jn.muser_id=_peopleid OR jn.pgroup_id=any( groupids ::BIGINT[]))
                                            GROUP BY jn.id;
                                        END
                                        
                    $BODY$;

                    ALTER FUNCTION public.fun_getjobneed(bigint, bigint, bigint)
                        OWNER TO youtilitydba;

                    """,
    'fun_getexttourjobneed':"""
                            -- FUNCTION: public.fun_getexttourjobneed(bigint, bigint, bigint)
                            -- DROP FUNCTION IF EXISTS public.fun_getexttourjobneed(bigint, bigint, bigint);

                            CREATE OR REPLACE FUNCTION public.fun_getexttourjobneed(
                                _peopleid bigint,
                                _buid bigint,
                                _clientid bigint)
                                RETURNS TABLE(id bigint, jobdesc character varying, plandatetime timestamp with time zone, expirydatetime timestamp with time zone, gracetime integer, receivedonserver timestamp with time zone, starttime timestamp with time zone, endtime timestamp with time zone, gpslocation geography, remarks text, cdtz timestamp with time zone, mdtz timestamp with time zone, pgroup_id bigint, asset_id bigint, cuser_id bigint, frequency character varying, job_id bigint, jobstatus character varying, jobtype character varying, muser_id bigint, performedby_id bigint, priority character varying, qset_id bigint, scantype character varying, people_id bigint, attachmentcount integer, identifier character varying, parent_id bigint, bu_id bigint, client_id bigint, seqno smallint, ticketcategory_id bigint, ctzoffset integer, multifactor numeric, uuid uuid) 
                                LANGUAGE 'plpgsql'
                                COST 100
                                VOLATILE PARALLEL UNSAFE
                                ROWS 1000

                            AS $BODY$
                                                        DECLARE 
                                                            groupids        TEXT;
                                                        BEGIN 
                                                            SELECT ARRAY(SELECT pgbelonging.pgroup_id as pg_id FROM pgbelonging WHERE pgbelonging.people_id=_peopleid AND pgbelonging.pgroup_id <> -1)::TEXT INTO groupids;

                                                            RETURN QUERY
                                                            SELECT jn.id, jn.jobdesc, jn.plandatetime, jn.expirydatetime, jn.gracetime, jn.receivedonserver, jn.starttime, jn.endtime, jn.gpslocation, 
                                                                jn.remarks, jn.cdtz, jn.mdtz, jn.pgroup_id,jn.asset_id, jn.cuser_id, jn.frequency, jn.job_id, jn.jobstatus, jn.jobtype, jn.muser_id, jn.performedby_id, 
                                                                jn.priority, jn.qset_id, jn.scantype, jn.people_id, jn.attachmentcount, jn.identifier, jn.parent_id,  
                                                                jn.bu_id, jn.client_id, jn.seqno, jn.ticketcategory_id, jn.ctzoffset, jn.multifactor, jn.uuid
                                                            FROM jobneed jn
                                                            WHERE (( jn.plandatetime + INTERVAL '1 MINUTE' * jn.ctzoffset)::DATE BETWEEN (current_date) AND (current_date + 1) 
                                                                OR (now() BETWEEN jn.plandatetime AND jn.expirydatetime)) 
                                                            AND jn.client_id = _clientid
                                                            AND (jn.identifier = 'EXTERNALTOUR')
                                                            AND (jn.people_id = _peopleid OR jn.cuser_id=_peopleid OR jn.muser_id=_peopleid OR jn.pgroup_id=any( groupids ::BIGINT[]))
                                                            GROUP BY jn.id;
                                                        END
                                                        
                            $BODY$;

                            ALTER FUNCTION public.fun_getexttourjobneed(bigint, bigint, bigint)
                                OWNER TO youtilitydba;

                            """,
    'fn_get_schedule_for_adhoc':"""
                             -- FUNCTION: public.fn_get_schedule_for_adhoc(timestamp with time zone, bigint, bigint, bigint, bigint)

                            -- DROP FUNCTION IF EXISTS public.fn_get_schedule_for_adhoc(timestamp with time zone, bigint, bigint, bigint, bigint);

                            CREATE OR REPLACE FUNCTION public.fn_get_schedule_for_adhoc(
                                _plandatetime timestamp with time zone,
                                _buid bigint,
                                _peopleid bigint,
                                _assetid bigint,
                                _questionsetid bigint)
                                RETURNS TABLE(bu_id bigint, jobneedid bigint, jobdesc character varying, plandatetime timestamp with time zone, expirydatetime timestamp with time zone, asset_id bigint, qset_id bigint, people_id bigint, pgroup_id bigint, identifier character varying, jobstatus character varying, jobtype character varying) 
                                LANGUAGE 'plpgsql'
                                COST 100
                                VOLATILE PARALLEL UNSAFE
                                ROWS 1000

                            AS $BODY$
                            DECLARE
                            _assigned BIGINT;
                            _groupids       TEXT;
                            BEGIN 
                            SELECT ARRAY( SELECT pgbelonging.pgroup_id FROM pgbelonging WHERE pgbelonging.people_id= _peopleid AND pgbelonging.pgroup_id <> -1 )::TEXT INTO _groupids;

                            RETURN QUERY 
                            SELECT jn.bu_id, jn.id as jobneedid, jn.jobdesc, jn.plandatetime, jn.expirydatetime, jn.asset_id, jn.qset_id, jn.people_id, 
                            jn.pgroup_id, jn.identifier, jn.jobstatus, jn.jobtype
                            FROM jobneed jn
                            WHERE 1=1
                            AND jn.jobstatus NOT IN ('COMPLETED')
                            AND jn.asset_id= _assetid
                            AND jn.bu_id= _buid
                            AND jn.qset_id= _questionsetid
                            AND _plandatetime BETWEEN (jn.plandatetime - INTERVAL '1 minute' * jn.gracetime) AND jn.expirydatetime
                            AND (
                            jn.people_id = _peopleid OR
                            jn.pgroup_id  = any(_groupids ::BIGINT[])  
                            )
                            ORDER BY jn.plandatetime ASC LIMIT 1;

                            END
                            $BODY$;

                            ALTER FUNCTION public.fn_get_schedule_for_adhoc(timestamp with time zone, bigint, bigint, bigint, bigint)
                                OWNER TO youtilitydba;

                            """,
    'fn_menupbt':          """
                        -- FUNCTION: public.fn_menupbt(bigint, anyelement)

                        -- DROP FUNCTION IF EXISTS public.fn_menupbt(bigint, anyelement);

                        CREATE OR REPLACE FUNCTION public.fn_menupbt(
                            p_buid bigint DEFAULT 1,
                            anyelement anyelement DEFAULT 'jsonb'::text)
                            RETURNS anyelement
                            LANGUAGE 'plpgsql'
                            COST 100
                            VOLATILE PARALLEL UNSAFE
                        AS $BODY$
                        DECLARE 
                            _butext		text;
                            _buarray    bigint[];
                            _bujson     jsonb;
                        BEGIN 

                            IF anyelement='text' THEN
                                --RAISE NOTICE 'Printing Text:: true, false';
                                WITH RECURSIVE butree(id, bucode, buname, parent_id, depth, path) AS (
                                    SELECT id, bucode, buname, parent_id, 1::INT AS depth, bt.id::TEXT AS path
                                    FROM bt 
                                    WHERE id=p_buid  --Pass Any Node ID
                                    UNION ALL
                                    SELECT ch.id, ch.bucode, ch.buname, ch.parent_id, rt.depth + 1 AS depth, (rt.path || '->' || ch.id::TEXT) 
                                    FROM bt ch INNER JOIN butree rt ON rt.parent_id = ch.id and ch.id not in(-1,1)
                                )
                                select array_to_string(array(SELECT id FROM butree order by 1),' ')::text INTO _butext;
                                return _butext;
                            ELSIF anyelement='array' THEN
                                --RAISE NOTICE 'Printing Array';
                                WITH RECURSIVE butree(id, bucode, buname, parent_id, depth, path) AS (
                                    SELECT id, bucode, buname, parent_id, 1::INT AS depth, bt.id::TEXT AS path
                                    FROM bt 
                                    WHERE id=p_buid  --Pass Any Node ID
                                    UNION ALL
                                    SELECT ch.id, ch.bucode, ch.buname, ch.parent_id, rt.depth + 1 AS depth, (rt.path || '->' || ch.id::TEXT) 
                                    FROM bt ch INNER JOIN butree rt ON rt.parent_id = ch.id and ch.id not in(-1,1)
                                )
                                select array(SELECT id FROM butree) INTO _buarray;
                                return _buarray;
                            ELSIF anyelement='jsonb' THEN
                                --RAISE NOTICE 'Printing jsonb';
                                WITH RECURSIVE butree(id, bucode, buname, parent_id, depth, path) AS (
                                    SELECT id, bucode, buname, parent_id, 1::INT AS depth, bt.id::TEXT AS path
                                    FROM bt 
                                    WHERE id=p_buid  --Pass Any Node ID
                                    UNION ALL
                                    SELECT ch.id, ch.bucode, ch.buname, ch.parent_id, rt.depth + 1 AS depth, (rt.path || '->' || ch.id::TEXT) 
                                    FROM bt ch INNER JOIN butree rt ON rt.parent_id = ch.id and ch.id not in(-1,1)
                                )
                                SELECT jsonb_object_agg(id, to_jsonb(t) - 'id') res INTO _bujson FROM (SELECT id, bucode, buname, parent_id FROM butree) AS t;
                                --select * from butree INTO _bujson;
                                return _bujson;
                            ELSE
                                RAISE NOTICE '
                                Not Passing Proper Argument, Try Any One From Below..
                                select * from fn_menupbt(12::bigint, ''text''::text)
                                select * from fn_menupbt(12::bigint, ''array''::text) 
                                select * from fn_menupbt(12::bigint, ''jsonb''::text)';
                            END IF;
                            
                        END
                        $BODY$;

                        ALTER FUNCTION public.fn_menupbt(bigint, anyelement)
                            OWNER TO youtilitydba;
        
                        """,
    'fn_mendownbt':"""
                -- FUNCTION: public.fn_mendownbt(bigint, anyelement)

            -- DROP FUNCTION IF EXISTS public.fn_mendownbt(bigint, anyelement);

            CREATE OR REPLACE FUNCTION public.fn_mendownbt(
                p_buid bigint DEFAULT 1,
                anyelement anyelement DEFAULT 'jsonb'::text)
                RETURNS anyelement
                LANGUAGE 'plpgsql'
                COST 100
                VOLATILE PARALLEL UNSAFE
            AS $BODY$
            DECLARE 
                _butext		text;
                _buarray    bigint[];
                _bujson     jsonb;
            BEGIN 

                IF anyelement='text' THEN
                    --RAISE NOTICE 'Printing Text:: true, false';
                    WITH RECURSIVE butree(id, bucode, buname, parent_id, depth, path) AS (
                        SELECT id, bucode, buname, parent_id, 1::INT AS depth, bt.id::TEXT AS path
                        FROM bt 
                        WHERE id=p_buid  --Pass Any Node ID
                        UNION ALL
                        SELECT ch.id, ch.bucode, ch.buname, ch.parent_id, rt.depth + 1 AS depth, (rt.path || '->' || ch.id::TEXT) 
                        FROM bt ch INNER JOIN butree rt ON rt.id = ch.parent_id
                    )
                    select array_to_string(array(SELECT id FROM butree order by 1),' ')::text INTO _butext;
                    return _butext;
                ELSIF anyelement='array' THEN
                    --RAISE NOTICE 'Printing Array';
                    WITH RECURSIVE butree(id, bucode, buname, parent_id, depth, path) AS (
                        SELECT id, bucode, buname, parent_id, 1::INT AS depth, bt.id::TEXT AS path
                        FROM bt 
                        WHERE id=p_buid  --Pass Any Node ID
                        UNION ALL
                        SELECT ch.id, ch.bucode, ch.buname, ch.parent_id, rt.depth + 1 AS depth, (rt.path || '->' || ch.id::TEXT) 
                        FROM bt ch INNER JOIN butree rt ON rt.id = ch.parent_id
                    )
                    select array(SELECT id FROM butree) INTO _buarray;
                    return _buarray;
                ELSIF anyelement='jsonb' THEN
                    --RAISE NOTICE 'Printing jsonb';
                    WITH RECURSIVE butree(id, bucode, buname, parent_id, depth, path) AS (
                        SELECT id, bucode, buname, parent_id, 1::INT AS depth, bt.id::TEXT AS path
                        FROM bt 
                        WHERE id=p_buid  --Pass Any Node ID
                        UNION ALL
                        SELECT ch.id, ch.bucode, ch.buname, ch.parent_id, rt.depth + 1 AS depth, (rt.path || '->' || ch.id::TEXT) 
                        FROM bt ch INNER JOIN butree rt ON rt.id = ch.parent_id
                    )
                    SELECT jsonb_object_agg(id, to_jsonb(t) - 'id') res INTO _bujson FROM (SELECT id, bucode, buname, parent_id FROM butree) AS t;
                    --select * from butree INTO _bujson;
                    return _bujson;
                ELSE
                    RAISE NOTICE '
                    Not Passing Proper Argument, Try Any One From Below..
                    select * from fn_menupbt(12::bigint, ''text''::text)
                    select * from fn_menupbt(12::bigint, ''array''::text) 
                    select * from fn_menupbt(12::bigint, ''jsonb''::text)';
                END IF;
                
            END
            $BODY$;

            ALTER FUNCTION public.fn_mendownbt(bigint, anyelement)
                OWNER TO youtilitydba;

            """,
    'fn_menallbt':"""
                    -- FUNCTION: public.fn_menallbt(bigint, anyelement)

                    -- DROP FUNCTION IF EXISTS public.fn_menallbt(bigint, anyelement);

                    CREATE OR REPLACE FUNCTION public.fn_menallbt(
                        p_buid bigint DEFAULT 1,
                        anyelement anyelement DEFAULT 'jsonb'::text)
                        RETURNS anyelement
                        LANGUAGE 'plpgsql'
                        COST 100
                        VOLATILE PARALLEL UNSAFE
                    AS $BODY$
                    DECLARE 
                        _butext		text;
                        _buarray    bigint[];
                        _bujson     jsonb;
                    BEGIN 

                        IF anyelement='text' THEN
                            --RAISE NOTICE 'Printing Text:: true, false';
                            select array_to_string(ARRAY (
                            select  distinct * from(
                            (WITH RECURSIVE butree(id, bucode, buname, parent_id) AS (
                                SELECT id, bucode, buname, parent_id
                                FROM bt 
                                WHERE id=p_buid
                                UNION ALL
                                SELECT ch.id, ch.bucode, ch.buname, ch.parent_id
                                FROM bt ch INNER JOIN butree rt ON rt.parent_id = ch.id and ch.id not in (1,-1)
                            )
                            select id from butree)
                            union all
                            (WITH RECURSIVE butree(id, bucode, buname, parent_id, depth, path) AS (
                                SELECT id, bucode, buname, parent_id, 1::INT AS depth, bt.id::TEXT AS path
                                FROM bt 
                                WHERE id=p_buid
                                UNION ALL
                                SELECT ch.id, ch.bucode, ch.buname, ch.parent_id, rt.depth + 1 AS depth, (rt.path || '->' || ch.id::TEXT) 
                                FROM bt ch INNER JOIN butree rt ON rt.id = ch.parent_id
                            )
                            select id from butree))a order by id) ,' ') INTO _butext;
                            return _butext;
                        ELSIF anyelement='array' THEN
                            --RAISE NOTICE 'Printing Array';
                            select ARRAY (
                            select  distinct * from(
                            (WITH RECURSIVE butree(id, bucode, buname, parent_id) AS (
                                SELECT id, bucode, buname, parent_id
                                FROM bt 
                                WHERE id=p_buid
                                UNION ALL
                                SELECT ch.id, ch.bucode, ch.buname, ch.parent_id
                                FROM bt ch INNER JOIN butree rt ON rt.parent_id = ch.id and ch.id not in (1,-1)
                            )
                            select id from butree)
                            union all
                            (WITH RECURSIVE butree(id, bucode, buname, parent_id, depth, path) AS (
                                SELECT id, bucode, buname, parent_id, 1::INT AS depth, bt.id::TEXT AS path
                                FROM bt 
                                WHERE id=p_buid
                                UNION ALL
                                SELECT ch.id, ch.bucode, ch.buname, ch.parent_id, rt.depth + 1 AS depth, (rt.path || '->' || ch.id::TEXT) 
                                FROM bt ch INNER JOIN butree rt ON rt.id = ch.parent_id
                            )
                            select id from butree))a order by id) INTO _buarray;
                            return _buarray;
                        ELSIF anyelement='jsonb' THEN
                            --RAISE NOTICE 'Printing jsonb';
                            SELECT jsonb_object_agg(id, to_jsonb(t) - 'id') res INTO _bujson FROM
                            (select distinct id, bucode, buname, parent_id from(
                            (WITH RECURSIVE butree(id, bucode, buname, parent_id, depth, path) AS (
                                SELECT id, bucode, buname, parent_id, 1::INT AS depth, bt.id::TEXT AS path
                                FROM bt 
                                WHERE id=p_buid  --Pass Any Node ID
                                UNION ALL
                                SELECT ch.id, ch.bucode, ch.buname, ch.parent_id, rt.depth + 1 AS depth, (rt.path || '->' || ch.id::TEXT) 
                                FROM bt ch INNER JOIN butree rt ON rt.parent_id = ch.id and ch.id not in (1,-1)
                            )
                            SELECT id, bucode, buname, parent_id FROM butree)
                            union all
                            (WITH RECURSIVE butree(id, bucode, buname, parent_id, depth, path) AS (
                                SELECT id, bucode, buname, parent_id, 1::INT AS depth, bt.id::TEXT AS path
                                FROM bt 
                                WHERE id=p_buid  --Pass Any Node ID
                                UNION ALL
                                SELECT ch.id, ch.bucode, ch.buname, ch.parent_id, rt.depth + 1 AS depth, (rt.path || '->' || ch.id::TEXT) 
                                FROM bt ch INNER JOIN butree rt ON rt.id = ch.parent_id
                            )
                            SELECT id, bucode, buname, parent_id FROM butree))a ) as t;
                            return _bujson;
                        ELSE
                            RAISE NOTICE '
                            Not Passing Proper Argument, Try Any One From Below..
                            select * from fn_menallbt(12::bigint, ''text''::text)
                            select * from fn_menallbt(12::bigint, ''array''::text) 
                            select * from fn_menallbt(12::bigint, ''jsonb''::text)';
                        END IF;
                        
                    END
                    $BODY$;

                    ALTER FUNCTION public.fn_menallbt(bigint, anyelement)
                        OWNER TO youtilitydba;
            """,
    'fn_getbulist_basedon_idnf': """
                            -- FUNCTION: public.fn_getbulist_basedon_idnf(bigint, boolean, boolean)

                        -- DROP FUNCTION IF EXISTS public.fn_getbulist_basedon_idnf(bigint, boolean, boolean);

                        CREATE OR REPLACE FUNCTION public.fn_getbulist_basedon_idnf(
                            p_buid bigint,
                            p_cus boolean DEFAULT true,
                            p_si boolean DEFAULT true)
                            RETURNS text
                            LANGUAGE 'plpgsql'
                            COST 100
                            VOLATILE PARALLEL UNSAFE
                        AS $BODY$
                        DECLARE 
                            _buid   bigint  := -1;
                            _rArray text;
                            --select getbulist_basedon_idnf(1,false,true);
                        BEGIN 
                            IF p_buid is not null THEN 
                            _buid := p_buid;
                            END IF;
                            
                            IF (p_cus is true and p_si is false) THEN
                                select array_to_string(ARRAY (
                                select  * from( 
                                WITH RECURSIVE butree(id, bucode, buname, parent_id, identifier_id, depth, path) AS (
                                SELECT id, bucode, buname, parent_id, identifier_id, 1::INT AS depth, id::TEXT AS path
                                FROM bt
                                WHERE id=_buid and parent_id=-1
                                UNION ALL
                                SELECT ch.id, ch.bucode, ch.buname, ch.parent_id, ch.identifier_id, rt.depth + 1 AS depth, (rt.path || '->' || ch.id::TEXT) 
                                FROM bt ch 
                                INNER JOIN butree rt ON rt.id = ch.parent_id)
                                select butree.id from butree
                                INNER JOIN typeassist ta on ta.id=butree.identifier_id
                                WHERE '1'='1' and ta.tacode='CUSTOMER' 
                                ) x) ,' ') into _rArray ;
                                --RAISE NOTICE 'Return Whole Client List ::  %',_rArray;
                            ELSIF (p_cus is false and p_si is true) THEN 
                                select array_to_string(ARRAY (
                                select  * from( 
                                WITH RECURSIVE butree(id, bucode, buname, parent_id, identifier_id, depth, path) AS (
                                SELECT id, bucode, buname, parent_id, identifier_id, 1::INT AS depth, id::TEXT AS path
                                FROM bt
                                WHERE id=_buid and parent_id=-1
                                UNION ALL
                                SELECT ch.id, ch.bucode, ch.buname, ch.parent_id, ch.identifier_id, rt.depth + 1 AS depth, (rt.path || '->' || ch.id::TEXT) 
                                FROM bt ch 
                                INNER JOIN butree rt ON rt.id = ch.parent_id)
                                select butree.id from butree
                                INNER JOIN typeassist ta on ta.id=butree.identifier_id 
                                WHERE '1'='1' and ta.tacode='SITE' 
                                ) x) ,' ') into _rArray ;
                                --RAISE NOTICE 'Return Whole Client List ::  %',_rArray;
                            ELSIF (p_cus is true and p_si is true) THEN 
                                select array_to_string(ARRAY (
                                select  * from( 
                                WITH RECURSIVE butree(id, bucode, buname, parent_id, identifier_id, depth, path) AS (
                                SELECT id, bucode, buname, parent_id, identifier_id, 1::INT AS depth, id::TEXT AS path
                                FROM bt
                                WHERE id=_buid and parent_id=-1
                                UNION ALL
                                SELECT ch.id, ch.bucode, ch.buname, ch.parent_id, ch.identifier_id, rt.depth + 1 AS depth, (rt.path || '->' || ch.id::TEXT) 
                                FROM bt ch 
                                INNER JOIN butree rt ON rt.id = ch.parent_id)
                                select butree.id from butree
                                INNER JOIN typeassist ta on ta.id=butree.identifier_id
                                WHERE '1'='1' and ta.tacode in ('CUSTOMER','SITE')
                                ) x) ,' ') into _rArray ;
                                --RAISE NOTICE 'Return Whole Client List ::  %',_rArray;
                            ELSIF (p_cus is false and p_si is false) THEN 
                                select array_to_string(ARRAY (
                                select  * from( 
                                WITH RECURSIVE butree(id, bucode, buname, parent_id, identifier_id, depth, path) AS (
                                SELECT id, bucode, buname, parent_id, identifier_id, 1::INT AS depth, id::TEXT AS path
                                FROM bt
                                WHERE id=_buid and parent_id=-1
                                UNION ALL
                                SELECT ch.id, ch.bucode, ch.buname, ch.parent_id, ch.identifier_id, rt.depth + 1 AS depth, (rt.path || '->' || ch.id::TEXT) 
                                FROM bt ch 
                                INNER JOIN butree rt ON rt.id = ch.parent_id)
                                select butree.id from butree
                                INNER JOIN typeassist ta on ta.id=butree.identifier_id
                                WHERE '1'='1' and ta.tacode ='CLIENT'
                                ) x) ,' ') into _rArray ;
                            END IF;

                            return _rArray;
                            _rArray :='';
                        END
                        $BODY$;

                        ALTER FUNCTION public.fn_getbulist_basedon_idnf(bigint, boolean, boolean)
                            OWNER TO youtilitydba;

                        """,
    'fn_getassetvsquestionset':                 """
                            -- FUNCTION: public.fn_getassetvsquestionset(bigint, text, text)

                        -- DROP FUNCTION IF EXISTS public.fn_getassetvsquestionset(bigint, text, text);

                        CREATE OR REPLACE FUNCTION public.fn_getassetvsquestionset(
                            _siteid bigint,
                            _assetcode text,
                            _type text)
                            RETURNS text
                            LANGUAGE 'plpgsql'
                            COST 100
                            VOLATILE PARALLEL UNSAFE
                        AS $BODY$
                        DECLARE 
                            _qsids      TEXT[];
                            _rasset     RECORD;
                            _rqset      RECORD;
                        BEGIN
                            --RAISE NOTICE 'INPUT _siteid    :=%', _siteid;
                            --RAISE NOTICE 'INPUT _assetcode :=%', _assetcode;
                            --RAISE NOTICE 'INPUT _type      :=%', _type;
                            FOR _rqset IN SELECT qs.id, qs.qsetname, qs.bu_id,  qs.assetincludes
                        FROM questionset qs
                        WHERE qs.parent_id = 1
                        --AND qs.type IN ('QUESTIONSET', 'CHECKLIST', 'ASSETMAINTENANCE')
                        AND qs.bu_id IN (_siteid) 
                        AND  _assetcode = ANY(qs.assetincludes)
                            LOOP
                                --RAISE NOTICE 'REPORT :=% >> %', _rqset.qsetname, _rqset.assetincludes;
                                IF lower(_type) = 'name' THEN
                                    _qsids:= array_append(_qsids, _rqset.qsetname::TEXT);
                                ELSE
                                    _qsids:= array_append(_qsids, _rqset.id::TEXT);
                                END IF;
                            END LOOP;  
                            --RAISE NOTICE 'SRIDS :=%', _qsids;
                            --RAISE NOTICE 'UNIQUE :=%', ARRAY(SELECT DISTINCT UNNEST(_qsids::TEXT[]) ORDER BY 1);
                            IF lower(_type) = 'name' THEN
                                RETURN ARRAY_TO_STRING(ARRAY(SELECT DISTINCT UNNEST(_qsids::TEXT[]) ORDER BY 1), '~');
                            ELSE
                                RETURN ARRAY_TO_STRING(ARRAY(SELECT DISTINCT UNNEST(_qsids::TEXT[]) ORDER BY 1), ' ');
                            END IF;
                        END
                        $BODY$;

                        ALTER FUNCTION public.fn_getassetvsquestionset(bigint, text, text)
                            OWNER TO youtilitydba;

                            """,
    'fn_getassetdetails':"""
                            -- FUNCTION: public.fn_getassetdetails(timestamp with time zone, bigint)

                        -- DROP FUNCTION IF EXISTS public.fn_getassetdetails(timestamp with time zone, bigint);

                        CREATE OR REPLACE FUNCTION public.fn_getassetdetails(
                            _mdtz timestamp with time zone,
                            _siteid bigint)
                            RETURNS TABLE(id bigint, uuid uuid, assetcode character varying, assetname character varying, enable boolean, iscritical boolean, gpslocation geography, parent_id bigint, runningstatus character varying, identifier character varying, type_id bigint, category_id bigint, subcategory_id bigint, brand_id bigint, ctzoffset integer, capacity numeric, unit_id bigint, bu_id bigint, client_id bigint, cuser_id bigint, muser_id bigint, cdtz timestamp with time zone, mdtz timestamp with time zone, location_id bigint, servprov_id bigint, servprovname character varying, qsetids text, qsetname text) 
                            LANGUAGE 'plpgsql'
                            COST 100
                            VOLATILE PARALLEL UNSAFE
                            ROWS 1000

                        AS $BODY$
                        DECLARE
                        BEGIN
                            RETURN QUERY
                                SELECT a.id, a.uuid, a.assetcode, a.assetname, a.enable, a.iscritical, a.gpslocation, a.parent_id, a.runningstatus, a.identifier,
                                a.type_id, a.category_id, a.subcategory_id, a.brand_id, a.ctzoffset ,
                                --a.model, a.supplier, 
                                a.capacity, a.unit_id, 
                                --a.yom, a.msn, a.bdate, a.pdate, a.isdate,a.billval, a.servprov, a.service, a.sfdate, a.stdate, a.meter, 
                                a.bu_id, a.client_id, a.cuser_id, a.muser_id, a.cdtz, a.mdtz,
                                a.location_id,
                                a.servprov_id,sp.buname as servprovname,
                                fn_getassetvsquestionset(a.bu_id, a.id::text, '') as qsetids,
                                fn_getassetvsquestionset(a.bu_id, a.id::text, 'name') as qsetname
                            FROM asset a
                            LEFT JOIN asset l ON l.id= a.parent_id
                            LEFT JOIN bt sp ON a.servprov_id=sp.id
                            WHERE a.mdtz >= _mdtz AND a.bu_id IN (_siteid) AND a.identifier <> 'NEA' and a.enable=true;
                        END;
                        $BODY$;

                        ALTER FUNCTION public.fn_getassetdetails(timestamp with time zone, bigint)
                            OWNER TO youtilitydba;

    """,
    
    'fn_get_siteslist_web': """
                            -- FUNCTION: public.fn_get_siteslist_web(bigint, bigint)

                        -- DROP FUNCTION IF EXISTS public.fn_get_siteslist_web(bigint, bigint);

                        CREATE OR REPLACE FUNCTION public.fn_get_siteslist_web(
                            p_clientid bigint,
                            p_peopleid bigint)
                            RETURNS TABLE(id bigint, bucode character varying, buname character varying, butype_id bigint, butypename character varying, enable boolean, cdtz timestamp with time zone, mdtz timestamp with time zone, cuser_id bigint, muser_id bigint) 
                            LANGUAGE 'plpgsql'
                            COST 100
                            VOLATILE PARALLEL UNSAFE
                            ROWS 1000

                        AS $BODY$
                        DECLARE
                            _isAdmin    boolean;
                            _sitegroup  text = '';
                            _sitelist   text = '';
                        BEGIN
                            SELECT p.isadmin INTO _isAdmin FROM people as p WHERE p.client_id= p_clientid AND p."id"= p_peopleid;
                            --SELECT string_to_array(assignsitegroup,' ')::text INTO _sitegroup FROM people WHERE people.buid= p_clientid AND peopleid= p_peopleid;        
                            
                            IF  (_isAdmin is true) THEN
                                --ADMIN
                                RETURN QUERY
                                SELECT distinct bu.id, 
                                    bu.bucode, 
                                    bu.buname, 
                                    bu.butype_id,
                                    t.taname as butypename,
                                    bu.enable,
                                    bu.cdtz, 
                                    bu.mdtz, 
                                    bu.cuser_id, 
                                    bu.muser_id 
                                FROM bt as bu
                                LEFT JOIN typeassist t on t.id= bu.butype_id 
                                WHERE bu.enable and bu.id IN (select unnest(string_to_array(fn_get_bulist(p_clientid::bigint,true,true,'Text', null::text), ' '))::bigint);
                            ELSE
                                RETURN QUERY
                                SELECT distinct bu.id, 
                                    bu.bucode, 
                                    bu.buname, 
                                    bu.butype_id,
                                    t.taname as butypename,
                                    bu.enable,
                                    bu.cdtz, 
                                    bu.mdtz, 
                                    bu.cuser_id, 
                                    bu.muser_id
                                FROM(
                                SELECT assignsites_id as site FROM pgbelonging WHERE pgroup_id = ANY((select string_to_array(people_extras->>'assignsitegroup', ' ')::text 
                                FROM people WHERE client_id= p_clientid AND people.id= p_peopleid)::bigint[])
                                UNION
                                SELECT sitepeople.bu_id as site FROM sitepeople WHERE people_id= p_peopleid AND current_date BETWEEN fromdt AND uptodt
                                )x
                                INNER JOIN bt as bu on bu.id=x.site
                                LEFT JOIN typeassist t ON t.id= bu.butype_id
                                WHERE bu.enable;
                            END IF;
                        END
                        $BODY$;

                        ALTER FUNCTION public.fn_get_siteslist_web(bigint, bigint)
                            OWNER TO youtilitydba;

    """,
    
    'fn_get_bulist':           """
                                -- FUNCTION: public.fn_get_bulist(bigint, boolean, boolean, text, anyelement)

                            -- DROP FUNCTION IF EXISTS public.fn_get_bulist(bigint, boolean, boolean, text, anyelement);

                            CREATE OR REPLACE FUNCTION public.fn_get_bulist(
                                p_buid bigint DEFAULT 1,
                                p_up boolean DEFAULT true,
                                p_dn boolean DEFAULT true,
                                phrase text DEFAULT 'jsonb'::text,
                                anyelement anyelement DEFAULT NULL::jsonb)
                                RETURNS SETOF anyelement 
                                LANGUAGE 'plpgsql'
                                COST 100
                                VOLATILE PARALLEL UNSAFE
                                ROWS 1000

                            AS $BODY$
                            DECLARE 
                                _butext		text;
                                _buarray    bigint[];
                                _bujson     jsonb;
                                query       varchar;
                                phrase      text:=lower(phrase);
                            BEGIN 
                                RAISE NOTICE 'Phrase :: %', phrase;
                                IF lower(phrase)='text' THEN
                                    IF (p_up is true and p_dn is false) THEN
                                        --RAISE NOTICE 'Printing Text:: true, false';
                                        query   := 'select fn_menupbt('|| p_buid ||','''|| phrase ||'''::text)';
                                        query   := TRIM(query);
                                        RETURN QUERY EXECUTE format(query);
                                    ELSIF (p_up is true and p_dn is true) THEN
                                        --RAISE NOTICE 'Printing Text:: true, true';
                                        query   := 'select fn_menallbt('|| p_buid ||','''|| phrase ||'''::text)';
                                        query   := TRIM(query);
                                        RETURN QUERY EXECUTE format(query);
                                    ELSIF (p_up is false and p_dn is true) THEN
                                        --RAISE NOTICE 'Printing Text:: false, true';
                                        query   := 'select fn_mendownbt('|| p_buid ||','''|| phrase ||'''::text)';
                                        query   := TRIM(query);
                                        RETURN QUERY EXECUTE format(query);
                                    ELSE
                                        --RAISE NOTICE 'Printing Text:: false, false';
                                        query   := 'select '|| p_buid ||'::text';
                                        query   := TRIM(query);
                                        RETURN QUERY EXECUTE format(query);
                                    END IF;
                                ELSIF lower(phrase)='array' THEN
                                    IF (p_up is true and p_dn is false) THEN
                                        --RAISE NOTICE 'Printing Array:: true, false';
                                        query   := 'select fn_menupbt('|| p_buid ||','''|| phrase ||'''::text)::bigint[]';
                                        query   := TRIM(query);
                                        RETURN QUERY EXECUTE format(query);
                                    ELSIF (p_up is true and p_dn is true) THEN
                                        --RAISE NOTICE 'Printing Array:: true, true';
                                        query   := 'select fn_menallbt('|| p_buid ||','''|| phrase ||'''::text)::bigint[]';
                                        query   := TRIM(query);
                                        RETURN QUERY EXECUTE format(query);
                                    ELSIF (p_up is false and p_dn is true) THEN
                                        --RAISE NOTICE 'Printing Array:: false, true';
                                        query   := 'select fn_mendownbt('|| p_buid ||','''|| phrase ||'''::text)::bigint[]';
                                        query   := TRIM(query);
                                        RETURN QUERY EXECUTE format(query);
                                    ELSE
                                        --RAISE NOTICE 'Printing Array :: false, false';
                                        query   := 'select array(select '|| p_buid ||')::bigint[]';
                                        query   := TRIM(query);
                                        RETURN QUERY EXECUTE format(query);
                                    END IF;
                                ELSIF lower(phrase)='jsonb' THEN
                                    IF (p_up is true and p_dn is false) THEN
                                        --RAISE NOTICE 'Printing jsonb:: true, false';
                                        query   := 'select fn_menupbt('|| p_buid ||','''|| phrase ||'''::text)::jsonb';
                                        query   := TRIM(query);
                                        RETURN QUERY EXECUTE format(query);
                                    ELSIF (p_up is true and p_dn is true) THEN
                                        --RAISE NOTICE 'Printing jsonb:: true, true';
                                        query   := 'select fn_menallbt('|| p_buid ||','''|| phrase ||'''::text)::jsonb';
                                        query   := TRIM(query);
                                        RETURN QUERY EXECUTE format(query);
                                    ELSIF (p_up is false and p_dn is true) THEN
                                        --RAISE NOTICE 'Printing jsonb:: false, true';
                                        query   := 'select fn_mendownbt('|| p_buid ||','''|| phrase ||'''::text)::jsonb';
                                        query   := TRIM(query);
                                        RETURN QUERY EXECUTE format(query);
                                    ELSE
                                        --RAISE NOTICE 'Printing jsonb:: false, false';
                                        query   := 'SELECT jsonb_object_agg(id, to_jsonb(t) - ''id'')::jsonb res  FROM (select distinct id, bucode, buname, parent_id from bt where id='||p_buid||') as t ';
                                        query   := TRIM(query);
                                        RETURN QUERY EXECUTE format(query);
                                    END IF;
                                ELSE
                                    RAISE NOTICE '
                                    Not Passing Proper Argument, Try Any One From Below..
                                    select * from fn_get_bulist(11::bigint, true::boolean, true::boolean,''Text'', null::text);
                                    select * from fn_get_bulist(12::bigint, true::boolean, true::boolean,''arRay'', null::bigint[]);
                                    select * from fn_get_bulist(4::bigint, true::boolean, true::boolean,''jsonb'', null::jsonb)';
                                END IF;
                            END
                            $BODY$;

                            ALTER FUNCTION public.fn_get_bulist(bigint, boolean, boolean, text, anyelement)
                                OWNER TO youtilitydba;

    """
                            
    }
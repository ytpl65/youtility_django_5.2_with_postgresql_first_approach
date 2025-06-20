def get_query(q):
    query = {
        'get_web_caps_for_client':          '''
                                                WITH RECURSIVE cap(id, capsname, capscode, parent_id, cfor, depth, path, xpath) AS (
                                                SELECT id, capsname, capscode, parent_id, cfor, 1::INT AS depth, capability.capscode::TEXT AS path, capability.id::text as xpath
                                                FROM capability
                                                WHERE id = 1 and cfor='WEB'
                                                UNION ALL
                                                SELECT ch.id, ch.capsname, ch.capscode, ch.parent_id, ch.cfor, rt.depth + 1 AS depth, (rt.path || '->' || ch.capscode::TEXT), (xpath||'>'||ch.id||rt.depth + 1)
                                                FROM capability ch INNER JOIN cap rt ON rt.id = ch.parent_id)
                                                select * from cap
                                                order by xpath
                                            ''',
        'get_childrens_of_bt':              '''
                                                WITH RECURSIVE cap(id, bucode, parent_id, butree, depth, path, xpath) AS (
                                                SELECT id,  bucode, parent_id, butree, 1::INT AS depth, bt.bucode::TEXT AS path, bt.id::text as xpath
                                                FROM bt
                                                WHERE id = %s
                                                UNION ALL
                                                SELECT ch.id, ch.bucode, ch.parent_id, ch.butree,  rt.depth + 1 AS depth, (rt.path || '->' || ch.bucode::TEXT), (xpath||'>'||ch.id||rt.depth + 1)
                                                FROM bt ch INNER JOIN cap rt ON rt.id = ch.parent_id)
                                                select * from cap
                                                order by xpath
                                            ''',
        'tsitereportdetails':               '''
                                                WITH RECURSIVE nodes_cte(id, parent_id, jobdesc, people_id, qset_id, plandatetime, cdtz, depth, path, top_parent, pseqno, bu_id)
                                                as ( 
                                                SELECT id, jobneed.parent_id, jobdesc, people_id, qset_id, plandatetime, jobneed.cdtz, 1::INT AS depth, qset_id::TEXT AS path,
                                                id as top_parent, seqno as pseqno, jobneed.bu_id
                                                FROM jobneed  
                                                WHERE jobneed.identifier = 'SITEREPORT' AND jobneed.parent_id=-1 AND 
                                                id<>-1 AND id= '1' 
                                                UNION ALL SELECT c.id, c.parent_id, c.jobdesc, c.people_id, c.qset_id, c.plandatetime, c.cdtz, p.depth + 1 
                                                AS depth, (p.path || '->' || c.id::TEXT) as path, c.parent_id as top_parent, seqno as pseqno, c.bu_id FROM nodes_cte AS p, jobneed AS
                                                c  WHERE c.identifier='SITEREPORT' AND c.parent_id = p.id )
                                                SELECT DISTINCT jobneed.jobdesc, jobneed.pseqno, jnd.seqno as cseqno, jnd.question_id, jnd.answertype, jnd.min, jnd.max, jnd.options,
                                                jnd.answer, jnd.alerton, jnd.ismandatory, q.quesname, q.answertype FROM nodes_cte as jobneed 
                                                LEFT JOIN jobneed_details as jnd ON jnd.jobneed_id = jobneed.id 
                                                LEFT JOIN question q ON jnd.question_id = q.id where jnd.answertype='Question Type' AND jobneed.parent_id <> -1 
                                                ORDER BY pseqno asc, jobdesc asc, pseqno, cseqno asc
                                            ''',
        'sitereportlist':                   '''
                                                SELECT * FROM(
                                                SELECT DISTINCT jobneed.id, jobneed.plandatetime, jobneed.jobdesc, people.peoplename, 
                                                CASE WHEN (jobneed.othersite!='' or upper(jobneed.othersite)!='NONE') THEN 'other location [ ' ||jobneed.othersite||' ]' ELSE bt.buname END AS buname,
                                                jobneed.qset_id, jobneed.jobstatus AS jobstatusname, ST_AsText(jobneed.gpslocation) as gpslocation, bt.pdist, count(attachment.owner) AS att,
                                                jobneed.bu_id, jobneed.remarks 
                                                FROM jobneed 
                                                INNER JOIN people ON jobneed.people_id = people.id 
                                                INNER JOIN bt ON jobneed.bu_id = bt.id 
                                                LEFT JOIN attachment ON jobneed.uuid::text = attachment.owner
                                                WHERE jobneed.parent_id=1 AND 1 = 1 AND bt.id IN %s 
                                                AND jobneed.identifier='SITEREPORT'
                                                AND jobneed.plandatetime >= %s AND jobneed.plandatetime <= %s 
                                                GROUP BY jobneed.id, buname,  bt.pdist, people.peoplename, jobstatusname, jobneed.plandatetime)
                                                jobneed 
                                                WHERE 1 = 1 ORDER BY plandatetime desc OFFSET 0 LIMIT 250
                                            ''',

        'incidentreportlist':                '''
                                                SELECT * FROM(
                                                SELECT DISTINCT jobneed.id, jobneed.plandatetime, jobneed.jobdesc,  jobneed.bu_id, 
                                                case when (jobneed.othersite!='' or upper(jobneed.othersite)!='NONE') then 'other location [ ' ||jobneed.othersite||' ]' else bt.buname end  As buname,
                                                people.peoplename, jobneed.jobstatus as jobstatusname, count(attachment.owner) as att, ST_AsText(jobneed.gpslocation) as gpslocation
                                                FROM jobneed 
                                                INNER JOIN people ON jobneed.people_id=people.id 
                                                INNER JOIN bt ON jobneed.bu_id=bt.id 
                                                LEFT JOIN attachment ON jobneed.uuid::text = attachment.owner 
                                                WHERE jobneed.parent_id=1 AND jobneed.identifier = 'INCIDENTREPORT' 
                                                AND bt.id IN %s 
                                                AND jobneed.plandatetime >= %s AND jobneed.plandatetime <= %s
                                                AND attachment.attachmenttype = 'ATTACHMENT'
                                                GROUP BY jobneed.id, buname, people.peoplename, jobstatusname, jobneed.plandatetime)
                                                jobneed
                                                where 1=1 ORDER BY plandatetime desc OFFSET 0 LIMIT 250
                                            ''',
        'workpermitlist':                   '''
                                            SELECT * FROM( 
                                            SELECT DISTINCT workpermit.id, workpermit.cdtz,workpermit.seqno, qset.qsetname as wptype, workpermit.wpstatus, workpermit.workstatus,
                                            workpermit.bu_id,  bt.buname  As buname,
                                            pb.peoplename, p.peoplename as user, count(attachment.uuid) as att

                                            FROM workpermit INNER JOIN people ON workpermit.muser_id=people.id
                                            INNER JOIN people p ON workpermit.cuser_id=p.id
                                            INNER JOIN people pb ON workpermit.approvedby_id=pb.id
                                            INNER JOIN bt ON workpermit.bu_id=bt.id
                                            INNER JOIN questionset qset ON workpermit.wptype_id=qset.id
                                            LEFT JOIN attachment ON workpermit.uuid::text=attachment.owner 

                                            WHERE workpermit.parent_id=1 
                                            AND 1=1 AND attachment.attachmenttype = 'ATTACHMENT'
                                            AND workpermit.bu_id IN (%s) 
                                            AND workpermit.parent_id='1' 
                                            AND workpermit.id != '1' 
                                            AND workpermit.cdtz >= now() - interval '100 day' 
                                            AND workpermit.cdtz <= now()
                                            GROUP BY workpermit.id, buname, people.peoplename, qset.qsetname, workpermit.wpstatus, workpermit.workstatus,pb.peoplename, p.peoplename)workpermit 
                                            WHERE 1=1 ORDER BY cdtz desc
                                            ''',
    'get_ticketlist_for_escalation':        '''
                                            SELECT DISTINCT *,ticket.cdtz + INTERVAL '1 minute' * esclation.calcminute as exp_time FROM 
                                            
                                            (SELECT ticket.id, ticket.ticketno, ticketdesc, ticket.comments, ticket.cdtz, ticket.mdtz, ticket.ticketcategory_id as tescalationtemplate, ticket.status, ticket.bu_id as tbu, 
                                            people.peoplename, pgroup.groupname, ticket.assignedtopeople_id as assignedtopeople, 
                                            ticket.assignedtogroup_id as assignedtogroup,ticket.ticketlog,ticket.level, creator.id as cuser_id,  creator.peoplename as who FROM ticket  
                                            LEFT JOIN people ON (ticket.assignedtopeople_id = people.id) 
                                            LEFT JOIN people  creator ON (ticket.cuser_id = people.id)
                                            LEFT JOIN pgroup ON (ticket.assignedtogroup_id = pgroup.id)
                                            WHERE (NOT (status IN ('CLOSE', 'CANCEL') AND status IS NOT NULL))) AS ticket,
                                            
                                            (SELECT escalationmatrix.id as esid, escalationmatrix.level as eslevel, escalationmatrix.frequency, escalationmatrix.frequencyvalue, escalationmatrix.bu_id, 
                                            escalationmatrix.escalationtemplate_id,  escalationmatrix.assignedgroup_id as escgrpid, escalationmatrix.assignedperson_id as escpersonid, 
                                            pp.peoplename as escpeoplename, pg.groupname as escgroupname,
                                            CASE WHEN escalationmatrix.frequency = 'MINUTE' THEN (CAST(escalationmatrix.frequencyvalue AS integer)) 
                                            WHEN escalationmatrix.frequency = 'HOUR' THEN (CAST(escalationmatrix.frequencyvalue AS integer) * 60) 
                                            WHEN escalationmatrix.frequency = 'DAY' THEN ((CAST(escalationmatrix.frequencyvalue AS integer) * 24) * 60)
                                            WHEN escalationmatrix.frequency = 'WEEK' THEN (((CAST(escalationmatrix.frequencyvalue AS integer) * 7) * 24) * 60) ELSE NULL END AS calcminute 
                                            
                                            FROM escalationmatrix 
                                            LEFT JOIN people pp ON escalationmatrix.assignedperson_id=pp.id 
                                            LEFT JOIN pgroup pg ON escalationmatrix.assignedgroup_id=pg.id ) AS esclation
                                            
                                            WHERE (ticket.level+1) = esclation.eslevel  AND ticket.tescalationtemplate = esclation.escalationtemplate_id AND ticket.cdtz + INTERVAL  '1 minute' * esclation.calcminute < now()
                                            ''',
    'ticketmail':                           '''
                                            SELECT ticket.id, ticket.ticketno, ticket.ticketlog, ticket.comments, ticket.ticketdesc, ticket.cdtz, 
                                             ticket.status,
                                             em.level, em.frequency, em.frequencyvalue, em.body, em.notify,  em.assignedperson_id as escperson,em.assignedgroup_id as escgrp, 
                                             CASE WHEN em.frequency = 'MINUTE' THEN ticket.cdtz + INTERVAL '1 minute' * em.frequencyvalue  
                                                 WHEN em.frequency = 'HOUR'   THEN ticket.cdtz + INTERVAL '1 minute' * em.frequencyvalue * 60 
                                                 WHEN em.frequency = 'DAY'    THEN ticket.cdtz + INTERVAL '1 minute' * em.frequencyvalue * 24 * 60 
                                                 WHEN em.frequency = 'WEEK'   THEN ticket.cdtz + INTERVAL '1 minute' * em.frequencyvalue * 07 * 24 * 60 
                                             END exptime, 
                                             ( SELECT emnext.frequencyvalue || ' ' || emnext.frequency FROM escalationmatrix AS emnext 
                                             WHERE ticket.ticketcategory_id=emnext.escalationtemplate_id AND emnext.level=ticket.level + 1) AS next_escalation, 
                                             people.peoplename, people.email as peopleemail, creator.id as creatorid, creator.email as creatoremail,  
                                             pgroup.groupname ,ticket.assignedtogroup_id,  ticket.priority, ticket.mdtz,
                                             ticket.assignedtopeople_id, ticket.ticketcategory_id, tcattype.taname as tescalationtemplate , 
                                             modifier.id as modifierid, modifier.peoplename as  modifiername, modifier.email as modifiermail , 
                                             (select array_to_string(ARRAY(select email from people where id in(select unnest(string_to_array(em.notify, ','))::bigint)),',') ) as notifyemail, 
                                             (select array_to_string(ARRAY(select email from people where id in(select people_id from pgbelonging where pgroup_id=pgroup.id )),',') ) as pgroupemail 
                                             FROM ticket 
                                             LEFT JOIN people              ON ticket.assignedtopeople_id=people.id 
                                             LEFT JOIN pgroup              ON ticket.assignedtogroup_id=pgroup.id 
                                             LEFT JOIN people creator      ON ticket.cuser_id=creator.id
                                             LEFT  JOIN people modifier    ON ticket.muser_id=modifier.id 
                                             INNER JOIN typeassist tcattype ON ticket.ticketcategory_id = tcattype.id 
                                             LEFT JOIN escalationmatrix em ON ticket.ticketcategory_id = em.escalationtemplate_id  AND em.level=(ticket.level ) 
                                             WHERE ticket.id = %s;
                                            ''',
    'tasksummary':                          '''
                                            WITH timezone_setting AS (
                                                SELECT %s::text AS timezone
                                            )

                                            SELECT * , 
                                                coalesce(round(x.tot_completed::numeric/nullif(x.tot_scheduled::numeric,0)*100,2),0) as perc
                                            FROM (
                                                SELECT
                                                bu.id,
                                                bu.buname as site,
                                                (jobneed.plandatetime AT TIME ZONE tz.timezone)::DATE as planneddate,
                                                count(jobneed.id)::numeric as tot_task,
                                                count(case when jobneed.jobtype = 'SCHEDULE' then jobneed.jobtype end)::numeric as tot_scheduled,
                                                count(case when jobneed.jobtype = 'ADHOC' then jobneed.jobtype end)::numeric as tot_adhoc,
                                                count(case when jobneed.jobtype = 'SCHEDULE' and jobneed.jobstatus = 'ASSIGNED' then jobneed.jobstatus end)::numeric as tot_pending,
                                                count(case when jobneed.jobtype = 'SCHEDULE' and jobneed.jobstatus = 'AUTOCLOSED' then jobneed.jobstatus end)::numeric as tot_closed,
                                                count(case when jobneed.jobtype = 'SCHEDULE' and jobneed.jobstatus = 'COMPLETED' then jobneed.jobstatus end)::numeric as tot_completed
                                                FROM jobneed
                                                INNER JOIN bt bu ON bu.id=jobneed.bu_id
                                                CROSS JOIN timezone_setting tz
                                                WHERE
                                                jobneed.identifier='TASK' AND
                                                jobneed.id <> 1 AND
                                                bu.id <> 1 AND
                                                jobneed.bu_id IN (SELECT unnest(string_to_array(%s, ',')::integer[]))  AND
                                                (jobneed.plandatetime AT TIME ZONE tz.timezone)::DATE BETWEEN %s AND %s
                                                GROUP BY bu.id, bu.buname, (jobneed.plandatetime AT TIME ZONE tz.timezone)::DATE
                                                ORDER BY bu.buname, (jobneed.plandatetime AT TIME ZONE tz.timezone)::DATE desc
                                            ) x;
                                            ''',
    'asset_status_period':                  '''
                                            SELECT asset_id, (SUM(standby_duration) || ' seconds')::interval  AS total_duration
                                            FROM (
                                                SELECT asset_id,
                                                    EXTRACT(EPOCH FROM (
                                                        lead(cdtz) OVER (PARTITION BY asset_id ORDER BY cdtz) - cdtz
                                                    )) AS standby_duration  -- This will give the duration in seconds
                                                FROM assetlog
                                                WHERE (oldstatus = %s OR newstatus = %s) and asset_id = %s
                                            ) sub
                                            GROUP BY asset_id;
                                            ''',
    'all_asset_status_duration':            '''
                                            WITH status_periods AS (
                                            SELECT
                                                asset_id,
                                                newstatus,
                                                asset.assetname as assetname,
                                                assetlog.cdtz AS period_start,
                                                COALESCE(LEAD(assetlog.cdtz) OVER (PARTITION BY asset_id ORDER BY assetlog.cdtz), CURRENT_TIMESTAMP) AS period_end
                                            FROM assetlog
                                            INNER JOIN asset on asset_id = asset.id
                                            where assetlog.client_id = %s and assetlog.bu_id = %s
                                            ),
                                            status_durations AS (
                                            SELECT
                                                asset_id,
												assetname,
                                                newstatus,
                                                SUM(EXTRACT(EPOCH FROM (period_end - period_start))) AS duration_seconds,
                                                MAX(period_end) AS max_period_end
                                            FROM status_periods
                                            GROUP BY asset_id, assetname, newstatus
                                            )
                                            SELECT
                                            asset_id,
                                            assetname,
                                            newstatus,
                                            duration_seconds,
                                            CASE 
                                                WHEN max_period_end = CURRENT_TIMESTAMP THEN 'till_now'
                                                ELSE CAST(INTERVAL '1 second' * duration_seconds AS VARCHAR)
                                            END AS duration_interval
                                            FROM status_durations
                                            ORDER BY asset_id, newstatus
                                            ''',
    'all_asset_status_duration_count':      '''
                                            SELECT COUNT(*) FROM (
                                                 WITH status_periods AS (
                                            SELECT
                                                asset_id,
                                                newstatus,
                                                asset.assetname as assetname,
                                                assetlog.cdtz AS period_start,
                                                COALESCE(LEAD(assetlog.cdtz) OVER (PARTITION BY asset_id ORDER BY assetlog.cdtz), CURRENT_TIMESTAMP) AS period_end
                                            FROM assetlog
                                            INNER JOIN asset on asset_id = asset.id
                                            where assetlog.client_id = %s and assetlog.bu_id = %s
                                            ),
                                            status_durations AS (
                                            SELECT
                                                asset_id,
												assetname,
                                                newstatus,
                                                SUM(EXTRACT(EPOCH FROM (period_end - period_start))) AS duration_seconds,
                                                MAX(period_end) AS max_period_end
                                            FROM status_periods
                                            GROUP BY asset_id, assetname, newstatus
                                            )
                                            SELECT
                                            asset_id,
                                            assetname,
                                            newstatus,
                                            duration_seconds,
                                            CASE 
                                                WHEN max_period_end = CURRENT_TIMESTAMP THEN 'till_now'
                                                ELSE CAST(INTERVAL '1 second' * duration_seconds AS VARCHAR)
                                            END AS duration_interval
                                            FROM status_durations
                                            ORDER BY asset_id, newstatus
                                            ) AS SUBQUERY
                                            ''',

    }
    return query.get(q)
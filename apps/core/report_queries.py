def get_query(query):
    return {
        "TASKSUMMARY": 
            '''
            WITH timezone_setting AS (
            SELECT '{timezone}'::text AS timezone
        )

        SELECT *,
            coalesce(round(x."Total Completed"::numeric/nullif(x."Total Scheduled"::numeric,0)*100,2),0) as "Percentage"
        FROM (
            SELECT
                bu.buname as "Site",
                (jobneed.plandatetime AT TIME ZONE tz.timezone)::DATE as "Planned Date",
                count(jobneed.id)::numeric as "Total Tasks",
                count(case when jobneed.jobtype = 'SCHEDULE' then jobneed.jobtype end)::numeric as "Total Scheduled",
                count(case when jobneed.jobtype = 'ADHOC' then jobneed.jobtype end)::numeric as "Total Adhoc",
                count(case when jobneed.jobtype = 'SCHEDULE' and jobneed.jobstatus = 'ASSIGNED' then jobneed.jobstatus end)::numeric as "Total Pending",
                count(case when jobneed.jobtype = 'SCHEDULE' and jobneed.jobstatus = 'AUTOCLOSED' then jobneed.jobstatus end)::numeric as "Total Closed",
                count(case when jobneed.jobtype = 'SCHEDULE' and jobneed.jobstatus = 'COMPLETED' then jobneed.jobstatus end)::numeric as "Total Completed",
                count(jobneed.id)::numeric - count(case when jobneed.jobtype = 'SCHEDULE' and jobneed.jobstatus = 'COMPLETED' then jobneed.jobstatus end)::numeric as "Not Performed"
            FROM jobneed
            INNER JOIN bt bu ON bu.id=jobneed.bu_id
            CROSS JOIN timezone_setting  AS tz
            WHERE
                jobneed.identifier='TASK' AND
                jobneed.id <> 1 AND
                bu.id <> 1 AND
                jobneed.bu_id IN (SELECT unnest(string_to_array('{siteids}', ',')::integer[]))  AND
                (jobneed.plandatetime AT TIME ZONE tz.timezone) BETWEEN '{from}' AND '{upto}'
            GROUP BY bu.id, bu.buname, (jobneed.plandatetime AT TIME ZONE tz.timezone)::DATE
            ORDER BY bu.buname, (jobneed.plandatetime AT TIME ZONE tz.timezone)::DATE desc
        ) as x
            ''',
        "TOURSUMMARY":
            '''
            WITH timezone_setting AS (
                SELECT '{timezone}' ::text AS timezone
            )

            SELECT * ,
                coalesce(round(x."Total Completed"::numeric/nullif(x."Total Tours"::numeric,0)*100,2),0) as "Percentage"
            FROM (
                SELECT
                bu.id,
                bu.buname as "Site",
                (jobneed.plandatetime AT TIME ZONE tz.timezone)::DATE as "Date",
                count(jobneed.id)::numeric as "Total Tours",
            count(case when jobneed.jobtype='SCHEDULE' then jobneed.jobtype end) as "Total Scheduled",
            count(case when jobneed.jobtype='ADHOC' then jobneed.jobtype end) as "Total Adhoc",
            count(case when jobneed.jobstatus='ASSIGNED' then jobneed.jobstatus end) as "Total Pending",
            count(case when jobneed.jobstatus='AUTOCLOSED' then jobneed.jobstatus end) as "Total Closed",
            count(case when jobneed.jobstatus='COMPLETED' then jobneed.jobstatus end) as "Total Completed"

                FROM jobneed
                INNER JOIN bt bu ON bu.id=jobneed.bu_id
                CROSS JOIN timezone_setting tz
                WHERE
                jobneed.identifier='INTERNALTOUR'
                AND jobneed.id <> 1
                AND bu.id <> 1
                AND jobneed.bu_id IN (SELECT unnest(string_to_array('{siteids}', ',')::integer[]))  
                AND (jobneed.plandatetime AT TIME ZONE tz.timezone) BETWEEN '{from}' AND '{upto}'
                GROUP BY bu.id, bu.buname, (jobneed.plandatetime AT TIME ZONE tz.timezone)::DATE
                ORDER BY bu.buname, (jobneed.plandatetime AT TIME ZONE tz.timezone)::DATE desc
            ) as x
            ''',
        "LISTOFTASKS":
            '''
            WITH timezone_setting AS (
                SELECT '{timezone}'::text AS timezone
            )
                SELECT
                bu.id,
                bu.buname as "Site",
                (jobneed.plandatetime AT TIME ZONE tz.timezone) as "Planned Date Time",
            jobneed.id as jobneedid,
            jobneed.identifier,
            jobneed.jobdesc as "Description",
                case
                    when jobneed.people_id <> 1 then people.peoplename
                    when jobneed.pgroup_id <> 1 then pgroup.groupname
                    else 'NONE' end as "Assigned To",
            jobneed.people_id assignedto,
            jobneed.jobtype,
            jobneed.jobstatus as "Status",
            jobneed.asset_id,
            performedpeople.peoplename as "Performed By",
            jobneed.qset_id as qsetname,
            (jobneed.expirydatetime AT TIME ZONE tz.timezone)  as "Expired Date Time" ,
            jobneed.gracetime as "Gracetime",
            jobneed.scantype,
            jobneed.receivedonserver,
            jobneed.priority,
            (jobneed.starttime AT TIME ZONE tz.timezone) as starttime ,
            (jobneed.endtime AT TIME ZONE tz.timezone) as endtime,
            jobneed.gpslocation,
            jobneed.qset_id,
            jobneed.remarks,
            asset.assetname as "Asset",
            questionset.qsetname as "Question Set",
            people.peoplename
                FROM jobneed
                INNER JOIN bt bu ON bu.id=jobneed.bu_id
            INNER JOIN asset ON asset.id=jobneed.asset_id
            INNER JOIN questionset ON questionset.id=jobneed.qset_id
            INNER JOIN people on jobneed.people_id=people.id
            INNER JOIN people performedpeople on jobneed.performedby_id=performedpeople.id
            inner join pgroup on pgroup.id=jobneed.pgroup_id
                CROSS JOIN timezone_setting tz
                WHERE jobneed.identifier='TASK' --AND jobneed.jobstatus='COMPLETED'
            AND jobneed.id <> 1 and jobneed.parent_id = 1
            AND bu.id <> 1
            AND jobneed.bu_id IN (SELECT unnest(string_to_array('{siteids}', ',')::integer[]))  
            AND (jobneed.plandatetime AT TIME ZONE tz.timezone) BETWEEN '{from}' AND '{upto}'
            ORDER BY bu.buname, (jobneed.plandatetime AT TIME ZONE tz.timezone)::DATE desc
            ''',
        "LISTOFTOURS":
            '''
            WITH timezone_setting AS (
                SELECT '{timezone}' ::text AS timezone
            )
                SELECT
                --bu.id,
				client_table.buname AS "Client",
                bu.buname as "Site",
				jobneed.jobdesc as "Tour/Route",
                (jobneed.plandatetime AT TIME ZONE tz.timezone)::timestamp as "Planned Datetime",
				(jobneed.expirydatetime AT TIME ZONE tz.timezone)::timestamp as "Expiry Datetime",
            case
                    when jobneed.people_id <> 1 then people.peoplename
                    when jobneed.pgroup_id <> 1 then pgroup.groupname
                    else 'NONE' end as "Assigned To",
            jobneed.jobtype as "JobType",
            jobneed.jobstatus as "Status",
			(jobneed.endtime AT TIME ZONE tz.timezone)::timestamp as "Performed On",
            performedpeople.peoplename as "Performed By",
			CASE 
				WHEN jobneed.other_info ->> 'istimebound' = 'true' THEN 'Static'
				ELSE 'Dynamic' 
			END as "Is Time Bound"
                FROM jobneed
                INNER JOIN bt bu ON bu.id=jobneed.bu_id
                INNER JOIN bt AS client_table ON jobneed.client_id = client_table.id
            INNER JOIN asset ON asset.id=jobneed.asset_id
            INNER JOIN questionset ON questionset.id=jobneed.qset_id
            INNER JOIN people on jobneed.people_id=people.id
            INNER JOIN people performedpeople on jobneed.performedby_id=performedpeople.id
            inner join pgroup on pgroup.id=jobneed.pgroup_id
                CROSS JOIN timezone_setting tz
                WHERE jobneed.identifier='INTERNALTOUR'
            AND jobneed.id <> 1 and jobneed.parent_id = 1
            AND bu.id <> 1
            AND jobneed.bu_id IN (SELECT unnest(string_to_array('{siteids}', ',')::integer[]))
            AND (jobneed.plandatetime AT TIME ZONE tz.timezone) BETWEEN '{from}' AND '{upto}'
            ORDER BY bu.buname, (jobneed.plandatetime AT TIME ZONE tz.timezone)::DATE desc
            ''',
        "PPMSUMMARY":
            '''
            WITH timezone_setting AS (
                SELECT '{timezone}' ::text AS timezone
            )
            SELECT
            assettype as "Asset Type",
            count(assettype) as "Total PPM Scheduled",
            sum(case when ((endtime AT TIME ZONE tz.timezone) <= (expirydatetime AT TIME ZONE tz.timezone) and jobstatus='COMPLETED') then 1 else 0 end) as "Completed On Time",
            sum(case when ((endtime AT TIME ZONE tz.timezone) > (expirydatetime AT TIME ZONE tz.timezone) and jobstatus='COMPLETED') then 1 else 0 end) as "Completed After Schedule",
            sum(case when jobstatus = 'AUTOCLOSED' then 1 else 0 end) as "PPM Missed",
            round((sum(case when ((endtime AT TIME ZONE tz.timezone) <= (expirydatetime AT TIME ZONE tz.timezone) and jobstatus='COMPLETED') then 1 else 0 end)::numeric/ NULLIF(count(jobstatus)::numeric,0)) * 100,2) as "Percentage",
            buname as "Site Name"
            FROM (SELECT jobneed.id,
                atype.taname AS assettype,
                jobneed.jobdesc,
                jobneed.plandatetime,
                jobneed.endtime,
                jobneed.expirydatetime,
                jobneed.jobstatus,
                jobneed.identifier,
                bu.buname,
                jobneed.bu_id as buid,
                jobneed.people_id as peopleid
            FROM jobneed
                JOIN people ON jobneed.people_id = people.id
                LEFT JOIN asset ON jobneed.asset_id = asset.id
                JOIN bt bu ON jobneed.bu_id = bu.id
                LEFT JOIN typeassist atype ON atype.id = asset.type_id
            WHERE jobneed.parent_id = '1'::integer  
            AND jobneed.plandatetime >= (now() - '60 days'::interval) AND jobneed.plandatetime <= now()
            AND jobneed.identifier='PPM') as jobneed
            cross join timezone_setting tz
            WHERE 1=1
            and buid IN (SELECT unnest(string_to_array('{siteids}', ',')::integer[])) 
            AND (jobneed.plandatetime AT TIME ZONE tz.timezone) BETWEEN '{from}' AND '{upto}'
            GROUP BY buname, assettype

            ''',
        "LISTOFTICKETS":
            '''
            WITH timezone_setting AS (
                SELECT '{timezone}' ::text AS timezone
            )

            SELECT
                t.id AS "Ticket No",
                t.cdtz AT TIME ZONE tz.timezone AS "Created On",
                t.mdtz AT TIME ZONE tz.timezone AS "Modied On",
                t.status as "Status",
                t.ticketdesc as "Description",
                t.priority as "Priority",
                ta.taname AS "Ticket Category",
                CASE
                    WHEN t.status IN ('RESOLVED', 'CLOSED') THEN TO_CHAR((t.mdtz - t.cdtz), 'HH24:MI:SS')
                    WHEN t.status = 'CANCELLED' THEN 'NA'
                    ELSE '00:00:00'
                END AS "TAT",
                CASE
                    WHEN t.status NOT IN ('RESOLVED', 'CLOSED', 'CANCELLED') THEN TO_CHAR((NOW() - t.cdtz), 'HH24:MI:SS')
                    WHEN t.status = 'CANCELLED' THEN 'NA'
                    ELSE '00:00:00'
                END AS tl,
                CASE
                    WHEN t.assignedtogroup_id IS NULL OR t.assignedtogroup_id = 1 THEN p1.peoplename
                    ELSE p2.groupname
                END AS "Assigned To",
                p3.peoplename AS "Created By",
                p4.peoplename AS modified_by
            FROM
                ticket t
            LEFT JOIN
                people p1 ON t.assignedtopeople_id = p1.id
            LEFT JOIN
                pgroup p2 ON t.assignedtogroup_id = p2.id
            LEFT JOIN
                people p3 ON t.cuser_id = p3.id
            LEFT JOIN
                people p4 ON t.muser_id = p4.id
            LEFT JOIN
                typeassist ta ON t.ticketcategory_id = ta.id
            CROSS JOIN timezone_setting tz
            WHERE
            NOT (t.assignedtogroup_id IS NULL AND t.assignedtopeople_id IS NULL)
                AND t.bu_id IN (SELECT unnest(string_to_array('{siteids}', ',')::integer[])) 
                
                AND NOT (t.assignedtogroup_id = 1 AND t.assignedtopeople_id = 1)
                AND NOT ((t.cuser_id = 1 or t.cuser_id IS NULL)  AND (t.muser_id = 1 or t.muser_id IS NULL))
                AND (t.cdtz AT TIME ZONE tz.timezone) BETWEEN '{from}' AND '{upto}'
            ''',
        "WORKORDERLIST":
            '''
            WITH timezone_setting AS (
                SELECT '{timezone}' ::text AS timezone
            )

            SELECT wom.id as "wo_id",
            wom.cdtz AT TIME ZONE tz.timezone as "Created On",
            wom.description as "Description", 
            wom.plandatetime AT TIME ZONE tz.timezone as "Planned Date Time", 
            wom.endtime as "Completed On",
            array_to_string(wom.categories, ',') as "Categories", 
            p.peoplename as "Created By", 
            wom.workstatus as "Status", 
            v.name as "Vendor Name", INITCAP(priority) as "Priority", bu.buname as "Site"
            from wom
            inner join people p on p.id = wom.cuser_id
            inner join vendor v  on v.id  = wom.vendor_id
            inner join bt bu on bu.id = wom.bu_id
            CROSS JOIN timezone_setting tz
            where NOT(wom.vendor_id is NULL) AND vendor_id <> 1
            AND wom.bu_id <> 1 AND wom.qset_id <> 1
            AND wom.bu_id IN (SELECT unnest(string_to_array('{siteids}', ',')::integer[]))
            AND (wom.cdtz AT TIME ZONE tz.timezone) BETWEEN '{from}' AND '{upto}'
            GROUP BY wom.id,bu.id, bu.buname, p.peoplename, v.name, tz.timezone,(wom.plandatetime AT TIME ZONE tz.timezone)::DATE
            ORDER BY bu.buname, (wom.plandatetime AT TIME ZONE tz.timezone)::DATE desc
            ''',
        'SITEREPORT':
            '''
            WITH timezone_setting AS (
                SELECT '{timezone}' ::text AS timezone
            ),
            jnd_p AS (
                SELECT 
                    id AS ct_id,
                    jobdesc AS ct_jobdesc,
                    qset_id AS ct_qset_id,
                    bu_id AS ct_bu_id,
                    asset_id AS ct_asset_id,
                    starttime AT TIME ZONE tz.timezone AS ct_starttime,
                    endtime AT TIME ZONE tz.timezone AS ct_endtime,
                    performedby_id AS ct_performedby_id,
                    plandatetime AT TIME ZONE tz.timezone AS ct_plandatetime
                FROM 
                    jobneed
                CROSS JOIN 
                    timezone_setting AS tz
                WHERE 
                    parent_id IS NOT NULL 
                    AND parent_id = 1
                    AND client_id = {clientid}
                    AND sgroup_id IN (SELECT unnest(string_to_array('{sgroupids}', ',')::integer[]))
                    AND (jobneed.plandatetime AT TIME ZONE tz.timezone) BETWEEN '{from}' AND '{upto}'
            )

            SELECT 
                --jnd.jobdesc AS jobdesc,
                bt.solid as"SOL ID",
                Max(pgroup.groupname) as "ROUTE NAME",
                bt.bucode as "SITE CODE", 
                bt.buname as "SITE NAME",
                --Max(qset.qsetname) AS qsetname,
                --Max(asset.assetname) AS assetname,
                --jnd.starttime AT TIME ZONE tz.timezone AS starttime,
                --jnd.endtime AT TIME ZONE tz.timezone AS endtime,
                (jnd.starttime AT TIME ZONE tz.timezone)::DATE AS "DATE OF VISIT",
                Max(to_char((jnd.starttime AT TIME ZONE tz.timezone),'HH24:MI:SS')) AS "TIME OF VISIT",
                Max(ST_X(ST_PointFromText(ST_AsText(jnd.gpslocation), 4326))) AS "LONGITUDE",
                Max(ST_Y(ST_PointFromText(ST_AsText(jnd.gpslocation), 4326))) AS "LATITUDE",
                people.peoplecode AS "RP ID",
                people.peoplename AS "RP OFFICER",
                people.mobno AS "CONTACT",
                Max(bt.bupreferences->>'address') AS "SITE ADDRESS",
                Max(bt.bupreferences->'address2'->>'state') AS "STATE",
                -- Add your CASE statements here for each condition 
                -- Example:
            Max(CASE WHEN upper(question.quesname)='FASCIA WORKING' THEN jnds.answer END) AS "FASCIA WORKING",
            Max(CASE WHEN upper(question.quesname)='LOLLY POP WORKING' THEN jnds.answer END) AS "LOLLY POP WORKING",
            Max(CASE WHEN upper(question.quesname)='ATM MACHINE COUNT' THEN jnds.answer END) AS "ATM MACHINE COUNT",
            Max(CASE WHEN upper(question.quesname)='AC IN ATM COOLING' THEN jnds.answer END) AS "AC IN ATM COOLING",
            Max(CASE WHEN upper(question.quesname)='ATM BACK ROOM LOCKED' THEN jnds.answer END) AS "ATM BACK ROOM LOCKED",
            Max(CASE WHEN upper(question.quesname)='UPS ROOM BEHIND ATM LOBBY ALL SAFE' THEN jnds.answer END) AS "UPS ROOM BEHIND ATM LOBBY ALL SAFE",
            Max(CASE WHEN upper(question.quesname)='BRANCH SHUTTER DAMAGED' THEN jnds.answer END) AS "BRANCH SHUTTER DAMAGED",
            Max(CASE WHEN upper(question.quesname)='BRANCH PERIPHERY ROUND TAKEN' THEN jnds.answer END) AS "BRANCH PERIPHERY ROUND TAKEN",
            Max(CASE WHEN upper(question.quesname)='AC ODU AND COPPER PIPE INTACT' THEN jnds.answer END) AS "AC ODU AND COPPER PIPE INTACT",
            Max(CASE WHEN upper(question.quesname)='ANY WATER LOGGING OR FIRE IN VICINITY' THEN jnds.answer END) AS "ANY WATER LOGGING OR FIRE IN VICINITY",
            Max(CASE WHEN upper(question.quesname)='FE AVAILABLE IN ATM LOBBY' THEN jnds.answer END) AS "FE AVAILABLE IN ATM LOBBY",
            Max(CASE WHEN upper(question.quesname)='DG DOOR LOCKED' THEN jnds.answer END) AS "DG DOOR LOCKED",
            Max(CASE WHEN upper(question.quesname)='DAMAGE TO ATM LOBBY' THEN jnds.answer END) AS "DAMAGE TO ATM LOBBY",
            Max(CASE WHEN upper(question.quesname)='ANY OTHER OBSERVATION' THEN jnds.answer END) AS "ANY OTHER OBSERVATION"

            FROM 
                jnd_p
            INNER JOIN 
                jobneed AS jnd ON jnd_p.ct_id=jnd.parent_id
            INNER JOIN 
                jobneeddetails jnds ON jnd.id=jnds.jobneed_id
            INNER JOIN 
                question ON question.id=jnds.question_id
            INNER JOIN 
                bt ON bt.id=jnd.bu_id
            INNER JOIN 
                asset ON asset.id=jnd.asset_id
            INNER JOIN 
                questionset AS qset ON qset.id=jnd.qset_id
            INNER JOIN 
                people ON people.id=jnd.performedby_id
            LEFT JOIN 
                pgroup ON pgroup.id=jnd.sgroup_id
            CROSS JOIN 
                timezone_setting tz
            WHERE 
                upper(qset.qsetname)='SITE REPORT'
                AND jnds.answer IS NOT NULL

            GROUP BY 
                jnd.jobdesc, 
                bt.solid, 
                bt.bucode, 
                bt.buname, 
                people.peoplecode, 
                people.peoplename, 
                people.mobno,
                jnd.starttime, 
                jnd.endtime, 
                jnd_p.ct_plandatetime, 
                tz.timezone;
            ''',
        'SITEVISITREPORT':
            '''
            WITH timezone_setting AS (
                SELECT %s::text AS timezone
            )

            SELECT 
                jn.plandatetime as plandatetime,
                jn.jobdesc AS section_name,
                q.quesname AS question,
                jnd.answer AS answers,
                att.filename AS attachment,
                jn.identifier AS identifier,
                jn.seqno AS seqno
            FROM 
                jobneed AS jn
            INNER JOIN 
                jobneeddetails AS jnd ON jn.id = jnd.jobneed_id
            INNER JOIN 
                Question AS q ON jnd.question_id = q.id
            LEFT JOIN 
                Attachment AS att ON jn.uuid::text = att.owner AND (att.attachmenttype = 'ATTACHMENT' OR att.attachmenttype IS NULL)
            CROSS JOIN 
                timezone_setting AS tz
            WHERE
                jn.identifier = 'SITEREPORT' AND
                jn.bu_id IN (SELECT unnest(string_to_array(%s, ',')::integer[]))
                AND (jn.cdtz AT TIME ZONE tz.timezone)::DATE = %s
            ORDER BY 
                jn.id, jnd.seqno;
            ''',
        'PEOPLEQR':
            '''
            select distinct people.peoplename, people.peoplecode from people
            where people.client_id = %s %s %s
            ''',
        'ASSETWISETASKSTATUS':
            '''
            WITH timezone_setting AS (
                SELECT '{timezone}'::text AS timezone
            )

            SELECT 
                Asset.id ,
                Asset.assetname AS "Asset Name",
                COUNT(CASE WHEN jobneed.jobstatus = 'AUTOCLOSED' THEN 1 END) AS "AutoClosed",
                COUNT(CASE WHEN jobneed.jobstatus = 'COMPLETED' THEN 1 END) AS "Completed",
                COUNT(CASE WHEN jobneed.jobstatus IN ('AUTOCLOSED', 'COMPLETED') THEN 1 END) AS "Total Tasks"
            FROM 
                Asset
            LEFT JOIN 
                jobneed ON Asset.id = jobneed.asset_id
			CROSS JOIN 
                timezone_setting AS tz
            WHERE
				Asset.identifier = 'ASSET' AND
                Asset.id <> 1 AND
                jobneed.bu_id IN (SELECT unnest(string_to_array('{siteids}', ',')::integer[]))
                AND (jobneed.plandatetime AT TIME ZONE tz.timezone) BETWEEN '{from}' AND '{upto}'
            GROUP BY 
                Asset.assetname,asset.id
            
            ''',
            "STATICDETAILEDTOURSUMMARY":
            '''
            WITH timezone_setting AS (
                SELECT '{timezone}' ::text AS timezone
            )
            SELECT * ,
                        CASE 
                            WHEN "No of Checkpoints" = 0 THEN 0
                            ELSE ROUND((CAST("Completed" AS FLOAT) / "No of Checkpoints") * 100)
                            END AS "Percentage"
                        FROM (
            SELECT 
                client_table.buname AS "Client Name",
                site_table.buname AS "Site Name",
                jn.jobdesc AS "Description",
                (jn.plandatetime AT TIME ZONE tz.timezone)::DATE AS "Start Time",
                (jn.expirydatetime AT TIME ZONE tz.timezone)::DATE as "End Time",
                jn.remarks as "Comments",
                type.taname as "Comments Type",
                (SELECT COUNT(*) FROM jobneed AS jn_child WHERE jn_child.parent_id = jn.id) AS "No of Checkpoints",
                (SELECT COUNT(*) FROM jobneed AS jn_child_completed WHERE jn_child_completed.parent_id = jn.id AND jn_child_completed.jobstatus = 'COMPLETED') AS "Completed",
                (SELECT COUNT(*) FROM jobneed AS jn_child_missed WHERE jn_child_missed.parent_id = jn.id AND (jn_child_missed.jobstatus = 'AUTOCLOSED' OR jn_child_missed.jobstatus ='ASSIGNED')) AS "Missed"
            FROM 
                jobneed AS jn
            JOIN 
                bt AS client_table ON jn.client_id = client_table.id
            JOIN 
                
                bt AS site_table ON jn.bu_id = site_table.id
            JOIN typeassist type ON type.id=jn.remarkstype_id
            cross join timezone_setting tz
            WHERE
                jn.other_info ->> 'istimebound' = 'true' AND
                jn.parent_id = 1 AND
                jn.identifier = 'INTERNALTOUR' AND

                jn.bu_id IN (SELECT unnest(string_to_array('{siteids}', ',')::integer[])) 
                AND (jn.plandatetime AT TIME ZONE tz.timezone) BETWEEN '{from}' AND '{upto}'
            ) as x
            ''',
            "DYNAMICDETAILEDTOURSUMMARY":
            '''
            WITH timezone_setting AS (
                SELECT '{timezone}' ::text AS timezone
            )
            SELECT * ,
                        CASE 
                            WHEN "No of Checkpoints" = 0 THEN 0
                            ELSE ROUND((CAST("Completed" AS FLOAT) / "No of Checkpoints") * 100)
                            END AS "Percentage"
                        FROM (
            SELECT 
                client_table.buname AS "Client Name",
                site_table.buname AS "Site Name",
                jn.jobdesc AS "Description",
                (jn.plandatetime AT TIME ZONE tz.timezone)::DATE AS "Start Time",
                (jn.expirydatetime AT TIME ZONE tz.timezone)::DATE as "End Time",
                jn.remarks as "Comments",
                type.taname as "Comments Type",
                (SELECT COUNT(*) FROM jobneed AS jn_child WHERE jn_child.parent_id = jn.id) AS "No of Checkpoints",
                (SELECT COUNT(*) FROM jobneed AS jn_child_completed WHERE jn_child_completed.parent_id = jn.id AND jn_child_completed.jobstatus = 'COMPLETED') AS "Completed",
                (SELECT COUNT(*) FROM jobneed AS jn_child_missed WHERE jn_child_missed.parent_id = jn.id AND (jn_child_missed.jobstatus = 'AUTOCLOSED' OR jn_child_missed.jobstatus = 'ASSIGNED')) AS "Missed"
            FROM 
                jobneed AS jn
            JOIN 
                bt AS client_table ON jn.client_id = client_table.id
            JOIN 
                
                bt AS site_table ON jn.bu_id = site_table.id
            JOIN typeassist type ON type.id=jn.remarkstype_id
            cross join timezone_setting tz
            WHERE
                jn.other_info ->> 'istimebound' = 'false' AND
                jn.parent_id = 1 AND
                jn.identifier = 'INTERNALTOUR' AND
                jn.bu_id IN (SELECT unnest(string_to_array('{siteids}', ',')::integer[])) 
                AND (jn.plandatetime AT TIME ZONE tz.timezone)::DATE BETWEEN '{from}' AND '{upto}'
            ) as x
            ''',
            "LOGSHEET":
            '''
            WITH timezone_setting AS (
                SELECT '{timezone}' ::text AS timezone
            )

            select
                jobneed.id,
                (jobneed.plandatetime AT TIME ZONE tz.timezone) as "Plan Datetime",
                jobneed.jobdesc,
                case when (jobneed.people_id<>1 or jobneed.people_id is NULL) then people.peoplename else pgroup.groupname end as "Assigned To",
                asset.assetname as "Asset",
                permby.peoplename as "Performed By",
                questionset.qsetname,
                (jobneed.expirydatetime AT TIME ZONE tz.timezone) as expirydatetime,
                jobneed.gracetime,
                site.buname as site,
                jobneed.scantype,
                jobneed.receivedonserver,
                jobneed.priority,
                (jobneed.starttime AT TIME ZONE tz.timezone) as "Start Time",
                (jobneed.endtime AT TIME ZONE tz.timezone) as "End Time",
                jobneed.gpslocation,
                jobneed.remarks,
                jndls.seqno,
                jndls.quesname,
                CASE
                    WHEN jndls.answer IS NOT NULL AND trim(jndls.answer) <> '' AND jndls.answertype = 'NUMERIC' THEN
                        coalesce(round(jndls.answer::NUMERIC, 2), 0)::text
                    WHEN trim(jndls.answer) = '' THEN
                        'X0X'::text
                    ELSE
                        coalesce(jndls.answer, '0')::text
                END AS answer
            from jobneed
            inner join asset on asset.id = jobneed.asset_id
            inner join people on jobneed.people_id = people.id  
            inner join pgroup on jobneed.pgroup_id = pgroup.id
            inner join questionset on questionset.id = jobneed.qset_id
            inner join bt site on site.id = jobneed.bu_id
            inner join people permby on permby.id = jobneed.performedby_id
            cross join timezone_setting tz
            left join (
                select 
                    jndd.jobneed_id,
                    q.quesname, 
                    jndd.answertype,
                    jndd.seqno,
                    jndd.answer,
                    jndd.min,
                    jndd.max,  
                    initcap(case when jndd.alerts=true then 'YES' else 'NO' end) as alerts
                from jobneeddetails jndd
                inner join question q on jndd.question_id = q.id
                
            ) jndls on jndls.jobneed_id = jobneed.id
            where 
                1=1 
                and jobneed.identifier = 'TASK' 
                and jobneed.jobstatus = 'COMPLETED'
                and jobneed.bu_id::text = '{buid}'
                AND jobneed.qset_id='{qsetid}'
                AND jobneed.asset_id='{assetid}'
                AND coalesce(jndls.answer, '') <> ''
            ''',
            "LogBook-Q1":
            '''
            with timezone_setting as (
                select {timezone} ::text as timezone
            )
            select
                jobneed.id,
                (jobneed.plandatetime AT TIME ZONE tz.timezone) as "Plan DateTime",
                jobneed.jobdesc as "Description",
                case when jobneed.people_id<> 1 then people.peoplename else pgroup.groupname end as "Assigned To",
                jt.tacode as jobtype,
                jstatus.tacode as "Status",
                asset.assetname as "Asset",
                permby.peoplename as "Performed By",
                questionset.qsetname,
                (jobneed.expirydatetime AT TIME ZONE tz.timezone) as expirydatetime,
                jobneed.gracetime,
                site.buname as site,
                jobneed.scantype,
                jobneed.receivedonserver,
                jobneed.priority,
                (jobneed.starttime AT TIME ZONE tz.timezone) as "Start Time" ,
                (jobneed.endtime AT TIME ZONE tz.timezone) as "End Time",
                jobneed.gpslocation,
                jobneed.qset_id,
                jobneed.remarks as "Remarks"
            from jobneed jobneed
            inner join asset on asset.id=jobneed.asset_id
            cross join timezone_setting tz
            inner join people on jobneed.people_id=people.id
            inner join pgroup on jobneed.pgroup_id=pgroup.id
            inner join questionset on questionset.id=jobneed.qset_id
            inner join bu site on site.id=jobneed.bu_id
            inner join people permby on permby.id=jobneed.performedby
            where 1=1 
            and identifier='TASK' and jobstatus='COMPLETED'
            and jobneed.bu_id::text = {siteid} and jobneed.asset_id={assetid}
            and jobneed.qset_id={qset_id} and
            (jobneed.plandatetime  at time zone tz.timezone)::DATE between {fromdate} and {uptodate} 
            ''',
            'LogBook-Q2':
            '''
            select 
            q.quesname, jndd.seqno, jndd.answer,
            jndd.min, jndd.max, initcap(case when jndd.alerts=true then 'YES' else 'NO' end) as alerts
            from jobneeddetails jndd
            inner join question q on jndd.question_id=q.id
            where  jobneedid={jobneedid} order by seqno
            ''',

            "RP_SITEVISITREPORT":
            ''' 
            with timezone_setting as (
                select '{timezone}' ::text as timezone
            )
            select 
                pg.groupname as "Route Name/Cluster",
                bu.bupreferences->'address2'->>'state'AS "State",
                bu.solid as "Sol Id",
                bu.buname as "Site Name",
                CASE WHEN jobneed.starttime IS NULL THEN 'Not Performed' 
                 ELSE TO_CHAR(jobneed.starttime AT TIME ZONE tz.timezone, 'HH24:MI') END AS endtime_time, 
                EXTRACT(DAY FROM parent.plandatetime AT TIME ZONE tz.timezone) AS endtime_day
            from jobneed 
            INNER JOIN bt bu ON bu.id=jobneed.bu_id 
            INNER JOIN pgroup pg on pg.id = jobneed.sgroup_id
            INNER JOIN jobneed parent on parent.id=jobneed.parent_id
            CROSS JOIN 
                timezone_setting AS tz
            where parent.other_info->>'tour_frequency'='2'
            AND jobneed.identifier = 'EXTERNALTOUR' 
            AND jobneed.parent_id <> 1
            AND jobneed.sgroup_id IN (SELECT unnest(string_to_array('{sgroupids}', ',')::integer[]))
            AND (parent.plandatetime AT TIME ZONE tz.timezone) BETWEEN '{from}' AND '{upto}'
            GROUP BY bu.solid,bu.buname,"State",endtime_time,endtime_day,jobneed.plandatetime,pg.groupname,jobneed.id
            ORDER By bu.buname,endtime_day;
            ''',
            "DYNAMICTOURLIST":
            '''
            WITH timezone_setting AS (
                SELECT '{timezone}' ::text AS timezone
            )
                SELECT
                --bu.id,
				client_table.buname AS "Client",
                bu.buname as "Site",
				jobneed.jobdesc as "Tour/Route",
                (jobneed.plandatetime AT TIME ZONE tz.timezone)::timestamp as "Planned Datetime",
				(jobneed.expirydatetime AT TIME ZONE tz.timezone)::timestamp as "Expiry Datetime",
            case
                    when jobneed.people_id <> 1 then people.peoplename
                    when jobneed.pgroup_id <> 1 then pgroup.groupname
                    else 'NONE' end as "Assigned To",
            jobneed.jobtype as "JobType",
            jobneed.jobstatus as "Status",
			(jobneed.endtime AT TIME ZONE tz.timezone)::timestamp as "Performed On",
            performedpeople.peoplename as "Performed By"
                FROM jobneed
                INNER JOIN bt bu ON bu.id=jobneed.bu_id
                INNER JOIN bt AS client_table ON jobneed.client_id = client_table.id
            INNER JOIN asset ON asset.id=jobneed.asset_id
            INNER JOIN questionset ON questionset.id=jobneed.qset_id
            INNER JOIN people on jobneed.people_id=people.id
            INNER JOIN people performedpeople on jobneed.performedby_id=performedpeople.id
            inner join pgroup on pgroup.id=jobneed.pgroup_id
                CROSS JOIN timezone_setting tz
                WHERE jobneed.identifier='INTERNALTOUR'
            AND jobneed.id <> 1 and jobneed.parent_id = 1
            AND jobneed.other_info ->> 'istimebound' = 'false'
            AND bu.id <> 1
            AND jobneed.bu_id IN (SELECT unnest(string_to_array('{siteids}', ',')::integer[]))
            AND (jobneed.plandatetime AT TIME ZONE tz.timezone) BETWEEN '{from}' AND '{upto}'
            ORDER BY bu.buname, (jobneed.plandatetime AT TIME ZONE tz.timezone)::DATE desc
            ''',
            "STATICTOURLIST":
            '''
            WITH timezone_setting AS (
                SELECT '{timezone}' ::text AS timezone
            )
                SELECT
                --bu.id,
				client_table.buname AS "Client",
                bu.buname as "Site",
				jobneed.jobdesc as "Tour/Route",
                (jobneed.plandatetime AT TIME ZONE tz.timezone)::timestamp as "Planned Datetime",
				(jobneed.expirydatetime AT TIME ZONE tz.timezone)::timestamp as "Expiry Datetime",
            case
                    when jobneed.people_id <> 1 then people.peoplename
                    when jobneed.pgroup_id <> 1 then pgroup.groupname
                    else 'NONE' end as "Assigned To",
            jobneed.jobtype as "JobType",
            jobneed.jobstatus as "Status",
			(jobneed.endtime AT TIME ZONE tz.timezone)::timestamp as "Performed On",
            performedpeople.peoplename as "Performed By"
                FROM jobneed
                INNER JOIN bt bu ON bu.id=jobneed.bu_id
                INNER JOIN bt AS client_table ON jobneed.client_id = client_table.id
            INNER JOIN asset ON asset.id=jobneed.asset_id
            INNER JOIN questionset ON questionset.id=jobneed.qset_id
            INNER JOIN people on jobneed.people_id=people.id
            INNER JOIN people performedpeople on jobneed.performedby_id=performedpeople.id
            inner join pgroup on pgroup.id=jobneed.pgroup_id
                CROSS JOIN timezone_setting tz
                WHERE jobneed.identifier='INTERNALTOUR'
            AND jobneed.id <> 1 and jobneed.parent_id = 1
            AND jobneed.other_info ->> 'istimebound' = 'true'
            AND bu.id <> 1
            AND jobneed.bu_id IN (SELECT unnest(string_to_array('{siteids}', ',')::integer[]))
            AND (jobneed.plandatetime AT TIME ZONE tz.timezone) BETWEEN '{from}' AND '{upto}'
            ORDER BY bu.buname, (jobneed.plandatetime AT TIME ZONE tz.timezone)::DATE desc
            ''',
            'PEOPLEATTENDANCESUMMARY':
            '''
            WITH timezone_setting AS (
                SELECT '{timezone}'::text AS timezone
            ),
            aggregated_times AS (
                SELECT
                    pel.id,
                    pel.people_id,
                    pel.datefor,
                    MIN(pel.punchintime) AS min_punchintime,
                    MAX(pel.punchouttime) AS max_punchouttime
                FROM 
                    peopleeventlog pel
                CROSS JOIN timezone_setting tz
                INNER JOIN typeassist eventtype on pel.peventtype_id = eventtype.id
                WHERE
                    pel.bu_id IN (SELECT unnest(string_to_array('{siteids}', ',')::integer[])) AND
                     pel.datefor BETWEEN '{from}' AND '{upto}' AND
                    (pel.punchouttime AT TIME ZONE tz.timezone)::date = pel.datefor AND
                    eventtype.tacode in ('SELF','MARK')
                GROUP BY
                    pel.id,
                    pel.people_id,
                    pel.datefor
            ),
            detailed_info AS (
                SELECT
                    at.id,
                    deptype.taname AS department,
                    desgtype.taname AS designation,
                    p.peoplename AS peoplename,
                    p.peoplecode AS peoplecode,
                    EXTRACT(DAY FROM at.datefor) AS day,
                    TO_CHAR(at.datefor, 'Day') AS day_of_week,
                    CONCAT(
                        EXTRACT(HOUR FROM at.min_punchintime AT TIME ZONE tz.timezone), 
                        ':', 
                        EXTRACT(MINUTE FROM at.min_punchintime AT TIME ZONE tz.timezone)
                    ) AS punch_intime,
                    CONCAT(
                        EXTRACT(HOUR FROM at.max_punchouttime AT TIME ZONE tz.timezone), 
                        ':', 
                        EXTRACT(MINUTE FROM at.max_punchouttime AT TIME ZONE tz.timezone)
                    ) AS punch_outtime,
                    CONCAT(
                        TRUNC((EXTRACT(EPOCH FROM at.max_punchouttime AT TIME ZONE tz.timezone) - EXTRACT(EPOCH FROM at.min_punchintime AT TIME ZONE tz.timezone)) / 3600),
                        ':',
                        EXTRACT(MINUTE FROM (at.max_punchouttime AT TIME ZONE tz.timezone - at.min_punchintime AT TIME ZONE tz.timezone))
                    ) AS totaltime
                FROM 
                    aggregated_times at
                INNER JOIN people p ON at.people_id = p.id
                INNER JOIN typeassist desgtype ON p.designation_id = desgtype.id
                INNER JOIN typeassist deptype ON p.department_id = deptype.id
                CROSS JOIN timezone_setting tz
            )
            SELECT * FROM detailed_info
            ORDER BY day;
            '''
    }.get(query) 


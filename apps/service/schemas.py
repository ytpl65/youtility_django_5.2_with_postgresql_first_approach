"""
JSON Schema definitions for API validation in YOUTILITY3.
"""

# User authentication schema
USER_LOGIN_SCHEMA = {
    "type": "object",
    "properties": {
        "loginid": {
            "type": "string",
            "minLength": 3,
            "maxLength": 50,
            "pattern": "^[a-zA-Z0-9@._-]+$"
        },
        "password": {
            "type": "string",
            "minLength": 6,
            "maxLength": 100
        },
        "clientcode": {
            "type": "string",
            "minLength": 2,
            "maxLength": 20,
            "pattern": "^[A-Z0-9]+$"
        }
    },
    "required": ["loginid", "password", "clientcode"],
    "additionalProperties": False
}

# Asset creation schema
ASSET_CREATE_SCHEMA = {
    "type": "object",
    "properties": {
        "assetname": {
            "type": "string",
            "minLength": 1,
            "maxLength": 100,
            "pattern": "^[a-zA-Z0-9\\s\\-_#.]+$"
        },
        "assetcode": {
            "type": "string",
            "minLength": 1,
            "maxLength": 50,
            "pattern": "^[A-Z0-9\\-_]+$"
        },
        "location_id": {
            "type": "integer",
            "minimum": 1
        },
        "bu_id": {
            "type": "integer",
            "minimum": 1
        },
        "client_id": {
            "type": "integer",
            "minimum": 1
        }
    },
    "required": ["assetname", "assetcode", "location_id", "bu_id", "client_id"],
    "additionalProperties": False
}

# Job creation schema
JOB_CREATE_SCHEMA = {
    "type": "object",
    "properties": {
        "jobname": {
            "type": "string",
            "minLength": 1,
            "maxLength": 200,
            "pattern": "^[a-zA-Z0-9\\s\\-_#.()]+$"
        },
        "jobdesc": {
            "type": "string",
            "maxLength": 2000
        },
        "planduration": {
            "type": "integer",
            "minimum": 1,
            "maximum": 1440  # Max 24 hours in minutes
        },
        "gracetime": {
            "type": "integer",
            "minimum": 0,
            "maximum": 60   # Max 1 hour grace time
        },
        "frequency": {
            "type": "string",
            "enum": ["ONCE", "DAILY", "WEEKLY", "MONTHLY", "YEARLY"]
        },
        "priority": {
            "type": "string",
            "enum": ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
        },
        "bu_id": {
            "type": "integer",
            "minimum": 1
        },
        "client_id": {
            "type": "integer",
            "minimum": 1
        }
    },
    "required": ["jobname", "planduration", "frequency", "priority", "bu_id", "client_id"],
    "additionalProperties": False
}

# Location coordinates schema
COORDINATES_SCHEMA = {
    "type": "object",
    "properties": {
        "latitude": {
            "type": "number",
            "minimum": -90,
            "maximum": 90
        },
        "longitude": {
            "type": "number",
            "minimum": -180,
            "maximum": 180
        }
    },
    "required": ["latitude", "longitude"],
    "additionalProperties": False
}

# Attendance update schema
ATTENDANCE_UPDATE_SCHEMA = {
    "type": "object",
    "properties": {
        "people_id": {
            "type": "integer",
            "minimum": 1
        },
        "location": COORDINATES_SCHEMA,
        "timestamp": {
            "type": "string",
            "pattern": "^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(\\.\\d{3})?Z?$"
        },
        "status": {
            "type": "string",
            "enum": ["IN", "OUT", "BREAK_START", "BREAK_END"]
        },
        "remarks": {
            "type": "string",
            "maxLength": 500
        }
    },
    "required": ["people_id", "location", "timestamp", "status"],
    "additionalProperties": False
}

# Question submission schema
QUESTION_ANSWER_SCHEMA = {
    "type": "object",
    "properties": {
        "question_id": {
            "type": "integer",
            "minimum": 1
        },
        "answer": {
            "oneOf": [
                {"type": "string", "maxLength": 1000},
                {"type": "number"},
                {"type": "boolean"}
            ]
        },
        "timestamp": {
            "type": "string",
            "pattern": "^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(\\.\\d{3})?Z?$"
        },
        "location": COORDINATES_SCHEMA
    },
    "required": ["question_id", "answer", "timestamp"],
    "additionalProperties": False
}

# File upload metadata schema
FILE_UPLOAD_SCHEMA = {
    "type": "object",
    "properties": {
        "filename": {
            "type": "string",
            "minLength": 1,
            "maxLength": 255,
            "pattern": "^[a-zA-Z0-9\\-_. ]+\\.[a-zA-Z0-9]+$"
        },
        "file_type": {
            "type": "string",
            "enum": ["image", "document", "video", "audio"]
        },
        "file_size": {
            "type": "integer",
            "minimum": 1,
            "maximum": 52428800  # 50MB max
        },
        "description": {
            "type": "string",
            "maxLength": 500
        },
        "related_entity": {
            "type": "string",
            "enum": ["job", "asset", "location", "people", "report"]
        },
        "related_id": {
            "type": "integer",
            "minimum": 1
        }
    },
    "required": ["filename", "file_type", "file_size", "related_entity", "related_id"],
    "additionalProperties": False
}

# Report generation schema
REPORT_REQUEST_SCHEMA = {
    "type": "object",
    "properties": {
        "report_type": {
            "type": "string",
            "enum": ["attendance", "job_summary", "asset_status", "tour_report", "performance"]
        },
        "date_from": {
            "type": "string",
            "pattern": "^\\d{4}-\\d{2}-\\d{2}$"
        },
        "date_to": {
            "type": "string",
            "pattern": "^\\d{4}-\\d{2}-\\d{2}$"
        },
        "filters": {
            "type": "object",
            "properties": {
                "bu_id": {"type": "integer", "minimum": 1},
                "people_id": {"type": "integer", "minimum": 1},
                "location_id": {"type": "integer", "minimum": 1},
                "status": {"type": "string", "maxLength": 50}
            },
            "additionalProperties": False
        },
        "format": {
            "type": "string",
            "enum": ["pdf", "csv", "excel"]
        }
    },
    "required": ["report_type", "date_from", "date_to", "format"],
    "additionalProperties": False
}

# Common pagination schema
PAGINATION_SCHEMA = {
    "type": "object",
    "properties": {
        "page": {
            "type": "integer",
            "minimum": 1,
            "maximum": 1000
        },
        "page_size": {
            "type": "integer",
            "minimum": 1,
            "maximum": 100
        },
        "sort_by": {
            "type": "string",
            "maxLength": 50,
            "pattern": "^[a-zA-Z_]+$"
        },
        "sort_order": {
            "type": "string",
            "enum": ["asc", "desc"]
        }
    },
    "additionalProperties": False
}

# Search/filter schema
SEARCH_SCHEMA = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "minLength": 1,
            "maxLength": 100,
            "pattern": "^[a-zA-Z0-9\\s\\-_#@.]+$"
        },
        "fields": {
            "type": "array",
            "items": {
                "type": "string",
                "pattern": "^[a-zA-Z_]+$"
            },
            "maxItems": 10
        },
        "filters": {
            "type": "object",
            "additionalProperties": {
                "oneOf": [
                    {"type": "string", "maxLength": 100},
                    {"type": "integer"},
                    {"type": "boolean"}
                ]
            }
        }
    },
    "required": ["query"],
    "additionalProperties": False
}

# Collection of all schemas for easy access
API_SCHEMAS = {
    'user_login': USER_LOGIN_SCHEMA,
    'asset_create': ASSET_CREATE_SCHEMA,
    'job_create': JOB_CREATE_SCHEMA,
    'coordinates': COORDINATES_SCHEMA,
    'attendance_update': ATTENDANCE_UPDATE_SCHEMA,
    'question_answer': QUESTION_ANSWER_SCHEMA,
    'file_upload': FILE_UPLOAD_SCHEMA,
    'report_request': REPORT_REQUEST_SCHEMA,
    'pagination': PAGINATION_SCHEMA,
    'search': SEARCH_SCHEMA,
}
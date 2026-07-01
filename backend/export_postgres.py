import psycopg2
import json
from decimal import Decimal
import datetime

def default_serializer(obj):
    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Type {type(obj)} not serializable")

host = "10.11.89.202"
port = 5432
user = "looker"
password = "eef016c359387b02def0ba508dccdadf593b0b1d"
dbname = "horus"

conn = psycopg2.connect(host=host, port=port, user=user, password=password, dbname=dbname)
cur = conn.cursor()

cur.execute("""
    SELECT id, user_id, team, operation_date, "educationPcd_id", "educationAgents_id",
            changes_staff, breathalyzers, cars_id, changes_general, contact_received,
            occurrence_observation, lat, lng, created_at, updated_at
    FROM reducols_sections
""")
reports_data = cur.fetchall()

cur.execute("""
    SELECT id, reducols_section_id, place_action, type_action, type_audience, institution_name,
            start_time, final_hour, approach, tests, used_caps, available_caps,
            distributed_folders, cricris, vetarolas, used_adhesives, sequence_certificates, gibis, distributed_certificates
    FROM reducols_section_twos
""")
actions_data = cur.fetchall()

data = {
    "reports": reports_data,
    "actions": actions_data
}

with open("external_reports.json", "w") as f:
    json.dump(data, f, default=default_serializer)

print("Exported external_reports.json")
cur.close()
conn.close()

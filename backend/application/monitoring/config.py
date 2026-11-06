from os import environ

# InfluxDB connection used to store monitoring metrics. The token has no default: set INFLUXDB_TOKEN
# to the token created on your InfluxDB instance, otherwise the monitoring system stays disabled.
INFLUXDB_TOKEN = environ.get("INFLUXDB_TOKEN") or None
INFLUXDB_ORG = environ.get("INFLUXDB_ORG") or "org"
INFLUXDB_URL = environ.get("INFLUXDB_URL") or "http://localhost:8086"
INFLUXDB_BUCKET = environ.get("INFLUXDB_BUCKET") or "MISP-Fleet-Commander"

#!/usr/bin/env python

from datetime import date
import json
from application.monitoring.utils import logger, SensorBase
from urllib.parse import urljoin


def parseTime(value, unit):
    if unit == 's':
        return float(value)
    elif unit == 'ms':
        return float(value)*1000

def parseBytes(value, unit):
    if unit == 'MB':
        return int(value)
    elif unit == 'GB':
        return int(value)*1024


class MISP(SensorBase):

    collection_rate = 5  # min
    measurement_name = 'MISP'

    def __init__(self, name, url, authkey, skip_ssl=False):
        self.name = name
        self.baseurl = url
        self.authkey = authkey
        self.skip_ssl = skip_ssl
        self.default_tags = {
            'instance': self.name,
            'url': self.baseurl,
        }
        self.headers = {
            'user-agent': 'circl-monitoring/0.1',
            'Authorization': self.authkey,
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        super().__init__()

    def query_misp(self, url, data=None, headers=None):
        fullurl = urljoin(self.baseurl, url)
        logger.debug(f'Querying {self.measurement_name} `{self.name}`: {fullurl}')
        return self.query(fullurl, data=data, headers=self.headers, ssl=not self.skip_ssl)

    def get_measurements_coroutines(self):
        # Create and executes all queries
        corou_to_execute = []
        corou_to_execute.append(self.get_login())
        corou_to_execute.append(self.get_stats())
        corou_to_execute.append(self.get_open_registration())
        for corou in self.get_all_benchmarking():
            corou_to_execute.append(corou)
        corou_to_execute.append(self.get_diagnostic())
        for corou in self.get_widgets():
            corou_to_execute.append(corou)
        return corou_to_execute

        # return await asyncio.gather(*corou_to_execute)

    def process_measurements(self, results):
        # Generate the measurements for each queries
        measurements = []
        logger.debug(f'Processing {self.measurement_name} `{self.name}`: logins')
        m_logins = self.process_loging(results[0])
        for m_login in m_logins:
            measurements.append(self.measurement_factory.create(m_login['tags'], m_login['fields'], m_login['time']))

        logger.debug(f'Processing {self.measurement_name} `{self.name}`: stats')
        m_stats = self.process_stats(results[1])
        measurements.append(self.measurement_factory.create(m_stats['tags'], m_stats['fields']))

        logger.debug(f'Processing {self.measurement_name} `{self.name}`: registrations')
        m_registration = self.process_open_registration(results[2])
        measurements.append(self.measurement_factory.create(m_registration['tags'], m_registration['fields']))

        logger.debug(f'Processing {self.measurement_name} `{self.name}`: benchmarkings')
        m_benchmarkings = self.process_all_benchmarking(results[3], results[4], results[5])
        for m_benchmarking in m_benchmarkings:
            measurements.append(self.measurement_factory.create(m_benchmarking['tags'], m_benchmarking['fields']))

        logger.debug(f'Processing {self.measurement_name} `{self.name}`: diagnostic')
        m_diagnostics = self.process_diagnostic(results[6])
        for m_diagnostic in m_diagnostics:
            measurements.append(self.measurement_factory.create(m_diagnostic['tags'], m_diagnostic['fields']))

        logger.debug(f'Processing {self.measurement_name} `{self.name}`: widgets')
        m_widgets = self.process_widgets(results[7], results[8], results[9])
        for m_widget in m_widgets:
            measurements.append(self.measurement_factory.create(m_widget['tags'], m_widget['fields'], m_widget.get('time', None)))

        return measurements

    def get_diagnostic(self):
        full_diagnostic = self.query_misp(f'/servers/serverSettings/diagnostics.json')
        return full_diagnostic

    def process_diagnostic(self, diagnostic):
        entries = []

        def process_version(version):
            return [{
                'tags': {
                    'scope': 'diagnostic',
                    'diagnostic_scope': 'version',
                },
                'fields': {
                    'version': version['current'],
                },
            }]

        def process_php_settings(php_settings):
            return []

        def process_db_configuration(db_configuration):
            return []

        def process_redis_info(redis_info):
            return [{
                'tags': {
                    'scope': 'diagnostic',
                    'diagnostic_scope': 'redis_info',
                },
                'fields': {
                    'used_memory': redis_info['used_memory'],
                    'used_memory_peak': redis_info['used_memory_peak'],
                    'db_13_keys': int(redis_info['db13'].split(',')[0][5:]),
                },
            }]

        def process_workers_info(workers_info):
            return [{
                'tags': {
                    'scope': 'diagnostic',
                    'diagnostic_scope': 'workers',
                },
                'fields': {
                    'cache_job_count': workers_info['cache']['jobCount'],
                    'default_job_count': workers_info['default']['jobCount'],
                    'email_job_count': workers_info['email']['jobCount'],
                    'prio_job_count': workers_info['prio']['jobCount'],
                    'update_job_count': workers_info['update']['jobCount'],
                },
            }]

        entries.extend(process_version(diagnostic['version']))
        entries.extend(process_php_settings(diagnostic['phpSettings']))
        entries.extend(process_db_configuration(diagnostic['dbConfiguration']))
        entries.extend(process_redis_info(diagnostic['redisInfo']))
        entries.extend(process_workers_info(diagnostic['workers']))
        return entries

    def get_login(self):
        minute = 60
        login_logs = self.query_misp(f'/logs/index/created:{minute}m/model:User/action:login.json')
        return login_logs

    def process_loging(self, login_logs):
        logins = []
        for login_log in login_logs:
            logins.append({
                'tags': {
                    'scope': 'logins',
                    'email': login_log['Log']['email'],
                    'org': login_log['Log']['org'],
                },
                'fields': {
                    'ip': login_log['Log']['ip'],
                },
                'time': login_log['Log']['created'],
            })
        return logins

    def get_widgets(self):
        systemRessource = self.query_misp(f'/dashboards/renderWidget/0/exportjson:1', {
            "config": "{}",
            "widget": "MispSystemResourceWidget"
        })
        adminRessource = self.query_misp(f'/dashboards/renderWidget/0/exportjson:1', {
            "config": "{}",
            "widget": "MispAdminResourceWidget"
        })
        APIActivity = self.query_misp(f'/dashboards/renderWidget/0/exportjson:1', {
            "config": json.dumps({
                # 'limit': 100,
                'days': 1,
            }),
            "widget": "APIActivityWidget"
        })
        return [systemRessource, adminRessource, APIActivity]

    def process_widgets(self, systemRessource, adminRessource, APIActivity):
        widgets = []
        disk = systemRessource[2]['value']
        loads = systemRessource[3]['value'].split('-')
        memory = systemRessource[4]['value']
        mysql_disk = adminRessource[2]
        widgets.append({
            'tags': {
                'scope': 'diagnostic',
                'diagnostic_scope': 'system_usage',
            },
            'fields': {
                'disk_usage': float(disk[:-1]),
                'load_short': float(loads[0]),
                'load_medium': float(loads[1]),
                'load_long': float(loads[2]),
                'memory_free': float(memory.split(' ', 1)[0]),
                'memory_usage': float(memory.split('(', 1)[1].split(' ')[0]),
                'mysql_disk_usage': float(mysql_disk['value'][:-1])
            },
        })

        total_queries = 0
        for entry in APIActivity:
            usage = int(entry['html'].split(' ')[0])
            total_queries += usage
        widgets.append({
            'tags': {
                'scope': 'api_activity',
            },
            'fields': {
                'total_queries': total_queries,
            },
        })
        return widgets

    def get_stats(self):
        stats = self.query_misp('/users/statistics.json')
        return stats

    def process_stats(self, stats):
        return {
            'tags': {
                'scope': 'data_stats',
            },
            'fields': {
                'event_count': int(stats['stats']['event_count']),
                'attribute_count': int(stats['stats']['attribute_count']),
                'attributes_per_event': int(stats['stats']['attributes_per_event']),
                'object_count': int(stats['stats'].get('object_count', 0)),
                'objects_per_event': int(stats['stats'].get('objects_per_event', 0)),
                'eventreport_count': int(stats['stats'].get('eventreport_count', 0)),
                'analyst_data_count': int(stats['stats'].get('analyst_data_count', 0)),
                'correlation_count': int(stats['stats']['correlation_count']),
                'proposal_count': int(stats['stats']['proposal_count']),
                'user_count': int(stats['stats']['user_count']),
                'user_count_pgp': int(stats['stats']['user_count_pgp']),
                'org_count': int(stats['stats']['org_count']),
                'local_org_count': int(stats['stats']['local_org_count']),
                'contributing_org_count': int(stats['stats']['contributing_org_count']),
                'average_user_per_org': int(float(stats['stats']['average_user_per_org'])),
            },
        }

    def get_open_registration(self):
        registrations_index = self.query_misp('/users/registrations.json')
        return registrations_index

    def process_open_registration(self, registrations_index):
        return {
            'tags': {
                'scope': 'open_self_registration',
            },
            'fields': {
                'open_self_registration': len(registrations_index)
            }
        }

    def get_all_benchmarking(self):
        today_date = date.today().isoformat()
        days = f"/days[]:{today_date}"
        benchmark_time_all_endpoint = self.query_misp(f'/benchmarks/index/scope:endpoint/field:time{days}.json')
        benchmark_sqltime_all_endpoint = self.query_misp(f'/benchmarks/index/scope:endpoint/field:sql_time{days}.json')
        benchmark_memory_all_endpoint = self.query_misp(f'/benchmarks/index/scope:endpoint/field:memory{days}.json')
        return [
            benchmark_time_all_endpoint,
            benchmark_sqltime_all_endpoint,
            benchmark_memory_all_endpoint,
        ]

    def process_all_benchmarking(self, benchmark_time_all_endpoint, benchmark_sqltime_all_endpoint, benchmark_memory_all_endpoint):
        benchmarking = []
        for benchmark_time_endpoint in benchmark_time_all_endpoint:
            benchmarking.append({
                'tags': {
                    'scope': 'benchmark',
                    'benchmark_scope': benchmark_time_endpoint['scope'],
                    'benchmark_field': benchmark_time_endpoint['field'],
                    'endpoint': benchmark_time_endpoint['key'],
                },
                'fields': {
                    'daily_time': parseTime(benchmark_time_endpoint['value'], benchmark_time_endpoint['unit']),
                }
            })

        for benchmark_sqltime_endpoint in benchmark_sqltime_all_endpoint:
            benchmarking.append({
                'tags': {
                    'scope': 'benchmark',
                    'benchmark_scope': benchmark_sqltime_endpoint['scope'],
                    'benchmark_field': benchmark_sqltime_endpoint['field'],
                    'endpoint': benchmark_sqltime_endpoint['key'],
                },
                'fields': {
                    'sql_time': parseTime(benchmark_sqltime_endpoint['value'], benchmark_sqltime_endpoint['unit']),
                }
            })

        for benchmark_memory_endpoint in benchmark_memory_all_endpoint:
            benchmarking.append({
                'tags': {
                    'scope': 'benchmark',
                    'benchmark_scope': benchmark_memory_endpoint['scope'],
                    'benchmark_field': benchmark_memory_endpoint['field'],
                    'endpoint': benchmark_memory_endpoint['key'],
                },
                'fields': {
                    'memory': parseBytes(benchmark_memory_endpoint['value'], benchmark_memory_endpoint['unit']),
                }
            })

        return benchmarking

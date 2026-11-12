"""Lifecycle (end-of-life / deprecation) registry used to scan ``infrastructure.existing_systems``.

Dates are compared with KB_AS_OF (a fixed snapshot date) so results stay deterministic.
kind:
  eol          - no longer supported on that date
  extended     - out of mainstream support; security fixes only until `date`
  maintenance  - service frozen / sustaining-only
  closed       - closed to new customers
  renamed      - still supported under a new name (informational)
"""

KB_AS_OF = "2026-11-13"

L = []


def life(name, patterns, kind, date, replacement, src, note=""):
    L.append({"name": name, "patterns": patterns, "kind": kind, "date": date, "replacement": replacement,
              "src": src, "note": note})


# --- Microsoft data platform / OS / apps
life("SQL Server 2012", [r"sql ?server 2012"], "eol", "2022-07-12", "SQL Server 2022 or Azure SQL", "ms_lifecycle")
life("SQL Server 2014", [r"sql ?server 2014"], "eol", "2024-07-09", "SQL Server 2022 or Azure SQL", "ms_lifecycle")
life("SQL Server 2016", [r"sql ?server 2016"], "eol", "2026-07-14", "SQL Server 2022 or Azure SQL", "ms_lifecycle")
life("SQL Server 2017", [r"sql ?server 2017"], "extended", "2027-10-12", "SQL Server 2022 or Azure SQL", "ms_lifecycle")
life("SQL Server 2019", [r"sql ?server 2019"], "extended", "2030-01-08", "SQL Server 2022/2025 or Azure SQL",
     "sqlserver2019", "Mainstream support ended 28 Feb 2025; security updates only.")
life("Windows Server 2012/2012 R2", [r"windows server 2012"], "eol", "2023-10-10", "Windows Server 2022/2025", "ms_lifecycle")
life("Windows Server 2016", [r"windows server 2016"], "extended", "2027-01-12", "Windows Server 2022/2025", "ms_lifecycle")
life("Windows Server 2019", [r"windows server 2019"], "extended", "2029-01-09", "Windows Server 2025", "ms_lifecycle")
life("Windows 10", [r"windows 10\b"], "eol", "2025-10-14", "Windows 11", "ms_lifecycle")
life("Exchange Server 2016/2019", [r"exchange (server )?(2016|2019)"], "eol", "2025-10-14", "Exchange Online / Exchange SE", "ms_lifecycle")
life("SharePoint Server 2016/2019", [r"sharepoint (server )?(2016|2019)"], "eol", "2026-07-14", "SharePoint Online / Subscription Edition", "ms_lifecycle")
life("Office 2016/2019", [r"office (2016|2019)"], "eol", "2025-10-14", "Microsoft 365 Apps", "ms_lifecycle")
life("Skype for Business Server", [r"skype for business"], "eol", "2025-10-14", "Microsoft Teams", "ms_lifecycle")
life("Skype", [r"\bskype\b(?! for business)"], "eol", "2025-05-05", "Microsoft Teams", "ms_lifecycle")
life("Internet Explorer", [r"internet explorer", r"\bie ?11\b"], "eol", "2022-06-15", "Microsoft Edge", "ms_lifecycle")
life("Azure AD (now Microsoft Entra ID)", [r"azure ad\b(?! graph)", r"azure active directory"], "renamed", "2023-07-11",
     "Microsoft Entra ID (same service)", "entra", "Renamed only; fully supported.")
life("Azure AD Graph API", [r"azure ad graph"], "eol", "2025-09-01", "Microsoft Graph", "graph")
life("Xamarin", [r"xamarin"], "eol", "2024-05-01", ".NET MAUI", "xamarin_eol")
life("Visual Studio App Center", [r"app ?center"], "eol", "2025-03-31", "EAS / Codemagic / GitHub Actions + fastlane", "appcenter_retire")
life(".NET Core 3.1 / .NET 5", [r"\.net core 3", r"\.net 5\b"], "eol", "2022-12-13", ".NET 10 LTS", "dotnet_policy")
life(".NET 6", [r"\.net 6\b"], "eol", "2024-11-12", ".NET 10 LTS", "dotnet_policy")
life(".NET 7", [r"\.net 7\b"], "eol", "2024-05-14", ".NET 10 LTS", "dotnet_policy")
life(".NET 8", [r"\.net 8\b"], "eol", "2026-11-10", ".NET 10 LTS", "dotnet_policy")
life(".NET 9", [r"\.net 9\b"], "eol", "2026-11-10", ".NET 10 LTS", "dotnet_policy", "STS releases now get 24 months.")
life(".NET Framework 4.5.2-4.6.1", [r"\.net framework 4\.(5|6\.0|6\.1)\b"], "eol", "2022-04-26", ".NET Framework 4.8.1 or .NET 10", "dotnet_policy")
life("Azure Database for PostgreSQL Single Server", [r"postgresql single server", r"azure database for postgresql single"],
     "eol", "2025-03-28", "Azure Database for PostgreSQL Flexible Server", "azure_pg_single")
life("Azure Database for MySQL Single Server", [r"mysql single server"], "eol", "2024-09-16", "Azure Database for MySQL Flexible Server", "azure_mysql_single")
life("Azure Cache for Redis", [r"azure cache for redis"], "closed", "2026-04-01", "Azure Managed Redis", "azure_cache_retire",
     "New creation blocked since 1 Apr 2026; retirement 30 Sep 2028.")
life("Azure Spring Apps", [r"azure spring apps", r"azure spring cloud"], "closed", "2025-03-17", "Azure Container Apps", "azure_spring_apps",
     "Retirement announced; service retires 31 Mar 2028.")
# --- runtimes / languages / frameworks
life("Node.js 14/16/18", [r"node(\.js)? ?(v)?1[4-8]\b"], "eol", "2025-04-30", "Node.js 24 LTS", "nodejs_rel")
life("Node.js 20", [r"node(\.js)? ?(v)?20\b"], "eol", "2026-04-30", "Node.js 24 LTS", "nodejs_rel")
life("Node.js 22", [r"node(\.js)? ?(v)?22\b"], "extended", "2027-04-30", "Node.js 24 LTS", "nodejs_rel", "Maintenance LTS.")
life("Python 2", [r"python ?2(\.\d+)?\b"], "eol", "2020-01-01", "Python 3.13+", "python_versions")
life("Python 3.6-3.9", [r"python ?3\.[6-9]\b"], "eol", "2025-10-31", "Python 3.13+", "python_versions")
life("Python 3.10", [r"python ?3\.10\b"], "eol", "2026-10-31", "Python 3.13+", "python_versions")
life("PHP 5.x/7.x", [r"php ?[57](\.\d+)?\b"], "eol", "2022-11-28", "PHP 8.4", "php_versions")
life("PHP 8.0/8.1", [r"php ?8\.[01]\b"], "eol", "2025-12-31", "PHP 8.4", "php_versions")
life("Java 8", [r"java ?8\b", r"jdk ?8\b", r"java 1\.8"], "extended", "2030-12-31", "Java 21/25 LTS", "java_roadmap",
     "Vendor extended support only.")
life("Java 11", [r"java ?11\b", r"jdk ?11\b"], "extended", "2032-01-31", "Java 21/25 LTS", "java_roadmap", "Vendor extended support only.")
life("Python Django 3.2/4.2", [r"django ?(3\.2|4\.2|[123]\.\d)\b"], "eol", "2026-04-30", "Django 5.2 LTS", "endoflife")
life("Spring Boot 2.x", [r"spring boot ?2"], "eol", "2023-11-24", "Spring Boot 3.5/4", "spring")
life("AngularJS", [r"angular ?js", r"angular 1(\.\d+)?\b"], "eol", "2021-12-31", "Angular or React", "angularjs_eol")
life("Vue 2", [r"vue ?2\b", r"vue\.js 2\b"], "eol", "2023-12-31", "Vue 3", "vue2_eol")
life("Create React App", [r"create[- ]react[- ]app"], "eol", "2025-02-14", "Vite or a React framework", "cra_sunset")
life("Gatsby", [r"gatsby"], "maintenance", "2023-02-01", "Astro or Next.js", "gatsby", "Minimal release activity since 2023.")
life("Lucia auth", [r"\blucia\b"], "eol", "2025-03-01", "Better Auth / framework auth", "lucia")
# --- databases / OS
life("MySQL 5.7", [r"mysql ?5\.7"], "eol", "2023-10-31", "MySQL 8.4 LTS", "endoflife")
life("MySQL 8.0", [r"mysql ?8\.0"], "eol", "2026-04-30", "MySQL 8.4 LTS", "endoflife")
life("PostgreSQL 13 and older", [r"postgres(ql)? ?(9\.\d|1[0-3])\b"], "eol", "2025-11-13", "PostgreSQL 17/18", "pg_versioning")
life("PostgreSQL 14", [r"postgres(ql)? ?14\b"], "eol", "2026-11-12", "PostgreSQL 17/18", "pg_versioning")
life("MongoDB 6.0 and older", [r"mongo(db)? ?([1-5]\.\d|6\.0)\b"], "eol", "2025-07-31", "MongoDB 8", "endoflife")
life("Elasticsearch 7.x", [r"elasticsearch ?7"], "eol", "2026-01-15", "Elasticsearch 8/9 or OpenSearch", "endoflife")
life("CentOS 7/8", [r"centos ?[78]\b", r"centos linux"], "eol", "2024-06-30", "RHEL / AlmaLinux / Rocky Linux", "centos_eol")
life("Ubuntu 18.04/20.04", [r"ubuntu ?(18|20)\.04"], "eol", "2025-05-31", "Ubuntu 24.04 LTS", "ubuntu_cycle", "Standard support ended (ESM only).")
# --- SaaS / cloud services
life("Heroku", [r"heroku"], "maintenance", "2026-02-06", "Render / DigitalOcean / Cloud Run / ECS", "heroku_sustaining",
     "Sustaining-engineering model: no new features, Enterprise sales stopped for new customers.")
life("AWS App Runner", [r"app ?runner"], "closed", "2026-04-30", "Amazon ECS Express Mode", "apprunner_change")
life("MinIO Community Edition", [r"minio"], "eol", "2026-02-12", "SeaweedFS, Ceph RGW or managed S3", "minio_repo",
     "Repository archived; no community binaries or updates.")
life("MongoDB Atlas Device Sync / Realm Sync", [r"realm", r"device sync"], "eol", "2025-09-30", "PowerSync or a custom SQLite sync", "atlas_app_services")
life("MongoDB Atlas Data API", [r"atlas data api"], "eol", "2025-09-30", "A thin API service or Atlas drivers", "atlas_app_services")
life("Firebase Dynamic Links", [r"dynamic links"], "eol", "2025-08-25", "App Links / Universal Links", "fdl_faq")
life("Fauna", [r"\bfauna(db)?\b"], "eol", "2025-05-30", "PostgreSQL / DynamoDB", "fauna")
life("Google Cloud IoT Core", [r"iot core"], "eol", "2023-08-16", "EMQX / AWS IoT Core / Azure IoT Hub", "iot_core_retired")
life("AWS IoT Analytics", [r"iot analytics"], "eol", "2025-12-15", "AWS IoT Core rules + S3/Timestream", "aws_iot_analytics")
life("Google Universal Analytics", [r"universal analytics"], "eol", "2024-07-01", "GA4 or privacy-first analytics", "endoflife")

LIFECYCLE = L

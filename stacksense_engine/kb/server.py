"""Backend frameworks/BaaS, database engines, managed database offerings and hosting platforms."""
from .common import tech, price, REGIONS_ALL, REGIONS_NO_INDIA, HYPER_COMPLIANCE, REGION_NAMES

JS = ("javascript", "typescript")

# ================================================================== BACKEND
tech("nestjs", "NestJS (Node.js LTS, TypeScript)", "backend", kind="structured Node framework", langs=JS,
     s=(3, 4, 4, 5, 4, 4), learn=3, ops=2, mature=4, traits=("structured", "realtime_ok", "node"),
     strengths=["Modules + dependency injection map cleanly onto a modular monolith",
                "TypeScript end-to-end with web and React Native clients",
                "Built-in WebSocket gateways (Socket.IO) and queues (BullMQ)"],
     limits=["More boilerplate than minimal frameworks",
             "Single-threaded event loop: CPU-heavy work must go to workers"],
     src=["nestjs", "nodejs_rel", "so2025"], version="NestJS 11 on Node.js LTS",
     aliases=[r"nest\.?js"])
tech("fastify", "Fastify (Node.js LTS, TypeScript)", "backend", kind="minimal Node framework", langs=JS,
     s=(4, 4, 4, 3, 4, 4), learn=4, ops=2, mature=4, traits=("minimal", "realtime_ok", "node"),
     strengths=["High-throughput Node framework with JSON-schema validation"],
     limits=["Little structure: architecture discipline is on the team"], src=["fastify", "techempower"],
     aliases=[r"fastify"])
tech("express", "Express (Node.js LTS)", "backend", kind="minimal Node framework", langs=JS,
     s=(3, 3, 4, 3, 4, 3), learn=5, ops=2, mature=5, traits=("minimal", "realtime_ok", "node"),
     strengths=["Ubiquitous; simplest learning curve"],
     limits=["Minimal structure and slower than Fastify", "Easy to grow into an unstructured codebase"],
     src=["express", "so2025"], aliases=[r"express(\.js)?"])
tech("nextjs_api", "Next.js full-stack (Route Handlers + Server Actions)", "backend", kind="full-stack framework",
     langs=JS, s=(3, 4, 5, 3, 4, 3), learn=3, ops=1, mature=4, traits=("fullstack", "no_websockets", "node"),
     strengths=["One codebase and deploy for UI and API", "Server actions remove an API layer for simple CRUD"],
     limits=["No persistent WebSockets on serverless hosts",
             "Business logic coupled to the UI framework's release cycle"], src=["nextjs"])
tech("django", "Django (Python)", "backend", kind="batteries-included framework", langs=("python",),
     s=(3, 4, 5, 5, 4, 5), learn=3, ops=2, mature=5, traits=("structured", "batteries", "admin", "python_ml"),
     strengths=["ORM, migrations, admin and auth built in",
                "Python ML ecosystem sits next to the app"],
     limits=["Sync-first; WebSockets need Channels/ASGI", "Heavier conventions for tiny services"],
     src=["django", "so2025"], version="Django 5.2 LTS", aliases=[r"django"])
tech("fastapi", "FastAPI (Python)", "backend", kind="async Python framework", langs=("python",),
     s=(4, 4, 4, 4, 4, 4), learn=4, ops=2, mature=4, traits=("minimal", "realtime_ok", "python_ml"),
     strengths=["Async Python with automatic OpenAPI docs", "Natural home for ML model serving"],
     limits=["Fewer built-ins (admin, auth) than Django"], src=["fastapi", "so2025"], aliases=[r"fastapi"])
tech("spring_boot", "Spring Boot (Java/Kotlin, JVM LTS)", "backend", kind="enterprise JVM framework",
     langs=("java", "kotlin"), s=(4, 5, 3, 5, 3, 5), learn=2, ops=2, mature=5,
     traits=("structured", "enterprise", "acid_strong", "realtime_ok"),
     strengths=["Mature declarative transactions for ACID ledgers",
                "Spring Security and a long compliance track record in banking",
                "JVM observability and performance tooling"],
     limits=["Higher memory footprint and slower cold starts", "More ceremony for small apps"],
     src=["spring", "java_roadmap", "so2025"], version="Spring Boot 3.5/4 on Java 21/25 LTS",
     aliases=[r"spring"])
tech("aspnet_core", "ASP.NET Core (.NET 10 LTS)", "backend", kind="enterprise .NET framework", langs=("csharp", "fsharp"),
     s=(5, 5, 4, 5, 4, 5), learn=3, ops=2, mature=5,
     traits=("structured", "enterprise", "realtime_ok", "entra_native", "acid_strong"),
     strengths=["Top-tier throughput in TechEmpower benchmarks",
                "Microsoft.Identity.Web for Entra ID SSO in a few lines",
                "SignalR for realtime"],
     limits=["Best tooling on Windows/Azure (runs everywhere)"],
     src=["aspnet", "dotnet_policy", "techempower", "ms_identity_web"], version=".NET 10 LTS",
     aliases=[r"asp\.?net", r"\.net core"])
tech("go_chi", "Go (net/http + chi)", "backend", kind="compiled Go service", langs=("go",),
     s=(5, 5, 3, 4, 5, 4), learn=3, ops=2, mature=5, traits=("minimal", "realtime_strong", "low_memory"),
     strengths=["Goroutines hold 10k+ concurrent WebSockets per node cheaply",
                "Single static binary, low memory, predictable latency"],
     limits=["Fewer batteries: more code for CRUD/admin", "Verbose error handling slows feature work"],
     src=["go", "chi", "techempower"], version="Go 1.2x", aliases=[r"\bgolang\b", r"\bgo service"])
tech("laravel", "Laravel (PHP 8.4)", "backend", kind="batteries-included framework", langs=("php",),
     s=(3, 3, 5, 4, 4, 4), learn=4, ops=2, mature=5, traits=("structured", "batteries", "realtime_ok"),
     strengths=["Queues, auth, mail and Reverb WebSockets built in"],
     limits=["Per-request PHP model needs care for long-lived connections"], src=["laravel", "php_versions"],
     aliases=[r"laravel"])
tech("rails", "Ruby on Rails", "backend", kind="batteries-included framework", langs=("ruby",),
     s=(3, 3, 5, 4, 4, 4), learn=4, ops=2, mature=5, traits=("structured", "batteries", "realtime_ok"),
     strengths=["Fast CRUD productivity; Hotwire and Action Cable"],
     limits=["Smaller hiring pool than Node/Python/Java"], src=["rails"], aliases=[r"rails"])
tech("phoenix", "Phoenix (Elixir)", "backend", kind="realtime framework", langs=("elixir",),
     s=(5, 5, 4, 4, 4, 4), learn=2, ops=2, mature=4, traits=("structured", "realtime_strong"),
     strengths=["Channels + Presence scale to millions of connections on the BEAM"],
     limits=["Elixir skills are rare"], src=["phoenix"])
tech("axum", "Rust (axum)", "backend", kind="compiled Rust service", langs=("rust",),
     s=(5, 5, 2, 4, 5, 5), learn=1, ops=2, mature=3, traits=("minimal", "realtime_strong", "low_memory"),
     strengths=["Maximum performance with memory safety"], limits=["Steep learning curve; slower iteration"],
     src=["axum", "techempower"])
tech("supabase", "Supabase (managed Postgres + Auth + Storage + Realtime)", "backend", kind="BaaS",
     langs=JS + ("sql",), s=(3, 4, 5, 3, 5, 4), learn=4, ops=1, mature=4, provider="supabase",
     traits=("baas", "auth", "realtime_ok", "storage", "postgres", "rls", "phone_otp"),
     regions=REGIONS_ALL, compliance=("gdpr", "dpdp", "soc2", "hipaa"), lock="medium",
     strengths=["Postgres, Auth (incl. phone OTP), Storage and Realtime in one managed project",
                "Row-Level Security policies isolate tenants in the database",
                "Open source: can be self-hosted later to exit"],
     limits=["Complex workflows end up in Edge Functions or SQL functions",
             "supabase.co was ISP-blocked in India in Feb 2026 (a custom domain mitigates)",
             "HIPAA requires the Team plan plus a BAA add-on"],
     src=["supabase", "supabase_regions", "supabase_pricing", "supabase_block"],
     region_names=REGION_NAMES["supabase"])
tech("firebase", "Firebase (Firestore + Auth + Functions)", "backend", kind="BaaS", langs=JS + ("dart", "kotlin", "swift"),
     s=(4, 5, 5, 3, 4, 4), learn=5, ops=1, mature=5, provider="gcp",
     traits=("baas", "auth", "realtime_ok", "storage", "offline_sync", "push", "phone_otp", "auth_global"),
     regions=REGIONS_ALL, compliance=("gdpr", "soc2", "iso27001", "dpdp"), lock="high", self_host=False, saas=True,
     strengths=["Firestore offline persistence and realtime listeners out of the box",
                "Generous free tier; FCM push notifications included"],
     limits=["Proprietary data model and APIs (high lock-in)",
             "Firebase Authentication offers no data-location choice",
             "Weak at relational queries and reporting"],
     src=["firebase", "firebase_locations", "firebase_pricing", "firestore_offline"],
     region_names=REGION_NAMES["firebase"])
tech("appwrite", "Appwrite", "backend", kind="BaaS", langs=JS + ("python", "dart"), s=(3, 3, 5, 3, 4, 4),
     learn=4, ops=2, mature=3, provider="appwrite", traits=("baas", "auth", "realtime_ok", "storage"),
     regions=REGIONS_NO_INDIA, compliance=("gdpr", "soc2"), lock="low",
     strengths=["Open-source BaaS that can be self-hosted"], limits=["Smaller ecosystem; few cloud regions"],
     src=["appwrite"], region_names=REGION_NAMES["appwrite"])
tech("pocketbase", "PocketBase", "backend", kind="single-binary BaaS", langs=("go", "javascript"),
     s=(4, 2, 5, 3, 5, 3), learn=5, ops=3, mature=2, traits=("baas", "auth", "realtime_ok", "single_node"),
     users_max=10000, lock="low",
     strengths=["One Go binary with SQLite, auth, files and realtime"],
     limits=["Single node only; pre-1.0 so breaking changes are possible"], src=["pocketbase"])
tech("functions", "Serverless functions", "backend", kind="FaaS", langs=JS + ("python", "go", "java", "csharp"),
     s=(4, 5, 5, 3, 5, 4), learn=4, ops=1, mature=5, traits=("functions", "no_websockets"), self_host=False,
     strengths=["Zero idle cost; scales per request", "Ideal for small handlers (forms, webhooks)"],
     limits=["No persistent connections", "Cold starts and execution time limits"], src=["lambda", "cloudrun", "netlify"])

# ================================================================== DATABASE ENGINES
tech("postgresql", "PostgreSQL", "database", kind="relational", langs=("sql",), s=(4, 4, 4, 5, 4, 5), learn=3, ops=3,
     mature=5, traits=("relational", "acid", "json", "fts", "geo", "rls", "vector", "extensions"),
     strengths=["ACID transactions, constraints and rich SQL",
                "Extensions: PostGIS (geo), pgvector (embeddings), built-in full-text search",
                "Row-level security for multi-tenant isolation",
                "Available as a managed service on every major cloud"],
     limits=["Single-writer primary: write scale beyond one large node needs partitioning/sharding",
             "Vacuum and connection pooling need attention at scale"],
     src=["postgres", "pg_fts", "postgis", "pg_rls", "pgvector", "dbengines", "so2025"], version="PostgreSQL 17/18",
     aliases=[r"postgres"])
tech("mysql", "MySQL", "database", kind="relational", langs=("sql",), s=(4, 4, 4, 4, 4, 4), learn=4, ops=3, mature=5,
     traits=("relational", "acid", "fts_basic"),
     strengths=["Ubiquitous relational database with mature managed offerings"],
     limits=["Fewer extensions than PostgreSQL (no PostGIS/pgvector equivalents)", "MySQL 8.0 reached EOL in April 2026: use 8.4 LTS"],
     src=["mysql", "dbengines", "endoflife"], version="MySQL 8.4 LTS", aliases=[r"mysql", r"mariadb"])
tech("sqlserver", "SQL Server (Azure SQL)", "database", kind="relational", langs=("sql", "csharp"),
     s=(4, 4, 4, 4, 2, 5), learn=3, ops=3, mature=5, traits=("relational", "acid", "fts_basic", "microsoft"),
     strengths=["Deep .NET/Entity Framework integration", "Azure SQL is fully managed with built-in HA"],
     limits=["Licence cost outside Azure SQL's managed tiers"],
     src=["azure_sql", "sqlserver2019", "dbengines"], aliases=[r"sql ?server", r"mssql", r"azure sql"])
tech("mongodb", "MongoDB", "database", kind="document", langs=("javascript", "typescript", "python"),
     s=(4, 5, 5, 3, 3, 4), learn=4, ops=3, mature=5, traits=("document", "fts_atlas", "geo", "flexible_schema", "vector"),
     lock="medium",
     strengths=["Flexible documents speed up early iteration", "Atlas Search and geo queries built in"],
     limits=["Multi-document transactions are possible but relational integrity is on the app",
             "SSPL licence for self-managed deployments"],
     src=["mongodb", "atlas_pricing", "dbengines"], version="MongoDB 8", aliases=[r"mongo"])
tech("firestore", "Cloud Firestore", "database", kind="document (serverless)", langs=JS + ("dart", "kotlin", "swift"),
     s=(4, 5, 5, 3, 4, 4), learn=5, ops=1, mature=5, provider="gcp",
     traits=("document", "offline_sync", "realtime", "serverless_db"), lock="high", self_host=False, saas=True,
     regions=REGIONS_ALL, compliance=("gdpr", "soc2", "iso27001", "dpdp", "hipaa"),
     strengths=["Client SDKs sync offline and stream realtime updates"],
     limits=["Limited querying/joins; reporting needs exports", "Proprietary (high lock-in)"],
     src=["firestore", "firestore_offline"], region_names=REGION_NAMES["firebase"])
tech("dynamodb", "Amazon DynamoDB", "database", kind="key-value (serverless)", langs=(), s=(5, 5, 3, 3, 4, 5),
     learn=2, ops=1, mature=5, provider="aws", traits=("kv", "serverless_db", "write_scale"), lock="high",
     self_host=False, saas=True, regions=REGIONS_ALL, compliance=HYPER_COMPLIANCE,
     strengths=["Single-digit-ms latency at any scale", "On-demand capacity, global tables"],
     limits=["Access patterns must be designed up front (single-table design)", "AWS-only"],
     src=["dynamodb"], region_names=REGION_NAMES["aws"])
tech("cosmosdb", "Azure Cosmos DB", "database", kind="multi-model (serverless)", langs=(), s=(5, 5, 3, 3, 2, 5),
     learn=2, ops=1, mature=4, provider="azure", traits=("document", "serverless_db", "write_scale", "multi_region"),
     lock="high", self_host=False, saas=True, regions=REGIONS_ALL, compliance=HYPER_COMPLIANCE,
     strengths=["Turnkey multi-region writes with SLAs"], limits=["RU-based pricing is easy to overspend", "Azure-only"],
     src=["cosmos"], region_names=REGION_NAMES["azure"])
tech("cassandra", "Apache Cassandra / ScyllaDB", "database", kind="wide-column", langs=(), s=(5, 5, 2, 3, 3, 4),
     learn=1, ops=5, mature=5, traits=("wide_column", "write_scale", "multi_region"), users_min=2_000_000,
     strengths=["Linear write scalability across data centres"],
     limits=["Query-driven data modelling; no joins", "Heavy operational burden unless managed"],
     src=["cassandra", "scylla"], aliases=[r"cassandra", r"scylla"])
tech("sqlite", "SQLite (embedded) + Litestream", "database", kind="embedded relational", langs=("sql",),
     s=(5, 1, 5, 4, 5, 4), learn=5, ops=1, mature=5, traits=("relational", "embedded", "single_node"),
     users_max=5000,
     strengths=["Zero-ops embedded database; Litestream streams backups to object storage"],
     limits=["Single writer; one server only"], src=["sqlite", "litestream"])
tech("timescaledb", "TimescaleDB (PostgreSQL extension)", "database", kind="time-series", langs=("sql",),
     s=(5, 4, 4, 4, 4, 4), learn=3, ops=3, mature=4, traits=("relational", "acid", "timeseries", "fts", "geo"),
     strengths=["Hypertables and compression for telemetry on plain Postgres"],
     limits=["Managed service availability varies by region"], src=["timescale"], aliases=[r"timescale"])
tech("clickhouse", "ClickHouse", "database", kind="columnar OLAP", langs=("sql",), s=(5, 5, 3, 4, 4, 4), learn=3,
     ops=3, mature=4, traits=("olap",), users_min=0,
     strengths=["Sub-second aggregations over billions of rows"],
     limits=["Not for transactional workloads (no row-level updates)"], src=["clickhouse"], aliases=[r"clickhouse"])
tech("bigquery", "Google BigQuery", "database", kind="serverless warehouse", langs=("sql",), s=(4, 5, 4, 4, 3, 5),
     learn=4, ops=1, mature=5, provider="gcp", traits=("olap", "serverless_db"), lock="high", self_host=False,
     saas=True, regions=REGIONS_ALL, compliance=HYPER_COMPLIANCE,
     strengths=["Serverless SQL warehouse, pay per query"], limits=["Not an OLTP store; per-scan pricing"],
     src=["bigquery"], region_names=REGION_NAMES["gcp"])
tech("cockroachdb", "CockroachDB", "database", kind="distributed SQL", langs=("sql",), s=(4, 5, 3, 4, 2, 5), learn=3,
     ops=3, mature=4, traits=("relational", "acid", "multi_region", "distributed"), users_min=500_000,
     strengths=["Postgres-wire distributed SQL with multi-region survival goals"],
     limits=["Higher latency per transaction than single-node Postgres", "Enterprise licence terms"],
     src=["cockroach"])
tech("fauna", "Fauna", "database", kind="serverless document", status="eol",
     status_note="Fauna shut down its service in May 2025.", src=["fauna"], aliases=[r"fauna"])

# ================================================================== MANAGED DATABASE OFFERINGS
# kind = engine id. provider = platform family. price = DB footprint per tier (excl. storage GB).

def offering(id, name, engine, provider, *, regions=REGIONS_ALL, compliance=HYPER_COMPLIANCE, cost, ops=1,
             traits=(), src=(), lock="low", self_host=False, region_names=None, status="active", status_note="",
             limits=(), strengths=()):
    return tech(id, name, "db_offering", kind=engine, provider=provider, regions=regions, compliance=compliance,
                cost=cost, ops=ops, traits=traits, src=src, lock=lock, self_host=self_host, saas=not self_host,
                region_names=region_names or REGION_NAMES.get(provider, {}), status=status,
                status_note=status_note, limits=limits, strengths=strengths)


AWS_RDS = price((13, 30), (30, 90), (150, 450), (500, 1800), (2000, 8000))
offering("rds_pg", "Amazon RDS for PostgreSQL", "postgresql", "aws", cost=AWS_RDS, traits=("ha", "pitr"),
         src=["rds_pg_pricing", "rds_sla", "aws_compliance"])
offering("aurora_pg", "Amazon Aurora PostgreSQL", "postgresql", "aws",
         cost=price((60, 120), (120, 250), (250, 700), (700, 2500), (2500, 10000)), traits=("ha", "pitr", "multi_region"),
         src=["aurora", "aws_compliance"])
offering("cloudsql_pg", "Cloud SQL for PostgreSQL", "postgresql", "gcp",
         cost=price((9, 30), (30, 90), (150, 450), (500, 1800), (2000, 8000)), traits=("ha", "pitr"),
         src=["cloudsql", "cloudsql_pricing", "gcp_compliance"])
offering("azure_pg", "Azure Database for PostgreSQL (Flexible Server)", "postgresql", "azure",
         cost=price((13, 30), (30, 100), (150, 450), (500, 1800), (2000, 8000)), traits=("ha", "pitr"),
         src=["azure_pg", "azure_compliance"])
offering("supabase_pg", "Supabase Postgres", "postgresql", "supabase", regions=REGIONS_ALL,
         compliance=("gdpr", "dpdp", "soc2", "hipaa"),
         cost=price((0, 25), (25, 60), (85, 400), (400, 1500), (1500, 5000)), traits=("pitr_addon",),
         src=["supabase_pricing", "supabase_regions"], lock="medium")
offering("neon_pg", "Neon serverless Postgres", "postgresql", "neon", regions=REGIONS_NO_INDIA,
         compliance=("gdpr", "soc2", "iso27001", "hipaa"),
         cost=price((0, 0), (19, 69), (69, 300), (300, 1200), (1200, 4000)), traits=("scale_to_zero", "branching", "pitr"),
         src=["neon_regions"])
offering("do_pg", "DigitalOcean Managed PostgreSQL", "postgresql", "digitalocean", compliance=("gdpr", "dpdp", "soc2"),
         cost=price((15, 15), (15, 60), (60, 250), (250, 1000), (1000, 4000)), traits=("ha",),
         src=["do_db", "do_regions"])
offering("render_pg", "Render Postgres", "postgresql", "render", regions=REGIONS_NO_INDIA, compliance=("gdpr", "soc2"),
         cost=price((6, 20), (20, 95), (95, 400), (400, 1500), (1500, 5000)), traits=("ha",), src=["render_pg", "render_regions"])
offering("railway_pg", "Railway Postgres", "postgresql", "railway", regions=REGIONS_NO_INDIA, compliance=("gdpr", "soc2"),
         cost=price((5, 10), (10, 40), (40, 200), (200, 800), (800, 3000)), src=["railway", "railway_regions"])
offering("self_pg", "Self-managed PostgreSQL (Patroni/pgBackRest)", "postgresql", "self", self_host=True, ops=4,
         compliance=HYPER_COMPLIANCE, cost=price((0, 10), (10, 40), (40, 150), (150, 600), (600, 2400)),
         traits=("ha_manual",), src=["postgres"])
offering("rds_mysql", "Amazon RDS for MySQL", "mysql", "aws", cost=AWS_RDS, traits=("ha", "pitr"), src=["aws_compliance"])
offering("cloudsql_mysql", "Cloud SQL for MySQL", "mysql", "gcp",
         cost=price((9, 30), (30, 90), (150, 450), (500, 1800), (2000, 8000)), traits=("ha", "pitr"), src=["cloudsql"])
offering("azure_mysql", "Azure Database for MySQL (Flexible Server)", "mysql", "azure",
         cost=price((13, 30), (30, 100), (150, 450), (500, 1800), (2000, 8000)), traits=("ha", "pitr"),
         src=["azure_compliance"])
offering("do_mysql", "DigitalOcean Managed MySQL", "mysql", "digitalocean", compliance=("gdpr", "dpdp", "soc2"),
         cost=price((15, 15), (15, 60), (60, 250), (250, 1000), (1000, 4000)), traits=("ha",), src=["do_db"])
offering("self_mysql", "Self-managed MySQL 8.4 LTS", "mysql", "self", self_host=True, ops=4,
         cost=price((0, 10), (10, 40), (40, 150), (150, 600), (600, 2400)), src=["mysql"])
offering("azure_sql_db", "Azure SQL Database", "sqlserver", "azure",
         cost=price((5, 15), (15, 75), (150, 500), (500, 2000), (2000, 8000)), traits=("ha", "pitr", "serverless_tier"),
         src=["azure_sql", "azure_compliance"])
offering("rds_sqlserver", "Amazon RDS for SQL Server", "sqlserver", "aws",
         cost=price((30, 80), (80, 250), (300, 900), (900, 3000), (3000, 10000)), traits=("ha",), src=["aws_compliance"])
offering("self_sqlserver", "SQL Server 2022 (self-managed)", "sqlserver", "self", self_host=True, ops=4,
         cost=price((0, 20), (20, 80), (80, 300), (300, 1000), (1000, 4000)), src=["sqlserver2019"])
offering("atlas", "MongoDB Atlas", "mongodb", "mongodb", regions=REGIONS_ALL, compliance=HYPER_COMPLIANCE,
         cost=price((0, 0), (0, 57), (57, 400), (400, 1500), (1500, 6000)), traits=("ha", "pitr"),
         src=["atlas_pricing"], lock="medium")
offering("self_mongo", "Self-managed MongoDB Community", "mongodb", "self", self_host=True, ops=4,
         cost=price((0, 10), (10, 40), (40, 150), (150, 600), (600, 2400)), src=["mongodb"])
offering("firestore_off", "Cloud Firestore", "firestore", "gcp", compliance=("gdpr", "soc2", "iso27001", "dpdp", "hipaa"),
         cost=price((0, 1), (1, 25), (25, 200), (200, 1500), (1500, 8000)), traits=("ha", "serverless"), lock="high",
         src=["firestore", "firebase_pricing"])
offering("dynamodb_off", "Amazon DynamoDB (on-demand)", "dynamodb", "aws",
         cost=price((0, 1), (1, 25), (25, 250), (250, 2000), (2000, 10000)), traits=("ha", "serverless"), lock="high",
         src=["dynamodb"])
offering("cosmos_off", "Azure Cosmos DB", "cosmosdb", "azure",
         cost=price((0, 25), (25, 100), (100, 600), (600, 3000), (3000, 12000)), traits=("ha", "serverless"), lock="high",
         src=["cosmos"])
offering("keyspaces", "Amazon Keyspaces (Cassandra-compatible)", "cassandra", "aws",
         cost=price((5, 20), (20, 100), (150, 600), (600, 2500), (2500, 10000)), traits=("ha", "serverless"), src=["cassandra"])
offering("self_cassandra", "Self-managed Cassandra/ScyllaDB cluster", "cassandra", "self", self_host=True, ops=5,
         cost=price((60, 150), (150, 300), (300, 1200), (1200, 4000), (4000, 15000)), src=["scylla"])
offering("sqlite_embedded", "SQLite on the app server + Litestream to object storage", "sqlite", "self", self_host=True,
         ops=2, cost=price((0, 1), (0, 2), (0, 5), (0, 5), (0, 5)), compliance=HYPER_COMPLIANCE, src=["sqlite", "litestream"])
offering("timescale_cloud", "Timescale Cloud (TigerData)", "timescaledb", "timescale", regions=REGIONS_ALL,
         compliance=("gdpr", "soc2", "hipaa"), cost=price((30, 60), (60, 150), (150, 600), (600, 2500), (2500, 9000)),
         traits=("ha",), src=["timescale"])
offering("self_timescale", "Self-managed TimescaleDB", "timescaledb", "self", self_host=True, ops=4,
         cost=price((0, 10), (10, 40), (40, 150), (150, 600), (600, 2400)), src=["timescale"])
offering("clickhouse_cloud", "ClickHouse Cloud", "clickhouse", "clickhouse", regions=REGIONS_ALL,
         compliance=("gdpr", "soc2", "iso27001", "hipaa", "pci_dss"),
         cost=price((50, 200), (100, 300), (300, 1000), (1000, 4000), (4000, 15000)), src=["clickhouse"])
offering("self_clickhouse", "Self-managed ClickHouse", "clickhouse", "self", self_host=True, ops=4,
         cost=price((10, 40), (40, 150), (150, 600), (600, 2400), (2400, 9000)), src=["clickhouse"])
offering("bigquery_off", "BigQuery", "bigquery", "gcp", cost=price((0, 20), (20, 100), (100, 500), (500, 2500), (2500, 10000)),
         traits=("serverless",), lock="high", src=["bigquery"])
offering("cockroach_cloud", "CockroachDB Cloud", "cockroachdb", "cockroach", regions=REGIONS_ALL,
         compliance=("gdpr", "soc2", "iso27001", "hipaa", "pci_dss"),
         cost=price((0, 50), (100, 300), (300, 1200), (1200, 5000), (5000, 20000)), traits=("ha", "multi_region"),
         src=["cockroach"])
offering("self_cockroach", "Self-managed CockroachDB", "cockroachdb", "self", self_host=True, ops=4,
         cost=price((30, 90), (90, 200), (200, 800), (800, 3000), (3000, 12000)), src=["cockroach"])

# ================================================================== HOSTING
STATIC_FREE = price((0, 0), (0, 0), (0, 5), (5, 25), (25, 200))


def host(id, name, provider, *, s, learn=4, ops=1, mature=4, traits=(), regions=REGIONS_ALL, compliance=(),
         cost, src=(), status="active", status_note="", strengths=(), limits=(), self_host=False, cloud=None,
         users_max=None, users_min=0, aliases=(), region_names=None):
    t = tech(id, name, "hosting", kind=cloud or provider, provider=provider, s=s, learn=learn, ops=ops,
             mature=mature, traits=traits, regions=regions, compliance=compliance, cost=cost, src=src,
             status=status, status_note=status_note, strengths=strengths, limits=limits, self_host=self_host,
             saas=not self_host, users_max=users_max, users_min=users_min, aliases=aliases,
             region_names=region_names or REGION_NAMES.get(provider, {}))
    return t


host("github_pages", "GitHub Pages", "github", s=(4, 4, 4, 4, 5, 4), learn=4, traits=("static", "git_deploy"),
     regions=(), cost=price((0, 0), (0, 0), (0, 0), (0, 0), (0, 0)), users_max=1_000_000,
     strengths=["Free static hosting straight from a Git repository", "Official Astro/Hugo deploy actions"],
     limits=["Static only; 100 GB/month soft bandwidth limit", "Not intended for commercial SaaS/e-commerce"],
     src=["gh_pages"])
host("cloudflare", "Cloudflare (Workers static assets / Pages)", "cloudflare", s=(5, 5, 4, 4, 5, 4), learn=4,
     traits=("static", "functions", "edge", "global_edge", "git_deploy", "no_websockets_default"), regions=(),
     compliance=("gdpr", "soc2", "iso27001", "pci_dss"),
     cost=price((0, 0), (0, 5), (0, 25), (5, 100), (5, 500)),
     strengths=["Static asset requests are free and unmetered on the global edge network",
                "Workers for edge functions if dynamic needs appear later"],
     limits=["Workers run in every PoP: personal-data residency cannot be pinned on standard plans",
             "Cloudflare now steers new projects from Pages to Workers static assets"],
     src=["cf_static", "cf_pages_migrate", "cf_pricing"])
host("netlify", "Netlify", "netlify", s=(4, 4, 5, 4, 4, 4), learn=5,
     traits=("static", "functions", "ssr_ok", "git_deploy", "forms"), regions=("us",), compliance=("gdpr", "soc2"),
     cost=price((0, 0), (0, 19), (19, 99), (99, 500), (500, 2000)),
     strengths=["Simplest Git-to-production flow; deploy previews", "Built-in forms and functions"],
     limits=["Functions default to a US region", "Credit-based usage limits on the free plan"],
     src=["netlify", "netlify_pricing"])
host("vercel", "Vercel", "vercel", s=(5, 5, 5, 4, 3, 4), learn=5,
     traits=("static", "functions", "ssr_native", "git_deploy", "edge", "no_websockets"), regions=REGIONS_ALL,
     compliance=("gdpr", "soc2", "iso27001", "dpdp"), cost=price((0, 0), (20, 60), (60, 300), (300, 1500), (1500, 6000)),
     strengths=["Native Next.js host: SSR/ISR, previews, image optimisation",
                "Function regions selectable (incl. bom1 Mumbai, fra1 Frankfurt)"],
     limits=["Hobby plan is non-commercial; Pro is billed per member",
             "Functions cannot hold WebSocket connections", "Usage-based bills can spike with traffic"],
     src=["vercel", "vercel_regions", "vercel_pricing", "vercel_fair_use"])
host("firebase_hosting", "Firebase Hosting", "gcp", s=(4, 4, 5, 4, 4, 4), learn=5, traits=("static", "functions", "git_deploy"),
     regions=REGIONS_ALL, compliance=("gdpr", "soc2", "iso27001", "dpdp"), cost=STATIC_FREE,
     strengths=["Global CDN static hosting with Cloud Functions/Cloud Run rewrites"],
     limits=["Best within the Firebase ecosystem"], src=["firebase_hosting"])
host("azure_swa", "Azure Static Web Apps", "azure", s=(4, 4, 4, 4, 5, 4), learn=3,
     traits=("static", "functions", "git_deploy", "entra_auth"), regions=("eu", "us", "other"),
     compliance=HYPER_COMPLIANCE, cost=price((0, 0), (0, 9), (9, 50), (50, 300), (300, 1500)),
     strengths=["Free/Standard static hosting with built-in Entra ID auth"],
     limits=["Managed Functions only in a few regions (no India): pair with App Service for in-country APIs"],
     src=["azure_swa"])
host("amplify", "AWS Amplify Hosting", "aws", s=(4, 4, 5, 4, 4, 4), learn=4, traits=("static", "ssr_ok", "git_deploy"),
     compliance=HYPER_COMPLIANCE, cost=price((0, 5), (5, 25), (25, 120), (120, 600), (600, 3000)),
     strengths=["Git-based static/SSR hosting inside an AWS account"], limits=["Less flexible than containers for APIs"],
     src=["amplify"])
host("s3_cloudfront", "Amazon S3 + CloudFront", "aws", s=(5, 5, 3, 4, 5, 5), learn=3, ops=2, traits=("static", "cdn"),
     compliance=HYPER_COMPLIANCE, cost=price((0, 1), (1, 5), (5, 40), (40, 300), (300, 2000)),
     strengths=["Static hosting on AWS with CloudFront's 1 TB/month always-free tier"],
     limits=["More setup (OAC, certificates, invalidations) than Git-based hosts"], src=["cloudfront", "cloudfront_pricing"])
host("render", "Render", "render", s=(4, 4, 5, 4, 4, 4), learn=5,
     traits=("containers", "websockets", "managed_paas", "git_deploy", "static"), regions=REGIONS_NO_INDIA,
     compliance=("gdpr", "soc2"), cost=price((0, 7), (14, 50), (85, 300), (300, 1200), (1200, 5000)),
     strengths=["Heroku-like simplicity with managed Postgres/Redis", "WebSockets and background workers"],
     limits=["Regions: Oregon, Ohio, Virginia, Frankfurt, Singapore (no India)"], src=["render", "render_regions", "render_pricing"])
host("railway", "Railway", "railway", s=(4, 4, 5, 3, 4, 3), learn=5,
     traits=("containers", "websockets", "managed_paas", "git_deploy"), regions=REGIONS_NO_INDIA,
     compliance=("gdpr", "soc2"), cost=price((5, 10), (10, 50), (60, 250), (250, 1000), (1000, 4000)),
     strengths=["Very fast setup; usage-based billing"], limits=["No India region", "Younger platform for regulated workloads"],
     src=["railway", "railway_regions"])
host("flyio", "Fly.io", "fly", s=(5, 4, 4, 4, 4, 4), learn=3, ops=2,
     traits=("containers", "websockets", "udp", "global_edge", "multi_region_easy", "sticky"), regions=REGIONS_NO_INDIA,
     compliance=("gdpr", "soc2"), cost=price((0, 10), (10, 50), (60, 300), (300, 1200), (1200, 5000)),
     strengths=["Run containers close to users in many regions", "Good fit for stateful WebSocket rooms (fly-replay routing)"],
     limits=["Mumbai (bom) is listed in Fly's region-consolidation project: no dependable India region",
             "More hands-on than classic PaaS"], src=["fly_regions", "fly_consolidation"])
host("do_app", "DigitalOcean App Platform", "digitalocean", s=(4, 4, 5, 4, 4, 4), learn=5,
     traits=("containers", "websockets", "managed_paas", "git_deploy", "static"), regions=REGIONS_ALL,
     compliance=("gdpr", "dpdp", "soc2"), cost=price((0, 5), (12, 50), (60, 250), (250, 1000), (1000, 4000)),
     strengths=["Simple PaaS with a Bangalore (BLR1) region", "Managed Postgres/Redis/Spaces in the same region"],
     limits=["Fewer compliance attestations than hyperscalers (no PCI DSS/HIPAA)", "Limited autoscaling controls"],
     src=["do_app", "do_regions"])
host("cloud_run", "Google Cloud Run", "gcp", s=(4, 5, 4, 4, 5, 5), learn=4, ops=1,
     traits=("containers", "websockets", "autoscale", "scale_to_zero", "multi_az", "managed_paas"),
     compliance=HYPER_COMPLIANCE, cost=price((0, 5), (5, 40), (60, 300), (300, 1500), (1500, 6000)),
     strengths=["Containers with per-request autoscaling and scale-to-zero",
                "Regional (multi-zone) by default; WebSockets supported"],
     limits=["WebSocket connections capped by request timeout (max 60 min): clients must reconnect",
             "Session affinity is best-effort for stateful rooms"],
     src=["cloudrun", "cloudrun_pricing", "cloudrun_ws", "gcp_regions"])
host("app_service", "Azure App Service", "azure", s=(4, 4, 4, 4, 3, 5), learn=4, ops=1,
     traits=("containers", "websockets", "managed_paas", "dotnet_native", "hybrid_connectivity", "multi_az", "entra_auth", "sticky"),
     compliance=HYPER_COMPLIANCE, cost=price((13, 15), (13, 75), (75, 300), (300, 1500), (1500, 6000)),
     strengths=["First-class .NET hosting with deployment slots",
                "Hybrid Connections reach on-prem systems (e.g. SQL Server) without a VPN",
                "Built-in Entra ID authentication"],
     limits=["Per-plan pricing, no scale-to-zero"], src=["appservice", "appservice_hybrid", "appservice_pricing"])
host("container_apps", "Azure Container Apps", "azure", s=(4, 5, 4, 4, 5, 5), learn=3, ops=2,
     traits=("containers", "websockets", "autoscale", "scale_to_zero", "multi_az"), compliance=HYPER_COMPLIANCE,
     cost=price((0, 10), (10, 50), (60, 300), (300, 1500), (1500, 6000)),
     strengths=["Serverless containers with KEDA autoscaling and Dapr"], limits=["More moving parts than App Service"],
     src=["aca"])
host("ecs_fargate", "AWS ECS on Fargate", "aws", s=(4, 5, 3, 4, 3, 5), learn=3, ops=3,
     traits=("containers", "websockets", "autoscale", "multi_az", "udp", "sticky"), compliance=HYPER_COMPLIANCE,
     cost=price((40, 70), (70, 150), (150, 500), (500, 2000), (2000, 8000)),
     strengths=["Serverless containers across multiple AZs, no cluster to manage",
                "Full AWS security tooling (IAM, KMS, WAF, GuardDuty) for regulated workloads",
                "ECS Express Mode is AWS's recommended App Runner replacement"],
     limits=["VPC, load balancer and NAT setup add fixed cost and complexity"],
     src=["fargate", "fargate_pricing", "apprunner_change"])
host("lambda", "AWS Lambda + API Gateway", "aws", s=(4, 5, 4, 3, 5, 5), learn=3, ops=2,
     traits=("functions", "autoscale", "scale_to_zero", "multi_az", "no_websockets"), compliance=HYPER_COMPLIANCE,
     cost=price((0, 5), (5, 30), (30, 200), (200, 1500), (1500, 8000)),
     strengths=["Pay-per-request; scales to zero"], limits=["Cold starts (JVM especially)", "15-minute limit; WebSockets need API Gateway WebSocket APIs"],
     src=["lambda"])
host("beanstalk", "AWS Elastic Beanstalk", "aws", s=(4, 4, 3, 2, 4, 4), learn=4, ops=2,
     traits=("containers", "websockets", "multi_az", "sticky"), compliance=HYPER_COMPLIANCE,
     cost=price((15, 40), (40, 120), (120, 450), (450, 1800), (1800, 7000)),
     strengths=["Simple PaaS on EC2 inside AWS"], limits=["Dated developer experience; slower deploys"], src=["beanstalk"])
host("kubernetes", "Managed Kubernetes (EKS / GKE / AKS)", "hyperscaler", s=(5, 5, 2, 4, 2, 5), learn=1, ops=5,
     traits=("containers", "websockets", "udp", "autoscale", "multi_az", "k8s", "sticky"), compliance=HYPER_COMPLIANCE,
     cost=price((150, 250), (200, 400), (400, 1200), (1200, 4000), (4000, 15000)), users_min=1_000_000,
     strengths=["Maximum control and portability for many services"],
     limits=["Needs dedicated platform engineers", "Control plane, node and add-on costs from day one"],
     src=["eks_pricing", "gke_autopilot", "aks", "cncf"], cloud="hyperscaler")
host("vm_compose", "Docker Compose on cloud VMs", "vm", s=(4, 3, 4, 3, 5, 3), learn=3, ops=4,
     traits=("containers", "websockets", "udp", "vm", "sticky"), compliance=HYPER_COMPLIANCE,
     cost=price((5, 20), (10, 40), (40, 160), (160, 600), (600, 2400)), self_host=True,
     strengths=["Cheapest predictable compute; full control"],
     limits=["You patch, back up and fail over yourself", "Single VM caps availability around 99.5-99.9%"],
     src=["compose"], cloud="any")
host("onprem_compose", "On-premise Linux servers + Docker Compose", "self", s=(4, 3, 3, 3, 4, 4), learn=3, ops=4,
     traits=("containers", "websockets", "udp", "onprem", "vm", "sticky"), compliance=HYPER_COMPLIANCE,
     cost=price((20, 80), (50, 200), (200, 800), (800, 3000), (3000, 10000)), self_host=True,
     strengths=["Runs fully inside your network; no third-party data processors"],
     limits=["Hardware, patching, backups and DR are your responsibility"], src=["compose"], cloud="none")
host("onprem_k8s", "On-premise Kubernetes (RKE2 / k3s)", "self", s=(5, 5, 2, 4, 3, 4), learn=1, ops=5,
     traits=("containers", "websockets", "udp", "onprem", "k8s", "multi_az", "sticky"), compliance=HYPER_COMPLIANCE,
     cost=price((80, 200), (150, 400), (400, 1200), (1200, 4000), (4000, 15000)), self_host=True, users_min=200_000,
     strengths=["Self-healing, rolling deploys across on-prem nodes"],
     limits=["Requires an experienced platform team"], src=["rke2", "k3s"], cloud="none")
host("gamelift", "Amazon GameLift Servers", "aws", s=(5, 5, 3, 4, 3, 5), learn=2, ops=3,
     traits=("udp", "game_servers", "autoscale", "multi_az"), compliance=HYPER_COMPLIANCE,
     cost=price((50, 150), (150, 400), (400, 1500), (1500, 6000), (6000, 20000)),
     strengths=["Managed dedicated game-server fleets with FlexMatch matchmaking"],
     limits=["AWS-specific SDK integration"], src=["gamelift"])
host("heroku", "Heroku", "heroku", s=(3, 3, 5, 3, 3, 4), traits=("containers", "managed_paas"), regions=("eu", "us"),
     compliance=("gdpr", "soc2", "iso27001", "pci_dss", "hipaa"), cost=price((5, 7), (25, 50), (50, 500), (500, 2000), (2000, 8000)),
     status="maintenance", status_note="Salesforce moved Heroku to a sustaining-engineering model in Feb 2026 (no new features).",
     src=["heroku_sustaining"], aliases=[r"heroku"])
host("app_runner", "AWS App Runner", "aws", s=(4, 4, 5, 4, 4, 5), traits=("containers",), compliance=HYPER_COMPLIANCE,
     cost=price((5, 25), (25, 100), (100, 400), (400, 1500), (1500, 6000)), status="closed_to_new",
     status_note="Closed to new customers on 30 Apr 2026; AWS recommends ECS Express Mode.", src=["apprunner_change"],
     aliases=[r"app ?runner"])

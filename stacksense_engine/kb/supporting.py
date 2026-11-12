"""Supporting services. layer = supporting category used by the selector."""
from .common import tech, price, REGIONS_ALL, REGIONS_NO_INDIA, HYPER_COMPLIANCE, REGION_NAMES

FREE5 = price((0, 0), (0, 0), (0, 0), (0, 0), (0, 0))
SELF_SMALL = price((0, 5), (5, 20), (20, 80), (80, 300), (300, 1200))


def sup(id, name, layer, provider, *, s=(3, 3, 4, 4, 4, 4), learn=4, ops=1, mature=4, traits=(), regions=REGIONS_ALL,
        compliance=HYPER_COMPLIANCE, cost=FREE5, src=(), self_host=False, saas=None, lock="low", langs=(),
        requires=(), users_max=None, users_min=0, strengths=(), limits=(), status="active", status_note="",
        pii=True, aliases=(), notes=""):
    t = tech(id, name, layer, kind=layer, provider=provider, s=s, learn=learn, ops=ops, mature=mature,
             traits=tuple(traits) + tuple(f"requires:{r}" for r in requires), regions=regions,
             compliance=compliance, cost=cost, src=src, self_host=self_host,
             saas=(not self_host) if saas is None else saas, lock=lock, langs=langs, users_max=users_max,
             users_min=users_min, strengths=strengths, limits=limits, status=status, status_note=status_note,
             pii=pii, aliases=aliases, region_names=REGION_NAMES.get(provider, {}), notes=notes)
    return t


# ------------------------------------------------------------------ cache
sup("elasticache", "Amazon ElastiCache for Valkey", "cache", "aws", s=(5, 5, 4, 4, 4, 5),
    cost=price((12, 25), (15, 50), (50, 200), (200, 800), (800, 3000)), traits=("pubsub", "managed"),
    strengths=["Managed Valkey/Redis-compatible cache with Multi-AZ failover"], limits=["AWS-only; VPC access"],
    src=["elasticache_pricing", "valkey"])
sup("memorystore", "Memorystore for Valkey/Redis", "cache", "gcp", s=(5, 5, 4, 4, 3, 5),
    cost=price((35, 50), (35, 80), (80, 250), (250, 900), (900, 3500)), traits=("pubsub", "managed"),
    strengths=["Managed Redis-compatible cache on GCP"], limits=["Minimum instance cost is relatively high"],
    src=["memorystore"])
sup("azure_redis", "Azure Managed Redis", "cache", "azure", s=(5, 5, 4, 4, 3, 5),
    cost=price((15, 60), (30, 100), (100, 350), (350, 1200), (1200, 4000)), traits=("pubsub", "managed"),
    strengths=["Microsoft's successor to Azure Cache for Redis"], limits=["Azure-only"],
    src=["azure_managed_redis", "azure_cache_retire"])
sup("azure_cache_legacy", "Azure Cache for Redis", "cache", "azure", status="closed_to_new",
    status_note="Creation blocked for new customers since 1 Apr 2026; retires 30 Sep 2028. Use Azure Managed Redis.",
    src=["azure_cache_retire"], aliases=[r"azure cache for redis"])
sup("do_valkey", "DigitalOcean Managed Valkey", "cache", "digitalocean", s=(4, 4, 5, 4, 4, 4),
    compliance=("gdpr", "dpdp", "soc2"), cost=price((15, 15), (15, 30), (30, 120), (120, 500), (500, 2000)),
    traits=("pubsub", "managed"), strengths=["Managed Valkey next to App Platform"], src=["do_db"])
sup("upstash", "Upstash Redis (serverless)", "cache", "upstash", s=(4, 4, 5, 4, 5, 4), regions=REGIONS_NO_INDIA,
    compliance=("gdpr", "soc2"), cost=price((0, 0), (0, 10), (10, 60), (60, 300), (300, 1500)),
    traits=("pubsub", "serverless"), strengths=["Per-request pricing with a free tier; HTTP API works from edge functions"],
    limits=["Per-command pricing grows with chatty workloads"], src=["upstash"])
sup("valkey_self", "Valkey (self-hosted)", "cache", "self", s=(5, 4, 4, 4, 5, 4), ops=3, self_host=True,
    cost=SELF_SMALL, traits=("pubsub",), strengths=["BSD-licensed Redis fork; runs anywhere"],
    limits=["You operate persistence and failover"], src=["valkey"])

# ------------------------------------------------------------------ queue / background jobs
sup("sqs", "Amazon SQS (+ EventBridge Scheduler)", "queue", "aws", s=(5, 5, 4, 4, 5, 5),
    cost=price((0, 1), (0, 5), (5, 30), (30, 150), (150, 800)), traits=("managed", "dlq"),
    strengths=["Fully managed queue with dead-letter queues; 1M requests/month free"], src=["sqs"])
sup("cloud_tasks", "Google Cloud Tasks / Pub/Sub", "queue", "gcp", s=(5, 5, 4, 4, 5, 5),
    cost=price((0, 1), (0, 5), (5, 30), (30, 150), (150, 800)), traits=("managed", "dlq"),
    strengths=["Push tasks straight to Cloud Run endpoints with retries"], src=["cloudtasks", "pubsub"])
sup("service_bus", "Azure Service Bus", "queue", "azure", s=(5, 5, 4, 4, 4, 5),
    cost=price((0, 10), (10, 15), (10, 50), (50, 700), (700, 2800)), traits=("managed", "dlq"),
    strengths=["Enterprise messaging with sessions and dead-lettering"], src=["servicebus"])
sup("pg_queue", "Postgres-backed job queue", "queue", "self", s=(4, 3, 5, 4, 5, 4), ops=1, self_host=True,
    cost=FREE5, traits=("requires_postgres",), users_max=2_000_000,
    strengths=["No extra infrastructure: jobs are rows in the primary database, transactional with business data"],
    limits=["Throughput bounded by the primary database"], src=["pgboss", "jobrunr", "hangfire"])
sup("redis_jobs", "Redis-backed job queue", "queue", "self", s=(4, 4, 5, 4, 4, 4), ops=1, self_host=True, cost=FREE5,
    traits=("requires_cache",), strengths=["Mature libraries (BullMQ, Celery, Sidekiq) on the existing cache"],
    limits=["Job durability depends on Redis persistence settings"], src=["bullmq", "celery"])
sup("rabbitmq", "RabbitMQ (self-hosted)", "queue", "self", s=(4, 4, 3, 4, 4, 4), ops=3, self_host=True,
    cost=SELF_SMALL, traits=("dlq",), strengths=["Battle-tested broker; works fully offline/on-prem"],
    limits=["Cluster operations and upgrades are on you"], src=["rabbitmq"])
sup("kafka", "Apache Kafka (Amazon MSK / Confluent)", "queue", "any", s=(5, 5, 2, 4, 2, 5), ops=4, learn=2,
    cost=price((150, 300), (200, 500), (300, 1200), (1200, 4000), (4000, 15000)), users_min=2_000_000,
    strengths=["Durable event log for very high-throughput streaming"],
    limits=["Over-engineering below millions of events per day"], src=["kafka"])

# ------------------------------------------------------------------ search
sup("pg_fts", "PostgreSQL full-text search (tsvector + pg_trgm)", "search", "self", s=(4, 3, 5, 5, 5, 5), self_host=True,
    cost=FREE5, traits=("requires_postgres",), users_max=1_000_000,
    strengths=["No extra service; search stays transactionally consistent with the data",
               "pg_trgm adds typo-tolerant matching"],
    limits=["Relevance tuning and faceting are basic compared with dedicated engines"], src=["pg_fts"])
sup("atlas_search", "MongoDB Atlas Search", "search", "mongodb", s=(4, 4, 5, 4, 4, 4), cost=FREE5,
    traits=("requires_mongodb",), strengths=["Lucene-based search inside Atlas"], src=["mongodb"])
sup("pagefind", "Pagefind (static search index)", "search", "self", s=(5, 3, 5, 4, 5, 5), self_host=True, cost=FREE5,
    traits=("static_only",), pii=False, strengths=["Builds a search index at build time; no server"],
    limits=["Only for static content"], src=["pagefind"])
sup("meilisearch_self", "Meilisearch (self-hosted)", "search", "self", s=(5, 3, 5, 4, 5, 4), ops=2, self_host=True,
    cost=SELF_SMALL, strengths=["Typo-tolerant instant search; single binary"],
    limits=["Single-node in the open-source edition"], src=["meilisearch"])
sup("opensearch_aws", "Amazon OpenSearch Service", "search", "aws", s=(4, 5, 3, 4, 3, 5), ops=2,
    cost=price((25, 50), (40, 150), (150, 500), (500, 2000), (2000, 8000)),
    strengths=["Managed OpenSearch with k-NN vectors"], limits=["Cluster sizing and cost overhead"], src=["aws_opensearch", "opensearch"])
sup("opensearch_self", "OpenSearch (self-hosted)", "search", "self", s=(4, 5, 3, 4, 4, 4), ops=4, self_host=True,
    cost=price((20, 60), (40, 120), (120, 400), (400, 1500), (1500, 6000)), strengths=["Apache-2.0 search; runs air-gapped"],
    src=["opensearch"])
sup("elastic_cloud", "Elastic Cloud (Elasticsearch)", "search", "elastic", s=(5, 5, 4, 4, 3, 5),
    cost=price((95, 120), (100, 200), (200, 800), (800, 3000), (3000, 12000)),
    strengths=["Best-in-class relevance tuning and analytics"], limits=["Highest entry price"], src=["elastic"])
sup("algolia", "Algolia", "search", "algolia", s=(5, 5, 5, 4, 3, 4), regions=REGIONS_NO_INDIA,
    compliance=("gdpr", "soc2", "iso27001"), cost=price((0, 0), (0, 50), (50, 500), (500, 2500), (2500, 10000)),
    lock="high", strengths=["Hosted instant search with great UX components"], limits=["Per-request pricing at scale"],
    src=["algolia"])
sup("azure_search", "Azure AI Search", "search", "azure", s=(4, 5, 4, 4, 3, 5),
    cost=price((75, 75), (75, 250), (250, 1000), (1000, 4000), (4000, 15000)),
    strengths=["Managed search with Entra ID integration"], src=["azure_search"])

# ------------------------------------------------------------------ auth (identity provider)
sup("supabase_auth", "Supabase Auth", "auth", "supabase", s=(4, 4, 5, 4, 5, 4), compliance=("gdpr", "dpdp", "soc2", "hipaa"),
    traits=("requires_supabase", "phone_otp", "social", "email", "mfa"), cost=FREE5,
    strengths=["Users live in your project's Postgres (same region)", "Phone OTP, social and email logins built in"],
    src=["supabase"])
sup("firebase_auth", "Firebase Authentication", "auth", "gcp", s=(4, 5, 5, 4, 5, 4), regions=(),
    compliance=("gdpr", "soc2", "iso27001"), traits=("requires_firebase", "phone_otp", "social", "email", "global_service"),
    cost=FREE5, lock="high", strengths=["Drop-in phone/social auth for mobile"],
    limits=["No choice of data location for identity data"], src=["firebase_locations"])
sup("cognito", "Amazon Cognito", "auth", "aws", s=(4, 5, 3, 3, 4, 5), learn=3,
    traits=("phone_otp", "social", "email", "saml", "mfa"), cost=FREE5,
    strengths=["User pools stay in the chosen AWS region", "SAML/OIDC federation"],
    limits=["Clunky customisation; per-MAU pricing above 10k MAU"], src=["cognito"])
sup("auth0", "Auth0 (Okta)", "auth", "auth0", s=(4, 5, 5, 4, 2, 5), regions=REGIONS_NO_INDIA,
    compliance=("gdpr", "soc2", "iso27001", "hipaa", "pci_dss"), traits=("phone_otp", "social", "email", "saml", "orgs", "mfa"),
    cost=FREE5, lock="medium", strengths=["Mature universal login, Organizations for B2B"],
    limits=["Gets expensive quickly as MAU grows", "No India public-cloud region"], src=["auth0"])
sup("clerk", "Clerk", "auth", "clerk", s=(4, 4, 5, 4, 3, 4), regions=("us",), compliance=("gdpr", "soc2", "hipaa"),
    traits=("social", "email", "phone_otp", "orgs", "mfa"), cost=FREE5, lock="medium",
    strengths=["Prebuilt React components and Organizations for B2B SaaS"], limits=["US-hosted identity data"],
    src=["clerk"])
sup("workos", "WorkOS (AuthKit + SSO)", "auth", "workos", s=(4, 4, 5, 4, 3, 5), regions=("us",),
    compliance=("gdpr", "soc2", "hipaa"), traits=("saml", "orgs", "social", "email", "scim"), cost=FREE5,
    strengths=["Enterprise SSO/SCIM per customer organisation for B2B SaaS"], limits=["SSO connections billed per connection"],
    src=["workos"])
sup("keycloak", "Keycloak (self-hosted)", "auth", "self", s=(4, 4, 3, 4, 4, 5), ops=3, learn=2, self_host=True,
    traits=("saml", "social", "email", "orgs", "mfa", "ldap"),
    cost=price((10, 40), (20, 80), (40, 150), (100, 400), (300, 1200)),
    strengths=["Open-source IdP with SAML/OIDC, LDAP federation; runs on-prem/air-gapped"],
    limits=["Upgrades and HA are your job"], src=["keycloak"])
sup("entra_id", "Microsoft Entra ID", "auth", "azure", s=(4, 5, 5, 5, 5, 5), traits=("saml", "enterprise", "existing_ms", "global_service"),
    cost=FREE5, strengths=["Corporate SSO, MFA and conditional access employees already use"],
    limits=["For workforce identity; customer identity needs External ID"], src=["entra", "ms_identity_web"],
    aliases=[r"entra", r"azure ad", r"azure active directory", r"\baad\b"])
sup("framework_auth", "Framework-native authentication", "auth", "self", s=(4, 4, 4, 4, 5, 4), self_host=True,
    traits=("email", "social", "phone_otp_with_sms"), cost=FREE5,
    strengths=["Identity data stays in your own database and region; no per-MAU fees"],
    limits=["You own password storage, rate limiting and MFA flows"], src=["better_auth", "aspnet", "spring", "django"])
sup("lucia", "Lucia auth library", "auth", "self", status="deprecated", status_note="Deprecated in 2025; now a learning resource.",
    src=["lucia"], aliases=[r"lucia"])
# SMS OTP gateways (sub-layer 'sms')
sup("msg91", "MSG91 OTP (DLT-registered)", "sms", "msg91", s=(4, 4, 5, 4, 5, 4), regions=("india",), compliance=("dpdp", "iso27001"),
    strengths=["Indian SMS gateway with DLT templates; low per-OTP cost"], limits=["India-focused"], src=["msg91", "trai_dlt"])
sup("twilio_verify", "Twilio Verify", "sms", "twilio", s=(4, 5, 5, 4, 2, 5), regions=("us", "eu", "other"),
    compliance=("gdpr", "soc2", "iso27001", "hipaa"), strengths=["Global OTP delivery with fraud guard"],
    limits=["Highest per-verification price"], src=["twilio_verify"])
sup("sns_sms", "Amazon SNS / End User Messaging SMS", "sms", "aws", s=(4, 5, 3, 4, 4, 5),
    strengths=["SMS from the same AWS account and region"], limits=["India SMS needs DLT sender registration"],
    src=["trai_dlt"])
sup("azure_comm_sms", "Azure Communication Services SMS", "sms", "azure", s=(4, 5, 4, 4, 3, 5),
    strengths=["SMS inside Azure"], limits=["Limited country coverage for sender types"], src=["azure_compliance"])
sup("self_sms_modem", "On-prem SMS gateway (GSM modem / operator SMPP)", "sms", "self", self_host=True, ops=3,
    s=(3, 2, 2, 3, 3, 3), strengths=["Works without internet SaaS"], limits=["Operator contract needed"], src=["trai_dlt"])

# ------------------------------------------------------------------ object storage
sup("s3", "Amazon S3", "storage", "aws", s=(5, 5, 4, 5, 4, 5), cost=FREE5, traits=("presigned", "lifecycle", "sse_kms"),
    strengths=["Presigned uploads, lifecycle tiers, SSE-KMS encryption"], src=["s3_pricing"])
sup("gcs", "Google Cloud Storage", "storage", "gcp", s=(5, 5, 4, 5, 4, 5), cost=FREE5, traits=("presigned", "resumable"),
    strengths=["Signed URLs and resumable uploads"], src=["gcs_pricing"])
sup("azure_blob", "Azure Blob Storage", "storage", "azure", s=(5, 5, 4, 5, 4, 5), cost=FREE5, traits=("presigned",),
    strengths=["SAS-token uploads, lifecycle tiers"], src=["blob_pricing"])
sup("supabase_storage", "Supabase Storage", "storage", "supabase", s=(4, 4, 5, 4, 5, 4),
    compliance=("gdpr", "dpdp", "soc2", "hipaa"), traits=("requires_supabase", "resumable"), cost=FREE5,
    strengths=["RLS-protected buckets and resumable (TUS) uploads; 100 GB included on Pro"], src=["supabase_resumable"])
sup("r2", "Cloudflare R2", "storage", "cloudflare", s=(5, 5, 4, 4, 5, 4), regions=("eu",),
    compliance=("gdpr", "soc2", "iso27001", "pci_dss"), cost=FREE5, traits=("zero_egress",),
    strengths=["S3-compatible with zero egress fees"], limits=["Data-location jurisdictions only for EU (and FedRAMP)"],
    src=["r2", "r2_location"])
sup("do_spaces", "DigitalOcean Spaces", "storage", "digitalocean", s=(4, 4, 5, 4, 5, 4),
    compliance=("gdpr", "dpdp", "soc2"), cost=FREE5, traits=("presigned", "cdn_builtin"),
    strengths=["S3-compatible storage with built-in CDN; flat $5 for 250 GB"], src=["do_spaces"])
sup("seaweedfs", "SeaweedFS (self-hosted S3-compatible)", "storage", "self", s=(4, 4, 3, 4, 5, 4), ops=3,
    self_host=True, cost=SELF_SMALL, strengths=["Apache-2.0 S3-compatible object store; runs on-prem"],
    limits=["You operate replication and backups"], src=["seaweedfs"])
sup("ceph_rgw", "Ceph RGW (self-hosted S3-compatible)", "storage", "self", s=(4, 5, 2, 4, 4, 5), ops=5, learn=1,
    self_host=True, cost=price((50, 150), (100, 300), (300, 1000), (1000, 4000), (4000, 15000)), users_min=100_000,
    strengths=["Enterprise-scale distributed storage"], limits=["Needs a storage team"], src=["ceph"])
sup("minio", "MinIO Community Edition", "storage", "self", status="eol",
    status_note="Repository placed in maintenance mode (Dec 2025) and archived (Feb 2026); no community binaries.",
    src=["minio_repo"], aliases=[r"minio"])

# ------------------------------------------------------------------ CDN
sup("cloudfront", "Amazon CloudFront", "cdn", "aws", s=(5, 5, 4, 4, 5, 5), pii=False,
    cost=price((0, 0), (0, 5), (5, 50), (50, 400), (400, 3000)), strengths=["1 TB/month always-free egress tier"],
    src=["cloudfront_pricing"])
sup("cloud_cdn", "Google Cloud CDN", "cdn", "gcp", s=(5, 5, 4, 4, 4, 5), pii=False,
    cost=price((0, 5), (5, 20), (20, 100), (100, 600), (600, 4000)), strengths=["Integrated with the external HTTPS load balancer"],
    src=["cloudcdn"])
sup("front_door", "Azure Front Door", "cdn", "azure", s=(5, 5, 4, 4, 3, 5), pii=False,
    cost=price((35, 40), (35, 60), (60, 200), (200, 800), (800, 4000)), strengths=["Global CDN + WAF for Azure apps"],
    src=["frontdoor"])
sup("cloudflare_cdn", "Cloudflare CDN (free/pro plan)", "cdn", "cloudflare", s=(5, 5, 5, 4, 5, 5), pii=False,
    compliance=("gdpr", "soc2", "iso27001", "pci_dss"), cost=price((0, 0), (0, 0), (0, 25), (25, 250), (250, 2000)),
    strengths=["Free unmetered CDN and DDoS protection in front of any origin"], src=["cloudflare_plans"])
sup("host_cdn", "Built-in CDN of the hosting platform", "cdn", "host", s=(5, 5, 5, 4, 5, 4), pii=False, cost=FREE5,
    strengths=["No extra configuration"], src=["vercel", "netlify", "cf_static", "gh_pages"])

# ------------------------------------------------------------------ realtime
sup("ws_native", "WebSockets in the backend service", "realtime", "self", s=(4, 4, 4, 4, 5, 4), self_host=True, cost=FREE5,
    traits=("needs_long_lived",), strengths=["No extra vendor; messages stay in-region"],
    limits=["Multi-instance fan-out needs a pub/sub backplane (Redis/Valkey)"],
    src=["socketio", "signalr", "phoenix", "go"])
sup("supabase_realtime", "Supabase Realtime", "realtime", "supabase", s=(4, 4, 5, 4, 5, 4),
    compliance=("gdpr", "dpdp", "soc2", "hipaa"), traits=("requires_supabase",), cost=FREE5,
    strengths=["Broadcast, presence and Postgres change streams without servers"], src=["supabase"])
sup("firestore_rt", "Firestore realtime listeners", "realtime", "gcp", s=(4, 5, 5, 4, 4, 4),
    compliance=("gdpr", "soc2", "iso27001", "dpdp"), traits=("requires_firebase",), cost=FREE5, lock="high",
    strengths=["Clients subscribe to documents directly"], src=["firestore"])
sup("azure_signalr", "Azure SignalR Service", "realtime", "azure", s=(5, 5, 5, 4, 3, 5),
    cost=price((0, 0), (49, 49), (49, 250), (250, 1000), (1000, 4000)), traits=("requires_aspnet",),
    strengths=["Offloads SignalR connections from App Service"], src=["azure_signalr"])
sup("apigw_ws", "API Gateway WebSocket APIs", "realtime", "aws", s=(4, 5, 3, 3, 4, 5),
    cost=price((0, 2), (2, 20), (20, 150), (150, 1000), (1000, 5000)),
    strengths=["Serverless WebSockets for Lambda backends"], limits=["Connection state handled in DynamoDB"],
    src=["apigw_ws"])
sup("ably", "Ably", "realtime", "ably", s=(5, 5, 5, 4, 3, 5), regions=REGIONS_NO_INDIA,
    compliance=("gdpr", "soc2", "hipaa"), cost=price((0, 0), (29, 100), (100, 500), (500, 2500), (2500, 10000)),
    strengths=["Managed pub/sub with guaranteed ordering and presence"], limits=["Per-message pricing"], src=["ably"])
sup("pusher", "Pusher Channels", "realtime", "pusher", s=(4, 4, 5, 4, 3, 4), compliance=("gdpr", "soc2"),
    cost=price((0, 0), (49, 99), (99, 499), (499, 1999), (1999, 8000)),
    strengths=["Simple hosted channels; clusters incl. ap2 (Mumbai)"], limits=["Connection-count pricing"], src=["pusher"])
sup("yjs", "Yjs CRDT + y-websocket/Hocuspocus provider", "realtime_crdt", "self", s=(5, 5, 4, 4, 5, 4), self_host=True,
    cost=FREE5, langs=("javascript", "typescript"),
    strengths=["Conflict-free merging of concurrent edits; offline edits reconcile automatically",
               "Awareness protocol for live cursors and presence"],
    limits=["Document snapshots must be compacted and persisted periodically"], src=["yjs", "hocuspocus", "figma_multiplayer"])

# ------------------------------------------------------------------ payments
sup("stripe", "Stripe (Payments + Billing)", "payments", "stripe", s=(4, 5, 5, 5, 4, 5), regions=REGIONS_NO_INDIA,
    compliance=("gdpr", "pci_dss", "soc2", "iso27001"), cost=FREE5, traits=("subscriptions", "global", "per_seat"),
    strengths=["Best-in-class APIs; Billing handles per-seat subscriptions and proration",
               "Hosted Checkout/Elements keep card data out of PCI scope (SAQ A)"],
    limits=["Stripe India onboarding is invite-only: not for India-resident payment data"],
    src=["stripe", "stripe_billing", "stripe_india"])
sup("razorpay", "Razorpay", "payments", "razorpay", s=(4, 4, 5, 4, 4, 5), regions=("india",),
    compliance=("dpdp", "pci_dss", "rbi_localisation", "iso27001", "soc2"), cost=FREE5,
    traits=("upi", "subscriptions", "india", "payouts"), mature=5,
    strengths=["UPI, cards, netbanking, e-mandates (EMI/AutoPay) and payouts (RazorpayX)",
               "PCI DSS Level 1; payment data stored in India"],
    limits=["India-centric"], src=["razorpay", "razorpay_security", "rbi_localisation"])
sup("cashfree", "Cashfree Payments", "payments", "cashfree", s=(4, 4, 5, 4, 4, 5), regions=("india",),
    compliance=("dpdp", "pci_dss", "rbi_localisation"), cost=FREE5, traits=("upi", "india", "payouts"),
    strengths=["UPI/cards plus bulk payouts for disbursals"], src=["cashfree", "rbi_localisation"])
sup("payu", "PayU India", "payments", "payu", s=(4, 4, 4, 4, 4, 5), regions=("india",),
    compliance=("dpdp", "pci_dss", "rbi_localisation"), cost=FREE5, traits=("upi", "india"),
    strengths=["Established Indian gateway with EMI options"], src=["payu"])
sup("paddle", "Paddle (merchant of record)", "payments", "paddle", s=(4, 4, 5, 4, 3, 5), regions=REGIONS_NO_INDIA,
    compliance=("gdpr", "pci_dss", "soc2"), cost=FREE5, traits=("subscriptions", "mor", "per_seat"),
    strengths=["Handles global sales tax/VAT as merchant of record for SaaS"], limits=["Higher fee than a pure gateway"],
    src=["paddle"])

# ------------------------------------------------------------------ ML
sup("sagemaker", "Amazon SageMaker AI real-time endpoint", "ml", "aws", s=(4, 5, 3, 4, 3, 5), ops=2,
    cost=price((85, 170), (85, 250), (170, 500), (500, 2000), (2000, 8000)), traits=("inference", "training", "model_registry"),
    strengths=["Managed model hosting with autoscaling and model registry"], limits=["Always-on endpoint cost"],
    src=["sagemaker"])
sup("vertex", "Vertex AI endpoints", "ml", "gcp", s=(4, 5, 3, 4, 3, 5), ops=2,
    cost=price((70, 150), (70, 250), (150, 500), (500, 2000), (2000, 8000)), traits=("inference", "training", "llm"),
    strengths=["Managed model serving, training and Gemini models"], src=["vertex"])
sup("azure_ml", "Azure Machine Learning online endpoints", "ml", "azure", s=(4, 5, 3, 4, 3, 5), ops=2,
    cost=price((70, 150), (70, 250), (150, 500), (500, 2000), (2000, 8000)), traits=("inference", "training"),
    strengths=["Managed endpoints with Entra-integrated access"], src=["azureml"])
sup("model_container", "Containerised model service (FastAPI + ONNX Runtime/scikit-learn)", "ml", "self",
    s=(4, 4, 4, 4, 5, 4), ops=2, self_host=True, langs=("python",),
    cost=price((5, 30), (20, 80), (60, 250), (250, 1000), (1000, 4000)), traits=("inference",),
    strengths=["Deploys beside the app on the same platform; versioned model artefacts"],
    limits=["You own model monitoring and rollout"], src=["fastapi", "onnx", "mlflow"])
sup("bedrock", "Amazon Bedrock (region-pinned LLM)", "ml", "aws", s=(4, 5, 5, 4, 3, 5),
    cost=price((10, 50), (50, 300), (300, 1500), (1500, 6000), (6000, 20000)), traits=("llm",),
    strengths=["Foundation models inside your AWS account and region; no training on your data"], src=["bedrock"])
sup("azure_openai", "Azure AI Foundry (OpenAI models)", "ml", "azure", s=(4, 5, 5, 4, 3, 5),
    cost=price((10, 50), (50, 300), (300, 1500), (1500, 6000), (6000, 20000)), traits=("llm",),
    strengths=["OpenAI models under Azure data-processing terms"], src=["azure_openai"])
sup("vertex_llm", "Vertex AI (Gemini)", "ml", "gcp", s=(4, 5, 5, 4, 4, 5),
    cost=price((10, 50), (50, 300), (300, 1500), (1500, 6000), (6000, 20000)), traits=("llm",),
    strengths=["Gemini models with regional endpoints"], src=["vertex"])
sup("hosted_llm_api", "Hosted LLM API (Anthropic / OpenAI)", "ml", "llm_vendor", s=(5, 5, 5, 4, 3, 4), regions=("us", "eu"),
    compliance=("gdpr", "soc2", "iso27001", "hipaa"), cost=price((10, 50), (50, 300), (300, 1500), (1500, 6000), (6000, 20000)),
    traits=("llm",), strengths=["Frontier model quality with the simplest integration"],
    limits=["Data processed outside India; check retention terms"], src=["bedrock"])
sup("self_llm", "Self-hosted open-weights LLM (vLLM on GPU)", "ml", "self", s=(4, 3, 2, 3, 2, 5), ops=5, self_host=True,
    learn=1, cost=price((300, 800), (500, 1500), (1500, 5000), (5000, 15000), (15000, 50000)), traits=("llm",),
    strengths=["Runs fully on-prem/air-gapped"], limits=["GPU cost and MLOps skills"], src=["vllm", "ollama"])
sup("pgvector", "pgvector (vector search in PostgreSQL)", "vector", "self", s=(4, 3, 5, 5, 5, 5), self_host=True,
    cost=FREE5, traits=("requires_postgres",), strengths=["Embeddings live next to the data with the same access control"],
    src=["pgvector"])
sup("qdrant", "Qdrant", "vector", "self", s=(5, 5, 4, 4, 4, 4), ops=2, self_host=True, cost=SELF_SMALL,
    strengths=["Purpose-built vector DB with filtering"], src=["qdrant"])
sup("training_managed", "Managed training jobs (SageMaker / Vertex / Azure ML) + MLflow tracking", "ml_training", "cloud",
    s=(4, 5, 3, 4, 3, 5), ops=2, cost=price((50, 200), (100, 500), (300, 1500), (1500, 6000), (6000, 25000)),
    strengths=["Spot GPUs, experiment tracking and model registry"], src=["sagemaker", "vertex", "mlflow"])
sup("training_self", "GPU servers + MLflow (self-hosted)", "ml_training", "self", s=(4, 3, 2, 3, 3, 5), ops=5,
    self_host=True, cost=price((200, 600), (400, 1200), (1200, 4000), (4000, 12000), (12000, 40000)),
    strengths=["Training without data leaving the premises"], src=["mlflow"])

# ------------------------------------------------------------------ CI/CD
sup("github_actions", "GitHub Actions", "ci_cd", "github", s=(4, 5, 5, 5, 5, 4), pii=False, regions=(),
    compliance=("gdpr", "soc2", "iso27001"), cost=price((0, 0), (0, 10), (0, 40), (40, 200), (200, 800)),
    strengths=["Free minutes for small teams; huge marketplace of actions"], src=["gh_actions"])
sup("azure_pipelines", "Azure Pipelines", "ci_cd", "azure", s=(4, 5, 4, 4, 4, 5), pii=False,
    cost=price((0, 0), (0, 15), (15, 60), (60, 300), (300, 1200)), strengths=["Integrated with Entra ID and Azure resources"],
    src=["azure_devops"])
sup("gitlab_self", "GitLab CI (self-managed)", "ci_cd", "self", s=(4, 5, 4, 4, 4, 5), ops=3, self_host=True, pii=False,
    cost=price((10, 40), (20, 60), (40, 150), (150, 500), (500, 2000)), strengths=["Runs entirely inside an on-prem/air-gapped network"],
    src=["gitlab"])
sup("host_git_deploy", "Git-push deploys of the hosting platform", "ci_cd", "host", s=(4, 4, 5, 4, 5, 4), pii=False,
    cost=FREE5, strengths=["Preview deploy per pull request with no pipeline code"], src=["vercel", "netlify", "cf_static"])
sup("eas", "Expo EAS Build/Submit/Update", "mobile_ci", "expo", s=(4, 4, 5, 4, 4, 4), pii=False, regions=(),
    cost=price((0, 0), (0, 19), (19, 99), (99, 300), (300, 1000)), strengths=["Cloud builds and store submission for React Native"],
    src=["eas"])
sup("codemagic", "Codemagic", "mobile_ci", "codemagic", s=(4, 4, 5, 4, 4, 4), pii=False, regions=(),
    cost=price((0, 0), (0, 50), (50, 150), (150, 500), (500, 1500)), strengths=["Flutter-first mobile CI/CD"], src=["codemagic"])
sup("fastlane_gha", "fastlane on GitHub Actions", "mobile_ci", "github", s=(4, 4, 4, 4, 5, 4), pii=False, regions=(),
    cost=price((0, 0), (0, 20), (20, 80), (80, 300), (300, 1000)), strengths=["Native Android/iOS build and release automation"],
    src=["fastlane", "gh_actions"])
sup("app_center", "Visual Studio App Center", "mobile_ci", "azure", status="eol",
    status_note="Retired 31 Mar 2025.", src=["appcenter_retire"], aliases=[r"app ?center"])

# ------------------------------------------------------------------ observability
sup("cloudwatch", "Amazon CloudWatch + X-Ray (OpenTelemetry)", "observability", "aws", s=(4, 5, 4, 4, 4, 5),
    cost=price((0, 10), (10, 40), (40, 200), (200, 800), (800, 3000)), strengths=["Logs/metrics/traces stay in-region"],
    src=["cloudwatch", "otel"])
sup("app_insights", "Azure Monitor Application Insights", "observability", "azure", s=(4, 5, 5, 4, 4, 5),
    cost=price((0, 5), (0, 30), (30, 150), (150, 600), (600, 2500)), strengths=["Auto-instrumentation for .NET; in-region workspace"],
    src=["appinsights"])
sup("gcp_ops", "Google Cloud Logging + Monitoring", "observability", "gcp", s=(4, 5, 5, 4, 4, 5),
    cost=price((0, 5), (0, 30), (30, 150), (150, 600), (600, 2500)), strengths=["Built in for Cloud Run; regional log buckets"],
    src=["gcp_ops"])
sup("sentry", "Sentry (errors + performance)", "observability", "sentry", s=(4, 4, 5, 4, 4, 4), regions=("us", "eu"),
    compliance=("gdpr", "soc2", "iso27001", "hipaa"), cost=price((0, 0), (0, 26), (26, 80), (80, 400), (400, 1500)),
    strengths=["Error tracking for web, mobile and backend in one place"], limits=["SaaS data in US/EU (self-host for residency)"],
    src=["sentry"])
sup("lgtm_self", "Prometheus + Grafana + Loki (self-hosted)", "observability", "self", s=(4, 5, 3, 4, 4, 5), ops=3,
    self_host=True, cost=price((5, 20), (10, 40), (40, 150), (150, 500), (500, 2000)),
    strengths=["Open-source stack that runs inside restricted networks"], src=["prometheus", "grafana"])
sup("host_logs", "Hosting platform logs/analytics", "observability", "host", s=(3, 3, 5, 3, 5, 3), cost=FREE5, pii=False,
    strengths=["Zero setup for static sites"], src=["vercel", "netlify", "cf_static"])

# ------------------------------------------------------------------ other building blocks
sup("fcm", "Firebase Cloud Messaging (push)", "push", "gcp", s=(4, 5, 5, 4, 5, 4), regions=(), pii=False,
    compliance=("gdpr", "soc2", "iso27001"), cost=FREE5,
    strengths=["Free push for Android/iOS/web"], limits=["Keep payloads free of personal data (delivery is global)"],
    src=["fcm"])
sup("ses", "Amazon SES", "email", "aws", s=(4, 5, 4, 4, 5, 5), cost=price((0, 1), (1, 5), (5, 30), (30, 150), (150, 600)),
    strengths=["Cheapest transactional email at volume"], src=["ses"])
sup("resend", "Resend", "email", "resend", s=(4, 4, 5, 4, 4, 4), regions=("us", "eu"), compliance=("gdpr", "soc2"),
    cost=price((0, 0), (0, 20), (20, 90), (90, 400), (400, 1500)), strengths=["Developer-friendly email API"], src=["resend"])
sup("graph_mail", "Microsoft Graph (Outlook/Teams notifications)", "email", "azure", s=(4, 5, 5, 4, 5, 5), cost=FREE5,
    traits=("existing_ms", "global_service", "requires_ms365"), strengths=["Uses the company's existing Microsoft 365 for approvals and alerts"],
    src=["graph"], aliases=[r"microsoft 365", r"office 365", r"\bm365\b", r"\bo365\b", r"exchange online", r"teams"])
sup("smtp_self", "On-prem SMTP relay", "email", "self", self_host=True, s=(3, 3, 4, 3, 5, 3), cost=FREE5,
    strengths=["No external email service"], src=["compose"])
sup("watermelondb", "WatermelonDB (SQLite) + custom sync endpoint", "offline_sync", "self", self_host=True,
    s=(4, 4, 4, 4, 5, 4), langs=("javascript", "typescript"), cost=FREE5,
    strengths=["Lazy-loaded SQLite store built for React Native with pull/push sync protocol"],
    limits=["Conflict rules and sync endpoint are yours to write"], src=["watermelondb", "expo_sqlite"])
sup("room_workmanager", "Room + WorkManager sync queue", "offline_sync", "self", self_host=True, s=(5, 4, 3, 5, 5, 4),
    langs=("kotlin", "java"), cost=FREE5, strengths=["Android-native offline store with guaranteed background upload"],
    src=["workmanager"])
sup("drift_sync", "Drift (SQLite) + background sync", "offline_sync", "self", self_host=True, s=(4, 4, 4, 4, 5, 4),
    langs=("dart",), cost=FREE5, strengths=["Type-safe SQLite for Flutter"], src=["flutter"])
sup("firestore_offline_sync", "Firestore offline persistence", "offline_sync", "gcp", s=(4, 5, 5, 4, 4, 4),
    traits=("requires_firebase",), cost=FREE5, lock="high", strengths=["Offline writes queue and sync automatically"],
    src=["firestore_offline"])
sup("powersync", "PowerSync (Postgres <-> SQLite sync)", "offline_sync", "powersync", s=(4, 4, 5, 4, 3, 4),
    regions=("us", "eu", "other"), compliance=("gdpr", "soc2", "hipaa"),
    cost=price((0, 0), (0, 49), (49, 300), (300, 1200), (1200, 5000)),
    strengths=["Managed sync engine between Postgres and on-device SQLite"], limits=["Cloud regions exclude India (self-host Open Edition)"],
    src=["powersync"])
sup("atlas_device_sync", "MongoDB Atlas Device Sync (Realm)", "offline_sync", "mongodb", status="eol",
    status_note="Deprecated Sept 2024; end of life 30 Sep 2025.", src=["atlas_app_services"], aliases=[r"realm", r"device sync"])
sup("postgis", "PostGIS extension", "geospatial", "self", self_host=True, s=(5, 4, 4, 5, 5, 4), cost=FREE5,
    traits=("requires_postgres",), strengths=["Spatial indexes and queries (nearby, within polygon)"], src=["postgis"])
sup("waf_kms_aws", "AWS WAF + KMS + Secrets Manager + CloudTrail/GuardDuty", "security", "aws", s=(4, 5, 4, 4, 3, 5),
    cost=price((15, 40), (30, 80), (80, 300), (300, 1000), (1000, 4000)),
    strengths=["Edge filtering, envelope encryption and audit trails expected by PCI DSS / RBI / ISO 27001 auditors"],
    src=["waf", "kms"])
sup("azure_sec", "Azure Key Vault + Defender for Cloud + Front Door WAF", "security", "azure", s=(4, 5, 4, 4, 3, 5),
    cost=price((5, 30), (20, 80), (80, 300), (300, 1000), (1000, 4000)), strengths=["Managed keys/secrets and posture management"],
    src=["keyvault"])
sup("gcp_sec", "Cloud Armor + Secret Manager + Cloud KMS", "security", "gcp", s=(4, 5, 4, 4, 3, 5),
    cost=price((5, 30), (20, 80), (80, 300), (300, 1000), (1000, 4000)), strengths=["WAF, managed keys and audit logs"],
    src=["gcp_compliance"])
sup("self_sec", "HashiCorp Vault/OpenBao + ModSecurity WAF (self-hosted)", "security", "self", self_host=True, ops=3,
    s=(4, 4, 3, 4, 4, 5), cost=price((10, 30), (20, 60), (60, 200), (200, 800), (800, 3000)),
    strengths=["Secrets and WAF without cloud services"], src=["compose"])
sup("hybrid_link", "Azure App Service Hybrid Connection (to on-prem)", "integration", "azure", s=(4, 3, 5, 4, 5, 4),
    cost=price((0, 10), (0, 10), (10, 20), (20, 40), (40, 80)),
    strengths=["Outbound-only TCP relay to an on-prem host:port; no inbound firewall changes"],
    src=["appservice_hybrid"])
sup("vpn_link", "Site-to-site VPN / private interconnect to on-prem", "integration", "cloud", s=(4, 4, 3, 4, 3, 5), ops=2,
    cost=price((30, 80), (30, 80), (80, 200), (200, 600), (600, 2000)),
    strengths=["Private routing between cloud and existing data centre"], src=["aws_regions"])
sup("aws_iot", "AWS IoT Core (MQTT)", "iot", "aws", s=(4, 5, 4, 4, 4, 5), cost=price((0, 5), (5, 30), (30, 200), (200, 1000), (1000, 5000)),
    strengths=["Managed MQTT with device registry and rules engine"], src=["aws_iot_core"])
sup("azure_iot_hub", "Azure IoT Hub", "iot", "azure", s=(4, 5, 4, 4, 4, 5), cost=price((0, 10), (10, 25), (25, 250), (250, 1000), (1000, 5000)),
    strengths=["Device twins and cloud-to-device messaging"], src=["azure_iot_hub"])
sup("emqx", "EMQX MQTT broker (self-hosted)", "iot", "self", self_host=True, ops=3, s=(5, 5, 3, 4, 4, 4),
    cost=SELF_SMALL, strengths=["Scales to millions of MQTT connections; runs anywhere"], src=["emqx", "mosquitto"])
sup("gcp_iot_core", "Google Cloud IoT Core", "iot", "gcp", status="eol", status_note="Retired 16 Aug 2023.",
    src=["iot_core_retired"], aliases=[r"cloud iot core", r"google iot core"])
sup("aws_iot_analytics", "AWS IoT Analytics", "iot", "aws", status="eol", status_note="End of support 15 Dec 2025.",
    src=["aws_iot_analytics"], aliases=[r"iot analytics"])
sup("nakama", "Nakama game server", "game_backend", "self", self_host=True, ops=3, s=(5, 5, 4, 4, 4, 4), langs=("go", "typescript", "lua"),
    cost=price((10, 40), (40, 150), (150, 600), (600, 2400), (2400, 9000)),
    strengths=["Matchmaking, leaderboards, realtime multiplayer and social out of the box"], src=["nakama"])
sup("colyseus", "Colyseus (authoritative rooms, Node.js)", "game_backend", "self", self_host=True, ops=3, s=(4, 4, 4, 4, 5, 4),
    langs=("typescript", "javascript"), cost=price((5, 20), (20, 80), (80, 300), (300, 1200), (1200, 5000)),
    strengths=["State-synchronised rooms for web/mobile games"], src=["colyseus"])
sup("metabase", "Metabase (self-hosted BI)", "analytics", "self", self_host=True, ops=2, s=(4, 4, 5, 4, 5, 4),
    cost=price((0, 10), (10, 40), (40, 120), (120, 400), (400, 1500)), strengths=["Dashboards on top of the primary DB"],
    src=["metabase"])

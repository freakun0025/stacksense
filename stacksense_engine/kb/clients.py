"""Frontend layer: web frameworks, mobile, desktop and game clients."""
from .common import tech

JS = ("javascript", "typescript")

# ------------------------------------------------------------------ web
tech("astro", "Astro", "web", kind="static-first meta-framework", langs=JS + ("html",), plats=("web",),
     s=(5, 4, 4, 4, 5, 4), learn=4, ops=1, mature=4, traits=("ssg", "ssr", "islands", "static_first", "content", "pwa"),
     strengths=["Ships zero JavaScript by default (islands architecture)",
                "Content collections for Markdown/MDX with type-safe frontmatter",
                "Builds to plain static files deployable on any CDN free tier"],
     limits=["App-like interactivity needs islands/hydration per component",
             "Smaller ecosystem than React meta-frameworks for complex apps"],
     src=["astro", "stateofjs", "so2025"], version="Astro 5")
tech("nextjs", "Next.js", "web", kind="React meta-framework", langs=JS, plats=("web",),
     s=(4, 5, 4, 4, 4, 4), learn=3, ops=2, mature=5, traits=("ssr", "ssg", "spa", "react", "fullstack", "pwa"),
     strengths=["Per-route SSR/SSG/ISR gives crawlable pages for SEO",
                "Largest React ecosystem and hiring pool",
                "Route handlers/server actions for light server logic"],
     limits=["Feature set is tuned for Vercel; self-hosting needs containers or OpenNext",
             "App Router caching model has a learning curve"],
     src=["nextjs", "react", "stateofjs", "so2025"], version="Next.js 15/16")
tech("react_vite", "React + Vite (SPA)", "web", kind="client-rendered SPA", langs=JS, plats=("web",),
     s=(4, 4, 4, 4, 5, 4), learn=3, ops=1, mature=5, traits=("spa", "react", "pwa", "rich_ui"),
     strengths=["Fast dev loop; deploys as static assets",
                "Huge React ecosystem incl. canvas, CRDT (Yjs) and data-grid libraries"],
     limits=["Client-side rendering is weak for SEO without prerendering",
             "Routing/data fetching choices left to the team"],
     src=["react", "vite", "stateofjs"], version="React 19 + Vite")
tech("nuxt", "Nuxt", "web", kind="Vue meta-framework", langs=JS, plats=("web",),
     s=(4, 4, 4, 4, 4, 4), learn=4, ops=2, mature=4, traits=("ssr", "ssg", "spa", "vue", "fullstack", "pwa"),
     strengths=["Vue SSR/SSG with strong conventions", "Gentle learning curve"],
     limits=["Smaller hiring pool than React"], src=["nuxt", "stateofjs"], version="Nuxt 4")
tech("sveltekit", "SvelteKit", "web", kind="Svelte meta-framework", langs=JS, plats=("web",),
     s=(5, 4, 4, 4, 4, 4), learn=4, ops=2, mature=4, traits=("ssr", "ssg", "spa", "svelte", "fullstack", "pwa"),
     strengths=["Small bundles and fast runtime (compiler-based)", "SSR/SSG adapters for many hosts"],
     limits=["Smaller ecosystem and talent pool than React/Vue"], src=["sveltekit", "stateofjs"], version="SvelteKit 2 / Svelte 5")
tech("angular", "Angular", "web", kind="enterprise SPA framework", langs=("typescript",), plats=("web",),
     s=(4, 5, 3, 5, 4, 5), learn=2, ops=2, mature=5, traits=("spa", "ssr", "angular", "rich_ui", "enterprise"),
     strengths=["Opinionated, batteries-included structure for large teams",
                "Strong typing, DI and long-term support releases"],
     limits=["Steeper learning curve", "Heavy for content sites"], src=["angular", "so2025"], version="Angular 20+")
tech("vue_vite", "Vue + Vite (SPA)", "web", kind="client-rendered SPA", langs=JS, plats=("web",),
     s=(4, 4, 4, 4, 5, 4), learn=4, ops=1, mature=5, traits=("spa", "vue", "pwa", "rich_ui"),
     strengths=["Approachable component model", "Static deploy"],
     limits=["Client-side rendering is weak for SEO"], src=["vue", "vite"], version="Vue 3")
tech("hugo", "Hugo", "web", kind="static site generator", langs=("html", "go"), plats=("web",),
     s=(5, 5, 4, 3, 5, 5), learn=3, ops=1, mature=5, traits=("ssg", "static_first", "content"),
     strengths=["Very fast builds; single binary", "Markdown-native content"],
     limits=["Go templates are unfamiliar to JavaScript developers", "Static only; no interactive app model"],
     src=["hugo"], version="Hugo 0.14x")
tech("eleventy", "Eleventy (11ty)", "web", kind="static site generator", langs=("javascript", "html"), plats=("web",),
     s=(5, 4, 4, 3, 5, 5), learn=4, ops=1, mature=4, traits=("ssg", "static_first", "content"),
     strengths=["Simple JavaScript SSG with zero client JS by default", "Many template languages"],
     limits=["Static only; no component framework for app-like pages"], src=["eleventy"], version="Eleventy 3")
tech("blazor", "Blazor (ASP.NET Core)", "web", kind="C# full-stack web UI", langs=("csharp",), plats=("web",),
     s=(4, 4, 4, 5, 4, 5), learn=3, ops=2, mature=4, traits=("ssr", "spa", "csharp_web", "enterprise", "fullstack", "rich_ui"),
     strengths=["Full-stack C#: shares models/validation with the ASP.NET Core backend",
                "Static SSR plus interactive Server/WebAssembly render modes",
                "First-class Microsoft Entra ID integration"],
     limits=["Interactive Server mode keeps a SignalR circuit per user",
             "WebAssembly mode has a larger first download"],
     src=["blazor", "aspnet", "dotnet_policy"], version=".NET 10 LTS")
tech("phaser", "Phaser", "web", kind="2D web game framework", langs=JS, plats=("web",),
     s=(4, 3, 4, 3, 5, 3), learn=4, ops=1, mature=4, traits=("game",),
     strengths=["Browser games with WebGL/Canvas", "TypeScript support"],
     limits=["2D focused; not for console/3D titles"], src=["phaser"], version="Phaser 3/4")
tech("htmx", "Server-rendered templates + HTMX", "web", kind="server-side rendering with progressive enhancement",
     langs=("python", "ruby", "php", "go", "java", "kotlin", "elixir", "csharp"), plats=("web",),
     s=(4, 4, 4, 4, 5, 4), learn=4, ops=1, mature=3, traits=("ssr", "server_templates", "needs_server", "pwa_none"),
     strengths=["Pages rendered by the backend framework's templates; no separate JavaScript build or API layer",
                "HTMX adds partial-page updates with HTML attributes instead of a SPA framework"],
     limits=["Rich offline/canvas-style interactivity still needs JavaScript islands",
             "UI and backend deploy together (fine for one team)"],
     src=["htmx", "django", "rails", "laravel", "aspnet"], version="HTMX 2 + framework templates")
# deprecated / not recommended (kept so the engine can explain why they are never chosen)
tech("cra", "Create React App", "web", kind="React toolchain", langs=JS, plats=("web",),
     s=(3, 3, 3, 2, 4, 3), learn=4, ops=1, mature=3, traits=("spa", "react"),
     status="deprecated", status_note="Deprecated by the React team on 14 Feb 2025; use Vite or a framework.",
     src=["cra_sunset"], aliases=[r"create[- ]react[- ]app", r"\bcra\b"])
tech("gatsby", "Gatsby", "web", kind="React SSG", langs=JS, plats=("web",),
     s=(4, 4, 3, 2, 4, 4), learn=3, ops=1, mature=3, traits=("ssg", "react", "content"),
     status="maintenance", status_note="Minimal release activity since 2023 (after Netlify acquisition); not advisable for new builds.",
     src=["gatsby"], aliases=[r"gatsby"])
tech("angularjs", "AngularJS (1.x)", "web", kind="legacy SPA framework", langs=("javascript",), plats=("web",),
     s=(2, 2, 2, 1, 4, 1), learn=3, ops=1, mature=2, traits=("spa",), status="eol",
     status_note="End of life since 31 Dec 2021.", src=["angularjs_eol"], aliases=[r"angular ?js", r"angular 1"])

# ------------------------------------------------------------------ mobile
tech("expo_rn", "React Native (Expo)", "mobile", kind="cross-platform mobile", langs=JS, plats=("android", "ios"),
     s=(4, 4, 5, 4, 4, 4), learn=4, ops=1, mature=5,
     traits=("cross_platform", "offline_capable", "react", "ota_updates"),
     strengths=["One TypeScript codebase for Android and iOS",
                "Reuses React skills from the web team",
                "EAS Build/Update for CI and over-the-air fixes",
                "Mature on-device SQLite (expo-sqlite, WatermelonDB) for offline-first data"],
     limits=["JS runtime overhead on very low-end phones (Hermes mitigates)",
             "Some native modules need custom development builds"],
     src=["expo", "rn", "eas", "so2025"], version="Expo SDK (New Architecture)")
tech("flutter", "Flutter", "mobile", kind="cross-platform mobile", langs=("dart",), plats=("android", "ios"),
     s=(5, 4, 4, 4, 4, 4), learn=3, ops=1, mature=5, traits=("cross_platform", "offline_capable", "low_end_ok"),
     strengths=["AOT-compiled native code with a consistent 60fps UI",
                "Single codebase for Android, iOS, web and desktop"],
     limits=["Dart is rarely already known by the team", "Larger binary than native apps"],
     src=["flutter", "so2025"], version="Flutter 3.x")
tech("kotlin_android", "Kotlin + Jetpack Compose (native Android)", "mobile", kind="native mobile",
     langs=("kotlin", "java"), plats=("android",), s=(5, 4, 3, 5, 4, 5), learn=3, ops=1, mature=5,
     traits=("native", "offline_capable", "low_end_ok", "background_sync"),
     strengths=["Best performance and memory footprint on low-end Android",
                "WorkManager + Room give robust background sync and offline storage"],
     limits=["Android only", "Needs Kotlin skills"], src=["compose", "workmanager"], version="Kotlin 2.x")
tech("swift_ios", "Swift + SwiftUI (native iOS)", "mobile", kind="native mobile", langs=("swift",), plats=("ios",),
     s=(5, 4, 3, 5, 4, 5), learn=3, ops=1, mature=5, traits=("native", "offline_capable"),
     strengths=["Best iOS performance and platform integration"], limits=["iOS only", "Needs Swift skills"],
     src=["swiftui"], version="Swift 6")
tech("kmp", "Kotlin Multiplatform + Compose Multiplatform", "mobile", kind="cross-platform (shared Kotlin)",
     langs=("kotlin", "java"), plats=("android", "ios"), s=(5, 4, 3, 4, 4, 5), learn=2, ops=1, mature=3,
     traits=("cross_platform", "native", "offline_capable", "low_end_ok"),
     strengths=["Shares business logic (and UI) in Kotlin with native performance",
                "Natural fit for JVM/Kotlin backend teams"],
     limits=["iOS tooling younger (Compose Multiplatform iOS stable since 2025)", "Smaller community than RN/Flutter"],
     src=["kmp", "cmp"], version="Kotlin 2.x")
tech("maui", ".NET MAUI", "mobile", kind="cross-platform (C#)", langs=("csharp",), plats=("android", "ios", "desktop"),
     s=(3, 3, 3, 3, 4, 4), learn=3, ops=1, mature=3, traits=("cross_platform", "offline_capable"),
     strengths=["C# across Android, iOS, Windows and macOS", "Successor to Xamarin"],
     limits=["Smaller ecosystem; tooling stability complaints", "Weaker on low-end Android"],
     src=["maui"], version=".NET 10")
tech("capacitor", "Ionic + Capacitor", "mobile", kind="hybrid web-in-native", langs=JS, plats=("android", "ios"),
     s=(3, 3, 5, 3, 5, 3), learn=5, ops=1, mature=4, traits=("cross_platform", "web_reuse"),
     strengths=["Reuses web code and skills", "Native APIs via Capacitor plugins"],
     limits=["WebView performance on low-end devices", "Less native look and feel"], src=["capacitor"])
tech("pwa", "Progressive Web App", "mobile", kind="installable web app", langs=JS, plats=("android", "ios"),
     s=(3, 3, 5, 3, 5, 3), learn=5, ops=1, mature=4, traits=("web_reuse", "no_store"),
     strengths=["No app store; one web codebase", "Installable with service-worker caching"],
     limits=["Background sync and storage persistence are limited, especially on iOS",
             "Browsers may evict offline data under storage pressure"],
     src=["pwa", "storage_eviction"])
tech("xamarin", "Xamarin", "mobile", kind="legacy cross-platform", langs=("csharp",), plats=("android", "ios"),
     s=(3, 3, 3, 1, 4, 3), learn=3, ops=1, mature=2, traits=("cross_platform",), status="eol",
     status_note="Support ended 1 May 2024; migrate to .NET MAUI.", src=["xamarin_eol"], aliases=[r"xamarin"])
tech("unity", "Unity", "mobile", kind="game engine", langs=("csharp",), plats=("android", "ios", "desktop", "web"),
     s=(5, 4, 4, 4, 4, 4), learn=3, ops=1, mature=5, traits=("game", "cross_platform"),
     strengths=["Largest mobile game engine ecosystem", "Build once for mobile, desktop, WebGL"],
     limits=["Licence tiers by revenue (Runtime Fee was cancelled in 2024)"], src=["unity", "unity_fee"], version="Unity 6")
tech("godot", "Godot", "mobile", kind="game engine", langs=("gdscript", "csharp"), plats=("android", "ios", "desktop", "web"),
     s=(4, 3, 4, 4, 5, 4), learn=4, ops=1, mature=4, traits=("game", "cross_platform"),
     strengths=["MIT-licensed, lightweight engine", "GDScript is quick to learn"],
     limits=["Smaller asset/plugin ecosystem than Unity"], src=["godot"], version="Godot 4")

# ------------------------------------------------------------------ desktop
tech("electron", "Electron", "desktop", kind="desktop (web tech)", langs=JS, plats=("desktop",),
     s=(3, 3, 5, 4, 4, 3), learn=4, ops=1, mature=5, traits=("web_reuse",),
     strengths=["Reuses web skills; proven by VS Code, Slack"], limits=["High memory use (bundled Chromium)"],
     src=["electron"])
tech("tauri", "Tauri", "desktop", kind="desktop (web UI + Rust core)", langs=JS + ("rust",), plats=("desktop",),
     s=(5, 4, 4, 4, 5, 4), learn=3, ops=1, mature=4, traits=("web_reuse",),
     strengths=["Small binaries using the OS WebView", "Rust core with a strict permission model"],
     limits=["Native logic needs Rust", "WebView rendering differs per OS"], src=["tauri"], version="Tauri 2")
tech("maui_desktop", ".NET MAUI / WinUI (desktop)", "desktop", kind="desktop (C#)", langs=("csharp",), plats=("desktop",),
     s=(4, 3, 4, 4, 4, 4), learn=3, ops=1, mature=4, traits=(),
     strengths=["Native Windows apps in C#"], limits=["Windows-first; macOS via MAUI only"], src=["maui"])
tech("flutter_desktop", "Flutter (desktop)", "desktop", kind="desktop (Dart)", langs=("dart",), plats=("desktop",),
     s=(4, 3, 4, 4, 4, 4), learn=3, ops=1, mature=3, traits=(),
     strengths=["Shares code with Flutter mobile"], limits=["Desktop plugins less mature"], src=["flutter"])

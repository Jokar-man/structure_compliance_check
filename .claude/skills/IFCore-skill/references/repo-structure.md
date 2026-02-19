# Repository Structure

## Team repos — `ifcore-team-a` … `ifcore-team-e`

```
ifcore-team-a/
├── tools/
│   ├── checker_doors.py
│   ├── checker_fire_safety.py
│   └── checker_rooms.py
├── requirements.txt
├── AGENTS.md
└── README.md
```

## Platform monorepo — `ifcore-platform`

```
ifcore-platform/
├── backend/               → HuggingFace Space
│   ├── README.md              ← HF frontmatter (sdk: docker, app_port: 7860)
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py
│   ├── orchestrator.py
│   ├── deploy.sh
│   └── teams/                 ← gitignored, populated by deploy.sh
│       ├── ifcore-team-a/tools/checker_*.py
│       └── ...
└── frontend/              → Cloudflare Pages + Worker
    ├── public/index.html
    ├── src/
    │   ├── app.js
    │   ├── api.js
    │   ├── store.js
    │   ├── poller.js
    │   └── modules/
    │       ├── upload/index.js
    │       ├── results/index.js
    │       ├── viewer-3d/index.js
    │       └── dashboard/index.js
    ├── functions/api/[[route]].js
    ├── migrations/0001_create_jobs.sql
    ├── package.json
    └── wrangler.toml
```

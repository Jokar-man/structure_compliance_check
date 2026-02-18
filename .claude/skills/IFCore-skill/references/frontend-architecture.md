# Frontend Architecture

Modular web app. Each feature is a self-contained module. Backend ops are async jobs.

## Structure

```
src/
├── app.js          ← shell: nav bar + router
├── api.js          ← shared API client → CF Worker
├── store.js        ← shared state (Zustand)
├── poller.js       ← polls active jobs, updates store
├── modules/
│   ├── upload/
│   ├── results/
│   ├── viewer-3d/
│   └── dashboard/
└── shared/
```

## Async Job Pattern

```
Frontend → POST /check → Worker → HF Space → {jobId}
Frontend → GET /jobs/id (every 2s) → Worker reads D1 → {status}
HF Space → POST /jobs/id/complete → Worker writes D1 → frontend gets results
```

### Recipe: Adding a New Async Endpoint

| File | What to add |
|------|-------------|
| HF Space `main.py` | POST /your-thing → BackgroundTasks → callback to Worker |
| Worker | Proxy route for POST /api/your-thing |
| Frontend `api.js` | startYourThing() → returns {jobId} → store.trackJob(jobId) |

## Shared State (Zustand)

```javascript
{
  currentFile: null,
  jobs: {},
  activeJobId: null,
  trackJob(jobId),
  completeJob(jobId, data),
  getActiveResults(),
}
```

## Module Pattern

```javascript
export function mount(container) {
  function render() {
    const results = useStore.getState().getActiveResults()
    container.innerHTML = `${passed} passed, ${failed} failed`
  }
  render()
  useStore.subscribe(render)
}
```

## Database (D1 Tables)

- `users` — id, name, team, created_at
- `projects` — id, user_id, name, file_url, ifc_schema, region, building_type, metadata, created_at
- `check_results` — id, project_id, job_id, check_name, team, status, summary, has_elements, created_at
- `element_results` — id, check_result_id, element_id, element_type, element_name, element_name_long, check_status, actual_value, required_value, comment, log

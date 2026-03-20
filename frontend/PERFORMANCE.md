# Frontend Performance Workflow

## Bundle analysis

```powershell
cd frontend
C:\nvm4w\nodejs\npm.cmd run analyze
```

Inspect the graph chunk, metrics/chart chunk, and shared chunk.

## Lighthouse

Run Lighthouse against:

- `http://127.0.0.1:3000/dashboard`

Focus on:

- Time to Interactive
- Total Blocking Time
- JavaScript execution cost

## Chrome Performance Profiler

Record:

- creating a pipeline
- watching live agent updates
- filtering execution logs

Look for:

- long tasks
- repeated style/layout recalculation
- scripting spikes while polling

## React DevTools Profiler

Profile rerenders during:

- live polling
- prompt submission
- history selection

Goal:

- only active panels rerender
- the full dashboard does not rerender every second

## Web Vitals

Vitals are captured client-side and exposed on:

- `window.__ADEA_WEB_VITALS__`

Track:

- `LCP`
- `INP`
- `CLS`

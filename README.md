# kushagrasanwal.com

Personal site built with Hugo. Auto-deploys to Cloudflare Pages on push to `main`.

## Writing a new post

```bash
hugo new posts/my-post-title.md
```

Then edit the file in `content/posts/`, set `draft: false`, and push.

## Local preview

```bash
hugo server -D
```

Visit `http://localhost:1313`

## Deploy

Push to `main`. Cloudflare Pages picks it up automatically.

## Jain Surfers (/jain-surfers/)

A self-contained endless-runner game in one file: `static/jain-surfers/index.html`. Hugo copies
`static/` through untouched, so it needs no layout, config or build change, and nothing else on the
site depends on it. No dependencies, no external requests, no backend.

- **Run locally:** `hugo server` and open `http://localhost:1313/jain-surfers/`, or just open the
  file in a browser.
- **Update:** edit `static/jain-surfers/index.html` on a branch and push. Cloudflare Pages builds a
  preview for the branch; check `/jain-surfers/` there, then merge to `main`. Gameplay numbers are in
  the `tuning` block near the top of the script.
- **Test:** `pip install playwright`, then `CHROME=/path/to/chrome python3 tests/jain-surfers/run.py`
  (28 headless checks; screenshots go to `tests/jain-surfers/shots/`).
- **Roll back:** in Cloudflare Pages > Deployments, choose the previous production deployment >
  "Rollback to this deployment"; or revert the merge commit on `main`.
- **Remove:** delete `static/jain-surfers/` and `tests/jain-surfers/`.

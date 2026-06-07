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

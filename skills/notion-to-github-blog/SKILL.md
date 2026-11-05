---
name: notion-to-github-blog
description: Convert user-authorized Notion technical notes into GitHub Pages blog posts with locally hosted images and a reviewable pull request.
---

# Notion → GitHub Blog Publishing Skill

## Target
- Repository: `syslians/syslians.github.io`
- Default branch: `main`
- Posts: `_posts/YYYY-MM-DD-descriptive-slug.md`
- Images: `assets/images/posts/YYYY-MM-DD-descriptive-slug/NN-short-name.ext`
- Source: user-provided Notion page URL
- Preserve the original Notion page unchanged.

## Required workflow

1. Fetch the Notion page and inspect full text, code blocks, tables, images, metadata, and any truncation warnings.
2. Inspect repository conventions and existing posts; never overwrite existing paths.
3. Create a new descriptive branch from `main` and use a new post filename.
4. Export/download **every** Notion image as bytes. Preserve image order and meaningful captions; use descriptive numbered filenames. Verify image MIME type, extension, and successful download. Do not substitute unrelated screenshots or link to expiring Notion URLs.
5. Upload image binaries to `assets/images/posts/<slug>/`. For binary files use an API that supports base64 blobs/trees or a Git checkout, not a UTF-8-only file creation API. Verify each GitHub asset path exists before changing Markdown.
6. Reference uploaded assets from Jekyll posts, e.g.:

   `![UNION SELECT output]({{ '/assets/images/posts/2026-11-05-bwapp-sqli/02-union-output.png' | relative_url }})`

7. Generate a Markdown post with appropriate YAML front matter (`layout`, `title`, `date`, `categories`, `tags`). Preserve SQL code fences and correct formatting. Clearly distinguish original content from editorial corrections.
8. Review security and privacy: remove tokens, cookies, API keys, live credentials and personal data; label any retained synthetic lab credentials. Avoid unsupported claims about hash algorithms or salt.
9. Validate that post links and local image paths resolve. Review GitHub Pages/Jekyll build if available.
10. Open a PR targeting `main` and describe changed files, image count, validation, and limitations. Never push directly to `main` or overwrite existing posts.
11. Keep PR as draft if images, build validation, or other required checks are incomplete. Do not claim publication until the PR is merged and the site is deployed.
12. Only merge the PR after explicit user instruction or a clear pre-existing authorization to merge; check mergeability and CI first.

## Missing image access

If Notion provides only `notion-file-block://` references and no downloadable image URLs or bytes, **do not fabricate images or pretend they were uploaded**. Request a Notion export (Markdown & CSV with subpages/images) or image attachments, then complete steps 4–10. Keep the PR in draft until done.

## Source traceability

Add a link to the original Notion page and retain the publication date. For updates, create a new PR and avoid replacing existing files without explicit authorization.

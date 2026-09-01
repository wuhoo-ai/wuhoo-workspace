# PDF Delivery via WeChat MEDIA Tags

## Size Limit

WeChat CDN rejects PDFs > ~100KB with HTTP 500. Compress with pymupdf:
```python
import fitz
d = fitz.open('file.pdf')
d.save('file.pdf.tmp', garbage=4, deflate=True, clean=True)
d.close()
os.rename('file.pdf.tmp', 'file.pdf')
```

## Batch Delivery Pattern

- **3 PDFs per message** — reliable delivery rate
- Single PDF: often works but 30s intervals may trigger rate limiting
- Many PDFs in one message: some silently dropped

## File Naming

- Chinese filenames in MEDIA paths work but sometimes fail silently
- If delivery fails, copy to `/tmp/simple_name.pdf` and retry
- `hermes send -t weixin "MEDIA:/tmp/file.pdf"` — times out; use inline MEDIA in response instead

## Background Process Noise

`terminal(background=True, notify_on_complete=True)` sends process stdout to the user as a message. For long simulations, suppress verbose output or use `grep -v` to filter before delivery.

## Common Failure Patterns

| Symptom | Likely Cause |
|---------|-------------|
| CDN upload HTTP 500 | File > 100KB |
| Empty response to user | MEDIA tag silently failed (wrong path, CDN error) |
| User receives raw logs | bg process notify_on_complete delivered stdout |

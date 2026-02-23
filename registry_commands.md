* **List all repositories (images):**
```bash
curl -X GET http://localhost:5000/v2/_catalog

```


* **List all tags for a specific image:**
```bash
curl -X GET http://localhost:5000/v2/video_processor/tags/list

```


* **Check registry health:**
```bash
curl -i http://localhost:5000/v2/

```

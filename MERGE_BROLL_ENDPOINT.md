# B-Roll Merge Endpoint Documentation

## Overview

The `/tasks/merge-broll` endpoint allows you to overlay 6 B-roll videos on top of a main video at specific timestamps. This is perfect for creating dynamic content where you want to show supplementary footage during specific moments of your main video.

## Endpoint

```
POST /tasks/merge-broll
```

## How It Works

1. Submit a main video and 6 B-roll videos with timing information
2. Receive a `task_id` immediately
3. Poll the status endpoint to check progress
4. Download the final merged video when complete

## Request Format

### Request Body

```json
{
  "main_video_url": "https://example.com/main.mp4",
  "broll_urls": [
    "https://example.com/broll1.mp4",
    "https://example.com/broll2.mp4",
    "https://example.com/broll3.mp4",
    "https://example.com/broll4.mp4",
    "https://example.com/broll5.mp4",
    "https://example.com/broll6.mp4"
  ],
  "broll_timings": [
    [3.0, 6.0],
    [8.0, 11.0],
    [13.0, 15.0],
    [17.0, 20.0],
    [22.0, 25.0],
    [27.0, 30.0]
  ]
}
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `main_video_url` | string (URL) | Yes | URL of the main video file |
| `broll_urls` | array[string] | Yes | Array of exactly 6 B-roll video URLs |
| `broll_timings` | array[array[float]] | Yes | Array of exactly 6 `[start, end]` timing pairs in seconds |

### Validation Rules

- **Exactly 6 B-rolls required**: You must provide exactly 6 B-roll videos
- **Exactly 6 timings required**: You must provide exactly 6 timing pairs
- **Timing format**: Each timing must be `[start_time, end_time]` in seconds
- **Start < End**: Start time must be less than end time for each pair
- **File size limit**: Total size of all videos cannot exceed 700MB (100MB × 7 files)

## Response Format

### Success Response (201 Created)

```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "message": "B-roll merge task queued successfully"
}
```

### Error Responses

#### 400 Bad Request
```json
{
  "detail": "Exactly 6 B-roll videos are required"
}
```

#### 413 Payload Too Large
```json
{
  "detail": "Total file size 850.5MB exceeds limit of 700MB"
}
```

## Checking Task Status

After submitting a task, poll the status endpoint:

```
GET /tasks/{task_id}
```

### Response

```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "success",
  "video_url": "https://your-app.railway.app/video/550e8400-e29b-41d4-a716-446655440000_broll_merged.mp4",
  "error": null,
  "created_at": "2025-10-27T12:00:00Z",
  "updated_at": "2025-10-27T12:05:00Z",
  "completed_at": "2025-10-27T12:05:00Z"
}
```

### Status Values

- `queued`: Task is waiting to be processed
- `running`: Task is currently being processed
- `success`: Task completed successfully, `video_url` is available
- `failed`: Task failed, `error` contains the error message

## Complete Example

### Using cURL

```bash
# Submit the task
curl -X POST "https://your-app.railway.app/tasks/merge-broll" \
  -H "Content-Type: application/json" \
  -d '{
    "main_video_url": "https://v3b.fal.media/files/b/kangaroo/main_video.mp4",
    "broll_urls": [
      "https://v3b.fal.media/files/b/zebra/broll1.mp4",
      "https://v3b.fal.media/files/b/panda/broll2.mp4",
      "https://v3b.fal.media/files/b/lion/broll3.mp4",
      "https://v3b.fal.media/files/b/panda/broll4.mp4",
      "https://v3b.fal.media/files/b/monkey/broll5.mp4",
      "https://v3b.fal.media/files/b/monkey/broll6.mp4"
    ],
    "broll_timings": [
      [3.0, 6.0],
      [8.0, 11.0],
      [13.0, 15.0],
      [17.0, 20.0],
      [22.0, 25.0],
      [27.0, 30.0]
    ]
  }'

# Response:
# {
#   "task_id": "abc123...",
#   "status": "queued",
#   "message": "B-roll merge task queued successfully"
# }

# Check status (poll every 5-10 seconds)
curl "https://your-app.railway.app/tasks/abc123..."

# When status is "success", download the video
curl -O "https://your-app.railway.app/video/abc123..._broll_merged.mp4"
```

### Using Python

```python
import requests
import time

# API base URL
BASE_URL = "https://your-app.railway.app"

# Submit the task
response = requests.post(f"{BASE_URL}/tasks/merge-broll", json={
    "main_video_url": "https://example.com/main.mp4",
    "broll_urls": [
        "https://example.com/broll1.mp4",
        "https://example.com/broll2.mp4",
        "https://example.com/broll3.mp4",
        "https://example.com/broll4.mp4",
        "https://example.com/broll5.mp4",
        "https://example.com/broll6.mp4"
    ],
    "broll_timings": [
        [3.0, 6.0],
        [8.0, 11.0],
        [13.0, 15.0],
        [17.0, 20.0],
        [22.0, 25.0],
        [27.0, 30.0]
    ]
})

task_data = response.json()
task_id = task_data["task_id"]
print(f"Task submitted: {task_id}")

# Poll for completion
while True:
    status_response = requests.get(f"{BASE_URL}/tasks/{task_id}")
    status = status_response.json()

    print(f"Status: {status['status']}")

    if status['status'] == 'success':
        print(f"Video URL: {status['video_url']}")
        break
    elif status['status'] == 'failed':
        print(f"Error: {status['error']}")
        break

    time.sleep(5)  # Wait 5 seconds before checking again
```

### Using JavaScript (Fetch API)

```javascript
const BASE_URL = 'https://your-app.railway.app';

// Submit the task
const response = await fetch(`${BASE_URL}/tasks/merge-broll`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    main_video_url: 'https://example.com/main.mp4',
    broll_urls: [
      'https://example.com/broll1.mp4',
      'https://example.com/broll2.mp4',
      'https://example.com/broll3.mp4',
      'https://example.com/broll4.mp4',
      'https://example.com/broll5.mp4',
      'https://example.com/broll6.mp4'
    ],
    broll_timings: [
      [3.0, 6.0],
      [8.0, 11.0],
      [13.0, 15.0],
      [17.0, 20.0],
      [22.0, 25.0],
      [27.0, 30.0]
    ]
  })
});

const { task_id } = await response.json();
console.log(`Task submitted: ${task_id}`);

// Poll for completion
const pollStatus = async () => {
  const statusResponse = await fetch(`${BASE_URL}/tasks/${task_id}`);
  const status = await statusResponse.json();

  console.log(`Status: ${status.status}`);

  if (status.status === 'success') {
    console.log(`Video URL: ${status.video_url}`);
    return status.video_url;
  } else if (status.status === 'failed') {
    throw new Error(status.error);
  } else {
    // Still processing, check again in 5 seconds
    await new Promise(resolve => setTimeout(resolve, 5000));
    return pollStatus();
  }
};

const videoUrl = await pollStatus();
```

## How B-Roll Timing Works

The `broll_timings` array defines when each B-roll appears:

```json
"broll_timings": [
  [3.0, 6.0],   // B-roll 1 shows from 3s to 6s
  [8.0, 11.0],  // B-roll 2 shows from 8s to 11s
  [13.0, 15.0], // B-roll 3 shows from 13s to 15s
  [17.0, 20.0], // B-roll 4 shows from 17s to 20s
  [22.0, 25.0], // B-roll 5 shows from 22s to 25s
  [27.0, 30.0]  // B-roll 6 shows from 27s to 30s
]
```

### Visual Timeline

```
Main Video:  |------------------------------------------|
             0    5    10   15   20   25   30
B-roll 1:         |===|
B-roll 2:              |===|
B-roll 3:                   |==|
B-roll 4:                       |===|
B-roll 5:                            |===|
B-roll 6:                                 |===|
```

During the specified time ranges, the B-roll video will overlay and cover the main video. The audio from the main video is preserved throughout.

## Technical Details

### Video Processing

- **Resolution**: All B-rolls are scaled to 1080x1920 (vertical/portrait format)
- **Aspect Ratio**: B-rolls are cropped to fit the 9:16 aspect ratio
- **Audio**: Original main video audio is preserved
- **Codec**: Output uses H.264 video codec with AAC audio
- **Preset**: Uses `ultrafast` preset for quick processing

### Processing Time

Processing time depends on:
- Video length and resolution
- Number of B-rolls
- Server resources

Typical processing time: 2-5 minutes for 30-second videos

### File Cleanup

Processed videos are automatically deleted after 2 hours to save storage space. Make sure to download your video within this timeframe.

## Error Handling

### Common Errors

1. **Invalid URL**: One or more video URLs are not accessible
   ```json
   {
     "detail": "Unable to access URL https://example.com/video.mp4: HTTP 404"
   }
   ```

2. **Wrong number of B-rolls**:
   ```json
   {
     "detail": "Exactly 6 B-roll videos are required"
   }
   ```

3. **Invalid timing format**:
   ```json
   {
     "detail": "B-roll timing 3 start time must be less than end time"
   }
   ```

4. **File too large**:
   ```json
   {
     "detail": "Total file size 850.5MB exceeds limit of 700MB"
   }
   ```

### Retry Logic

If a task fails:
1. Check the error message in the status response
2. Fix the issue (e.g., correct video URL, adjust file sizes)
3. Submit a new task

## API Interactive Documentation

Visit your deployment's interactive API documentation:

- **Swagger UI**: `https://your-app.railway.app/docs`
- **ReDoc**: `https://your-app.railway.app/redoc`

These provide interactive testing capabilities and detailed schema information.

## Support

For issues or questions:
1. Check the task status error message
2. Review server logs for detailed error information
3. Verify all video URLs are publicly accessible
4. Ensure total file sizes are within limits

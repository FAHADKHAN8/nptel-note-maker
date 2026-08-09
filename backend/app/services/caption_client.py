import httpx
from ..config import Settings
from ..errors import AppError


class CaptionClient:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def fetch(self, video_id: str, language: str = "en") -> dict:
        try:
            async with httpx.AsyncClient(timeout=self.settings.caption_service_timeout) as client:
                response = await client.post(f"{self.settings.caption_service_url.rstrip('/')}/captions", json={"videoId": video_id, "language": language})
        except httpx.HTTPError as exc:
            raise AppError("CAPTION_SERVICE_UNAVAILABLE", "Caption service is unavailable.", 503) from exc
        if response.status_code == 404:
            raise AppError("CAPTIONS_NOT_FOUND", "English captions were not available for this lecture.", 404)
        if response.is_error:
            raise AppError("CAPTION_SERVICE_UNAVAILABLE", "Caption service returned an error.", 502)
        return response.json()

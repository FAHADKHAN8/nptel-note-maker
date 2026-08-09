import express from "express";
import he from "he";
import { getSubtitles } from "youtube-captions-scraper";

const app = express();
const port = Number(process.env.PORT || 3001);
const timeoutMs = Number(process.env.CAPTION_REQUEST_TIMEOUT || 60000);
const videoIdPattern = /^[A-Za-z0-9_-]{11}$/;

app.use(express.json({ limit: "8kb" }));

function cleanText(text) {
  return he.decode(String(text || "")).replace(/\s+/g, " ").trim();
}

app.get("/health", (_req, res) => res.json({ status: "ok" }));

app.post("/captions", async (req, res) => {
  const { videoId, language = "en" } = req.body || {};
  if (!videoIdPattern.test(videoId || "")) {
    return res.status(400).json({ error: { code: "INVALID_YOUTUBE_VIDEO_ID", message: "videoId must be exactly 11 valid YouTube ID characters.", details: null } });
  }
  const timeout = new Promise((_, reject) => setTimeout(() => reject(new Error("CAPTION_TIMEOUT")), timeoutMs));
  try {
    const captions = await Promise.race([getSubtitles({ videoID: videoId, lang: language }), timeout]);
    if (!captions?.length) {
      return res.status(404).json({ error: { code: "CAPTIONS_NOT_FOUND", message: "Captions were not available.", details: null } });
    }
    const segments = captions.map((item) => ({ start: Number(item.start || 0), duration: Number(item.dur || 0), text: cleanText(item.text) })).filter((x) => x.text);
    return res.json({ videoId, language, source: "youtube_captions", transcript: segments.map((x) => x.text).join(" "), segments });
  } catch (error) {
    if (String(error.message).includes("TIMEOUT")) {
      return res.status(504).json({ error: { code: "CAPTION_SERVICE_TIMEOUT", message: "Caption request timed out.", details: null } });
    }
    return res.status(404).json({ error: { code: "CAPTIONS_NOT_FOUND", message: "Captions were not available.", details: null } });
  }
});

app.listen(port, () => console.log(`caption-service listening on ${port}`));

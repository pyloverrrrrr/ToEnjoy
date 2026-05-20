from pydantic import BaseModel, Field


class VoiceTranscribeResponse(BaseModel):
    text: str = Field(..., description="转写后的文本")
    duration_ms: int = Field(default=0, description="音频时长（毫秒）")


class VoiceSynthesizeRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000, description="要合成的文本")
    voice: str = Field(default="zh_female_qingxin", description="音色标识")
    speed: float = Field(default=1.0, ge=0.5, le=2.0, description="语速倍率")


class VoiceSynthesizeResponse(BaseModel):
    audio_url: str = Field(..., description="DashScope OSS 音频 URL，前端直接加载播放")

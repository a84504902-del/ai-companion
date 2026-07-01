"""TTS 语音合成模块"""
import os
import hashlib
import tempfile
from config import TTS_VOICE


async def synthesize(text):
    """调用 Edge TTS 合成语音"""
    try:
        import edge_tts
    except ImportError:
        raise RuntimeError("edge-tts 未安装")

    text_hash = hashlib.md5(text.encode()).hexdigest()[:12]
    output_file = os.path.join(tempfile.gettempdir(), f"tts_{text_hash}.mp3")

    if os.path.exists(output_file):
        return output_file

    clean_text = text.replace("*", "").replace("**", "").replace("#", "")
    clean_text = clean_text.replace("【", "").replace("】", "").strip()

    if not clean_text:
        raise ValueError("文本为空")

    communicate = edge_tts.Communicate(clean_text, TTS_VOICE)
    await communicate.save(output_file)

    return output_file


def get_audio_url(text_hash):
    return f"/audio/{text_hash}"

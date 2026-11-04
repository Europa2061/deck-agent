"""将原生取消结果转换为会话中的中断提示，原始 Pi 记录仍由 Pi 保存。"""
import re


def is_abort_error(value):
    return bool(re.fullmatch(r"(?:AbortError:\s*)?(?:(?:this|the)\s+)?operation\s+(?:was\s+)?aborted[.!]?|aborted[.!]?", str(value or "").strip(), re.IGNORECASE))


def is_user_interruption(message):
    return message.get("role") == "assistant" and (
        message.get("stopReason") == "aborted" or is_abort_error(message.get("errorMessage"))
    )


def message_view(message):
    result = dict(message)
    if is_user_interruption(message):
        result["userInterrupted"] = True
        result.pop("errorMessage", None)
    return result

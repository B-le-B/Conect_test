# translator.py
import requests
import json
import logging
from typing import Optional

# 从 config.py 导入配置 (这些现在只作为绝对的后备，如果调用者完全没提供)
# 更好的做法是让调用者 (app.py) 总是提供这些，或者在 Translator 初始化时就报错
try:
    from config import API_KEY as FALLBACK_API_KEY_CONFIG, \
                       BASE_URL as FALLBACK_BASE_URL_CONFIG, \
                       DEFAULT_MODEL as FALLBACK_MODEL_CONFIG
except ImportError:
    FALLBACK_API_KEY_CONFIG = None
    FALLBACK_BASE_URL_CONFIG = None
    FALLBACK_MODEL_CONFIG = None


logger = logging.getLogger(__name__)

# 考虑将类名改为更通用的，例如 LLMAPITranslator 或 APITranslator
class SiliconFlowTranslator: # Or GenericLLMTranslator
    def __init__(self, api_key: str, base_url: str, model: str, platform_id: Optional[str] = None): # platform_id is new
        # 现在强制要求调用者 (app.py) 提供这些值
        if not api_key:
            raise ValueError("API Key must be provided for translator initialization.")
        if not base_url:
            raise ValueError("Base URL must be provided for translator initialization.")
        if not model:
            raise ValueError("Model must be provided for translator initialization.")

        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.platform_id = platform_id if platform_id else self._infer_platform_from_url(base_url) # Infer platform if not given

        # Headers 将在 _make_request 中动态构建
        # self.headers 不再在这里固定设置

        logger.info(f"Translator initialized for platform: {self.platform_id}, Base URL: {self.base_url}, Model: {self.model}, API Key: {'SET' if self.api_key else 'NOT SET'}")

    def _infer_platform_from_url(self, url: str) -> str:
        """简单的根据URL推断平台的方法，app.py中传递platform_id更可靠"""
        if "api.siliconflow.cn" in url: return "siliconflow"
        if "api-inference.modelscope.cn" in url: return "modelscope"
        if "openrouter.ai" in url: return "openrouter"
        if "api.openai.com" in url: return "openai"
        if "api.deepseek.com" in url: return "deepseek"
        if "api.moonshot.cn" in url: return "moonshot"
        if "localhost:11434" in url: return "ollama" # Ollama
        return "custom" # 默认或未知

    def _get_headers(self) -> dict:
        """
        根据推断的平台动态构造请求头。
        这是关键的修改点。
        """
        common_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json" # 有些API可能需要这个
        }

        # 平台特定的 Header 逻辑
        # **你需要查阅每个平台的确切 API 文档来确定正确的认证方式**
        if self.platform_id == "modelscope":
            # ModelScope 通常使用 Bearer token，但也有一些旧API可能直接用token。
            # 假设它需要 Bearer token, key 本身就是 token 字符串
            common_headers["Authorization"] = f"Bearer {self.api_key}"
            # ModelScope 的流式API可能需要特定的Header, 例如：
            # common_headers["X-DashScope-SSE"] = "enable" # 如果是SSE并且API需要
            logger.debug(f"Using ModelScope specific headers. Key starts with: {self.api_key[:5] if self.api_key else 'None'}")
        elif self.platform_id == "openrouter":
            common_headers["Authorization"] = f"Bearer {self.api_key}"
            # OpenRouter 推荐添加这些 (从你的项目根 URL 和应用名称替换)
            # common_headers["HTTP-Referer"] = os.getenv("OPENROUTER_REFERRER", "http://localhost:5000")
            # common_headers["X-Title"] = os.getenv("OPENROUTER_APP_TITLE", "MyTranslatorApp")
        elif self.platform_id == "ollama":
            # Ollama 本地通常不需要认证头，但如果你的Ollama配置了，需要相应添加
            # 如果 ollama API key 存在，可以像其他平台一样添加 Bearer token
            if self.api_key and self.api_key.lower() != "none" and self.api_key.lower() != "ollama": # 假设 'ollama' 或 'none' 表示无key
                 common_headers["Authorization"] = f"Bearer {self.api_key}"
            logger.debug("Using Ollama specific headers (potentially no auth).")
        # 对于 SiliconFlow, OpenAI, DeepSeek, Moonshot，Bearer token 通常是正确的
        elif self.platform_id in ["siliconflow", "openai", "deepseek", "moonshot"]:
            common_headers["Authorization"] = f"Bearer {self.api_key}"
        else: # "custom" 或其他未知平台，默认使用 Bearer token
            if self.api_key: # 只有当提供了API Key时才添加Auth头
                common_headers["Authorization"] = f"Bearer {self.api_key}"
            logger.debug(f"Using default Bearer token auth for platform: {self.platform_id}")
        
        return common_headers

    def translate(self, text: str, target_lang: str, source_lang: Optional[str] = None, stream: bool = False):
        if not text:
            logger.warning("Attempted translation with empty text.") # Changed to warning
            return "Error: Text to translate cannot be empty." if not stream else self._yield_error_stream("Text to translate cannot be empty.")
        if not target_lang:
            logger.warning("Attempted translation with empty target language.")
            return "Error: Target language cannot be empty." if not stream else self._yield_error_stream("Target language cannot be empty.")

        messages = [
            {"role": "system", "content": "You are a professional and helpful translator. Translate accurately and naturally."},
        ]
        if source_lang:
            messages.append({"role": "user", "content": f"Translate the following text from {source_lang} to {target_lang}:\n\n{text}"})
        else:
            messages.append({"role": "user", "content": f"Translate the following text to {target_lang}:\n\n{text}"})

        payload = {
            "model": self.model,
            "messages": messages,
            # "temperature": 0.7, # 可以根据平台和模型调整，或设为可配置
            # "max_tokens": 2000, # 同上
            "stream": stream
        }
        # 一些平台可能需要不同的temperature/max_tokens默认值或不支持它们
        if self.platform_id not in ["ollama"]: # Ollama 的 /api/chat 不直接支持这些顶级参数
            payload["temperature"] = 0.7
            payload["max_tokens"] = 4000 # 增加一些以防长文本被截断

        api_endpoint = "/chat/completions" # 大多数 OpenAI 兼容 API 使用此端点
        full_api_url = f"{self.base_url.rstrip('/')}{api_endpoint}"
        
        request_headers = self._get_headers() # 动态获取 Headers

        try:
            # Log a part of the key for verification, but not the whole thing
            masked_key = f"{self.api_key[:5]}...{self.api_key[-4:]}" if self.api_key and len(self.api_key) > 8 else "Provided (short or empty)"
            logger.info(f"Sending {'STREAM' if stream else 'NON-STREAM'} request to: {full_api_url} for platform {self.platform_id} with model {self.model}, API Key ends with ...{masked_key[-4:] if masked_key != 'Provided (short or empty)' else masked_key}")
            # logger.debug(f"Request Headers: {request_headers}") # 打印实际发送的头
            # logger.debug(f"Request Payload: {json.dumps(payload)}")

            if stream:
                response = requests.post(full_api_url, headers=request_headers, json=payload, stream=True, timeout=(10, 180)) # 增加读超时
                # 对于流，我们不在获得初始响应时就 raise_for_status，因为错误可能在流的中间
                # 但可以检查初始状态码
                if response.status_code >= 400:
                    error_content = response.text # 尝试读取错误响应体
                    response.close() # 确保关闭连接
                    logger.error(f"Initial API HTTP Error {response.status_code} for STREAM request to {full_api_url}. Platform: {self.platform_id}. Response: {error_content[:500]}")
                    # 返回一个可迭代的错误，这样 app.py 中的流处理逻辑可以接收到它
                    return self._yield_error_stream(f"API Error {response.status_code}: {error_content[:200]}")
                return response # 返回原始的 requests.Response 对象
            else: # Non-stream
                response = requests.post(full_api_url, headers=request_headers, json=payload, timeout=60) # 增加超时
                response.raise_for_status() # This will raise HTTPError for 4xx/5xx
                data = response.json()
                # logger.debug(f"Received NON-STREAM response: {json.dumps(data)}")
                if data and data.get("choices") and data["choices"][0].get("message") and data["choices"][0]["message"].get("content"):
                    translated_text = data["choices"][0]["message"]["content"].strip()
                    return translated_text
                else:
                    error_msg = f"No translation found in non-stream response or unexpected format from {self.platform_id}. Raw: {json.dumps(data, indent=2)[:500]}"
                    logger.error(error_msg)
                    return f"Error: {error_msg}"

        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response is not None else "Unknown"
            response_text = e.response.text if e.response is not None else "No response text"
            try:
                # 尝试解析JSON错误体
                error_details_json = e.response.json() if e.response is not None else {}
                message = error_details_json.get("error", {}).get("message", response_text) # OpenAI style
                if not message or message == response_text: # Try other common error structures
                    message = error_details_json.get("errors", {}).get("message", response_text) # ModelScope style
                if not message or message == response_text:
                    message = error_details_json.get("detail", response_text) # Some other APIs
                detail_json_str = json.dumps(error_details_json) if error_details_json else response_text
            except json.JSONDecodeError:
                message = response_text
                detail_json_str = response_text

            error_msg_prefix = f"API HTTP Error {status_code}"
            specific_error_msg = self._get_specific_http_error_message(status_code)
            
            full_error_output = f"{error_msg_prefix}: {specific_error_msg}\nDetails: {message}"
            logger.error(f"HTTPError for {self.platform_id}: {full_error_output}. Raw response: {detail_json_str[:500]}")
            return full_error_output if not stream else self._yield_error_stream(full_error_output)

        except requests.exceptions.RequestException as e: # Catches ConnectionError, Timeout, etc.
            error_msg = f"Network/Request Error for {self.platform_id}: {type(e).__name__} - {e}"
            logger.error(error_msg)
            return error_msg if not stream else self._yield_error_stream(error_msg)
        except json.JSONDecodeError as e: # Should be caught by non-stream part primarily
            raw_response_text = response.text if 'response' in locals() and hasattr(response, 'text') else 'No response text available.'
            error_msg = f"JSON Decode Error from {self.platform_id}: Could not decode API response. {e}. Raw: {raw_response_text[:200]}"
            logger.error(error_msg)
            return error_msg if not stream else self._yield_error_stream(error_msg)
        except Exception as e: # Catch-all for other unexpected errors
            import traceback
            error_msg = f"Unexpected error in translator for {self.platform_id}: {type(e).__name__} - {e}"
            logger.error(f"{error_msg}\n{traceback.format_exc()}")
            return error_msg if not stream else self._yield_error_stream(error_msg)

    def _get_specific_http_error_message(self, status_code: int) -> str:
        """Helper to get a more specific message based on status code."""
        if status_code == 401: return "Unauthorized. API Key is invalid, missing, or expired."
        if status_code == 403: return "Forbidden. API Key may lack permissions for this model/operation."
        if status_code == 404: return f"Not Found. Model '{self.model}' or API endpoint incorrect."
        if status_code == 429: return "Rate Limit Exceeded. Please wait and try again or check your plan."
        if status_code >= 500: return "API Server Error. Please try again later."
        return "A client-side or unexpected API error occurred."

    def _yield_error_stream(self, error_message: str):
        """Helper to yield an error in SSE format for stream=True cases"""
        logger.debug(f"Yielding error stream: {error_message}")
        yield f"data: {json.dumps({'error': error_message})}\n\n"
        # yield f"data: [DONE]\n\n" # Optionally send a DONE marker after error
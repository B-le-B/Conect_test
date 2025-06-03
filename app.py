# app.py
import os
import logging
from flask import Flask, render_template, request, jsonify, send_from_directory, Response
from werkzeug.utils import secure_filename
import uuid
import threading
import time
import webbrowser
import json
import requests
import shutil # For moving files


import os
from pathlib import Path
from dotenv import load_dotenv

# 确保从正确的路径加载 .env
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

# 立即验证
print(f"Working directory: {os.getcwd()}")
print(f".env file exists: {env_path.exists()}")
print(f"OPENROUTER_API_KEY loaded: {os.getenv('OPENROUTER_API_KEY') is not None}")

# 在报错的地方之前添加
print(f"Looking for platform: Openrouter")
print(f"Environment variable OPENROUTER_API_KEY: {os.getenv('OPENROUTER_API_KEY')}")



# ==============================================================================
# Load .env file variables into environment at the very beginning
from dotenv import load_dotenv
load_dotenv() # Call only ONCE at the top
# Your DEBUG prints for initial .env load check (KEEP THESE for now):
print(f"DEBUG_ENV_LOAD [app.py top]: MODELSCOPE_API_KEY after load_dotenv: {os.getenv('MODELSCOPE_API_KEY')}")
print(f"DEBUG_ENV_LOAD [app.py top]: SILICONFLOW_API_KEY after load_dotenv: {os.getenv('SILICONFLOW_API_KEY')}")
print(f"DEBUG_ENV_LOAD [app.py top]: OPENROUTER_API_KEY after load_dotenv: {os.getenv('OPENROUTER_API_KEY')}")
# ==============================================================================

# Import our existing translators and file processing logic
from translator import SiliconFlowTranslator
from file_translator import translate_text_file
from docx_translator import translate_docx_file
try:
    from docx_full_translator import translate_docx_file_formatted
    logging.info("Successfully imported translate_docx_file_formatted from docx_full_translator.")
except ImportError:
    logging.warning("docx_full_translator.py or translate_docx_file_formatted function not found. Formatted DOCX translation will not be available.")
    def translate_docx_file_formatted(*args, **kwargs): # Fallback dummy function
        return "Error: Formatted DOCX translator module or function is not configured."

# Import fallback configurations from config.py (ensure config.py is generic now)
try:
    from config import API_KEY as DEFAULT_FALLBACK_API_KEY, \
                       BASE_URL as DEFAULT_FALLBACK_BASE_URL, \
                       DEFAULT_MODEL as DEFAULT_FALLBACK_MODEL
except ImportError:
    logging.warning("config.py not found or missing default fallback constants. Global fallbacks will be None.")
    DEFAULT_FALLBACK_API_KEY = None
    DEFAULT_FALLBACK_BASE_URL = None
    DEFAULT_FALLBACK_MODEL = None

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configure upload and translated folders
UPLOAD_FOLDER = 'uploads'
TRANSLATED_FOLDER = 'translated_output_web'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['TRANSLATED_FOLDER'] = TRANSLATED_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50 MB

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(TRANSLATED_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {'txt', 'docx'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/translate_api', methods=['POST'])
def translate_api():
    data = request.form
    api_platform = data.get('api_platform', 'custom')

    logger.info(f"Received translation request for platform: {api_platform}")

    # Get settings from frontend form first
    frontend_api_key = data.get('api_key', '').strip()
    frontend_base_url = data.get('base_url', '').strip()
    frontend_model = data.get('model', '').strip()
    
    logger.info(f"Frontend inputs - API Key: {'SET (length ' + str(len(frontend_api_key)) + ')' if frontend_api_key else 'Not provided'}, Base URL: '{frontend_base_url}', Model: '{frontend_model}'")

    target_lang = data.get('target_lang')
    source_lang = data.get('source_lang')

    if not target_lang:
        logger.error("Target language is required.")
        return jsonify({"error": "Target language is required."}), 400

    # ==============================================================================
    # >>>>>>>>>> START OF REVISED CONFIGURATION LOADING LOGIC <<<<<<<<<<
    # --- Platform-specific configuration loading ---
    platform_configs = {
        "siliconflow": {
            "api_key_env": "SILICONFLOW_API_KEY",
            "base_url_env": "SILICONFLOW_BASE_URL",
            "model_env": "SILICONFLOW_MODEL",
            "default_base_url": "https://api.siliconflow.cn/v1",
            "default_model": "THUDM/GLM-4-9B-0414" 
        },
        "deepseek": {
            "api_key_env": "DEEPSEEK_API_KEY",
            "base_url_env": "DEEPSEEK_BASE_URL",
            "model_env": "DEEPSEEK_MODEL",
            "default_base_url": "https://api.deepseek.com/v1",
            "default_model": "deepseek-chat"
        },
        "moonshot": {
            "api_key_env": "MOONSHOT_API_KEY",
            "base_url_env": "MOONSHOT_BASE_URL",
            "model_env": "MOONSHOT_MODEL",
            "default_base_url": "https://api.moonshot.cn/v1",
            "default_model": "moonshot-v1-8k"
        },
        "openai": {
            "api_key_env": "OPENAI_API_KEY",
            "base_url_env": "OPENAI_BASE_URL",
            "model_env": "OPENAI_MODEL",
            "default_base_url": "https://api.openai.com/v1",
            "default_model": "gpt-3.5-turbo"
        },
        "ollama": {
            "api_key_env": "OLLAMA_API_KEY", 
            "base_url_env": "OLLAMA_BASE_URL",
            "model_env": "OLLAMA_MODEL",
            "default_base_url": "http://localhost:11434/v1",
            "default_model": "llama3"
        },
        "modelscope": { 
            "api_key_env": "MODELSCOPE_API_KEY",
            "base_url_env": "MODELSCOPE_BASE_URL",
            "model_env": "MODELSCOPE_MODEL",
            "default_base_url": "https://api-inference.modelscope.cn/v1",
            "default_model": "Qwen/Qwen2.5-72B-Instruct"
        },
        "openrouter": { 
            "api_key_env": "OPENROUTER_API_KEY",
            "base_url_env": "OPENROUTER_BASE_URL",
            "model_env": "OPENROUTER_MODEL",
            "default_base_url": "https://openrouter.ai/api/v1",
            "default_model": "google/gemini-2.0-flash-exp:free"
        }
    }

    api_key_to_use = frontend_api_key
    base_url_to_use = frontend_base_url
    model_to_use = frontend_model

    selected_platform_config = platform_configs.get(api_platform)

    if selected_platform_config:
        logger.info(f"Processing config for known platform: {api_platform}")
        # Try to get API Key from .env if not provided by frontend
        if not api_key_to_use and selected_platform_config.get("api_key_env"):
            env_var_name = selected_platform_config["api_key_env"]
            key_from_env = os.getenv(env_var_name)
            logger.info(f"Attempting to load API Key from env var '{env_var_name}': {'Found' if key_from_env else 'Not Found'}")
            if key_from_env:
                api_key_to_use = key_from_env
        
        # Try to get Base URL from .env if not provided by frontend
        if not base_url_to_use and selected_platform_config.get("base_url_env"):
            env_var_name = selected_platform_config["base_url_env"]
            url_from_env = os.getenv(env_var_name)
            logger.info(f"Attempting to load Base URL from env var '{env_var_name}': {'Found' if url_from_env else 'Not Found'}")
            if url_from_env:
                base_url_to_use = url_from_env
        
        # Try to get Model from .env if not provided by frontend
        if not model_to_use and selected_platform_config.get("model_env"):
            env_var_name = selected_platform_config["model_env"]
            model_from_env = os.getenv(env_var_name)
            logger.info(f"Attempting to load Model from env var '{env_var_name}': {'Found' if model_from_env else 'Not Found'}")
            if model_from_env:
                model_to_use = model_from_env

        # Fallback to platform hardcoded defaults if still not set
        if not base_url_to_use:
            base_url_to_use = selected_platform_config.get("default_base_url")
            if base_url_to_use: logger.info(f"Using platform default Base URL for '{api_platform}': {base_url_to_use}")
        if not model_to_use:
            model_to_use = selected_platform_config.get("default_model")
            if model_to_use: logger.info(f"Using platform default Model for '{api_platform}': {model_to_use}")
    else:
        logger.info(f"Platform '{api_platform}' is 'custom' or not in predefined configs. Relying on frontend inputs or global fallbacks.")
    
    # Final fallback to global defaults from config.py (which should be generic or None)
    if not api_key_to_use:
        api_key_to_use = DEFAULT_FALLBACK_API_KEY # This is from config.py
        if api_key_to_use: logger.info(f"Using global fallback API Key (from config.py) for '{api_platform}'.")
    if not base_url_to_use:
        base_url_to_use = DEFAULT_FALLBACK_BASE_URL # This is from config.py
        if base_url_to_use: logger.info(f"Using global fallback Base URL (from config.py) for '{api_platform}'.")
    if not model_to_use:
        model_to_use = DEFAULT_FALLBACK_MODEL # This is from config.py
        if model_to_use: logger.info(f"Using global fallback Model (from config.py) for '{api_platform}'.")
    
    logger.info(f"Final config for API call - Platform: '{api_platform}', API Key: {'SET (ends ...' + api_key_to_use[-4:] + ')' if api_key_to_use and len(api_key_to_use) > 4 else ('PROVIDED (short/empty)' if api_key_to_use else 'NOT SET (CRITICAL!)')}, Base URL: {base_url_to_use}, Model: {model_to_use}")

    # Validate final configurations
    if not api_key_to_use: # This check is now more critical
        err_msg = f"API Key for platform '{api_platform}' is ultimately missing. Please configure it via UI or .env file."
        logger.error(err_msg)
        return jsonify({"error": err_msg}), 400
    # Similar checks for base_url_to_use and model_to_use
    if not base_url_to_use:
        err_msg = f"Base URL for platform '{api_platform}' is ultimately missing. Please configure it."
        logger.error(err_msg)
        return jsonify({"error": err_msg}), 400
    if not model_to_use:
        err_msg = f"Model for platform '{api_platform}' is ultimately missing. Please configure it."
        logger.error(err_msg)
        return jsonify({"error": err_msg}), 400
    # >>>>>>>>>> END OF REVISED CONFIGURATION LOADING LOGIC <<<<<<<<<<
    # ==============================================================================
    
    try:
        translator_instance = SiliconFlowTranslator(
    api_key=api_key_to_use,
    base_url=base_url_to_use,
    model=model_to_use,
    platform_id=api_platform # <--- 新增传递 platform_id
)
    except ValueError as e:
        logger.error(f"Translator initialization error with resolved config: {e}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Unexpected error initializing translator: {type(e).__name__} - {e}")
        return jsonify({"error": f"Server error during translator setup: {str(e)}"}), 500

    # --- Text Input Translation ---
    if 'text_input' in data and data['text_input']:
        text_to_translate = data['text_input']
        if not text_to_translate.strip():
             logger.error("Text to translate cannot be empty.")
             return jsonify({"error": "Text to translate cannot be empty."}), 400

        logger.info(f"Processing text translation: '{text_to_translate[:50]}...' to {target_lang} via {api_platform}")

        def generate_translation_stream():
            response_stream = None
            try:
                response_stream = translator_instance.translate(text_to_translate, target_lang, source_lang, stream=True)
                if not isinstance(response_stream, requests.Response):
                    error_msg = f"Translation API for {api_platform} did not return a valid stream. Type: {type(response_stream)}. Content: {str(response_stream)[:200]}"
                    logger.error(error_msg)
                    yield f"data: {json.dumps({'error': error_msg})}\n\n"
                    return

                for chunk in response_stream.iter_lines(): 
                    if chunk:
                        chunk_str = chunk.decode('utf-8')
                        if chunk_str.startswith("data: "):
                            json_part_str = chunk_str[len("data: "):].strip()
                        elif chunk_str.strip().startswith("{") and chunk_str.strip().endswith("}"): 
                             json_part_str = chunk_str.strip()
                             logger.debug(f"Received non-standard JSON line, processing as data: {json_part_str}")
                        else:
                            logger.debug(f"Skipping non-data line from stream: {chunk_str}")
                            continue
                        if json_part_str == "[DONE]":
                            logger.info("Stream finished with [DONE] marker from API.")
                            yield f"data: {json.dumps({'done': True})}\n\n"
                            break
                        try:
                            json_part = json.loads(json_part_str)
                            if json_part.get("choices") and isinstance(json_part["choices"], list) and len(json_part["choices"]) > 0 and \
                               json_part["choices"][0].get("delta") and "content" in json_part["choices"][0]["delta"]:
                                content = json_part["choices"][0]["delta"]["content"]
                                if content is not None: 
                                    yield f"data: {json.dumps({'text_chunk': content})}\n\n"
                            elif json_part.get("error"): 
                                error_detail = json_part["error"].get("message", str(json_part["error"])) if isinstance(json_part["error"], dict) else str(json_part["error"])
                                logger.error(f"Error in stream from API ({api_platform}): {error_detail}")
                                yield f"data: {json.dumps({'error': error_detail})}\n\n"
                                break 
                            elif json_part.get("done") is True :
                                logger.info(f"Stream finished with 'done: true' marker from API ({api_platform}).")
                                yield f"data: {json.dumps({'done': True})}\n\n"
                                break
                        except json.JSONDecodeError:
                            logger.warning(f"Could not decode JSON from stream chunk ({api_platform}): {json_part_str}")
                            continue 
            except requests.exceptions.RequestException as e:
                logger.error(f"RequestException during streaming to {api_platform} API: {e}")
                yield f"data: {json.dumps({'error': f'API request error: {e}'})}\n\n"
            except Exception as e:
                import traceback
                logger.error(f"Unexpected error in generate_translation_stream ({api_platform}): {e}\n{traceback.format_exc()}")
                yield f"data: {json.dumps({'error': f'Server error during streaming: {str(e)}'})}\n\n"
            finally:
                if response_stream and hasattr(response_stream, 'close'):
                    response_stream.close()
                logger.info(f"Translation stream generation ended for {api_platform}.")
        return Response(generate_translation_stream(), mimetype='text/event-stream')

    # --- File Input Translation ---
    # ... (保持你原有的文件翻译逻辑不变，它会使用上面已确定的 translator_instance) ...
    elif 'file' in request.files:
        file = request.files['file']
        if not file or file.filename == '': 
            logger.error("No file selected or file object missing.")
            return jsonify({"error": "No file selected."}), 400

        if not allowed_file(file.filename):
            logger.error(f"File type not allowed: {file.filename}")
            return jsonify({"error": "File type not allowed. Please upload .txt or .docx."}), 400

        original_filename = secure_filename(file.filename)
        file_extension = original_filename.rsplit('.', 1)[1].lower()
        unique_filename_base = str(uuid.uuid4())
        input_unique_filename = unique_filename_base + '.' + file_extension
        input_filepath = os.path.join(app.config['UPLOAD_FOLDER'], input_unique_filename)
        
        try:
            file.save(input_filepath)
            logger.info(f"File uploaded: {original_filename} to {input_filepath}")
        except Exception as e:
            logger.error(f"Failed to save uploaded file {original_filename}: {e}")
            return jsonify({"error": f"Failed to save uploaded file: {str(e)}"}), 500


        user_output_folder = data.get('output_folder_path', '').strip()
        actual_output_dir = app.config['TRANSLATED_FOLDER'] 
        if user_output_folder:
            abs_user_output_folder = os.path.abspath(user_output_folder)
            try:
                os.makedirs(abs_user_output_folder, exist_ok=True)
                if os.path.isdir(abs_user_output_folder): 
                    actual_output_dir = abs_user_output_folder
                else: 
                    logger.warning(f"User output folder '{user_output_folder}' is not a valid directory, using default.")
            except Exception as e:
                logger.warning(f"Could not use/create user output folder '{user_output_folder}': {e}. Using default.")
        
        logger.info(f"Translations will be saved to: {actual_output_dir}")

        translated_filepath_or_error = None 
        translation_format = data.get('translation_format', 'unformatted')
        
        logger.info(f"Processing file '{original_filename}', format: {translation_format if file_extension == 'docx' else 'N/A'}")

        if file_extension == 'txt':
            encoding = data.get('encoding', 'utf-8')
            logger.info(f"Translating TXT file with encoding '{encoding}'.")
            translated_filepath_or_error = translate_text_file(
                input_filepath, actual_output_dir, target_lang, translator_instance, 
                source_lang, encoding, unique_filename_base
            )
        elif file_extension == 'docx':
            if translation_format == 'formatted':
                logger.info(f"Attempting formatted DOCX translation.")
                translated_filepath_or_error = translate_docx_file_formatted(
                    input_filepath, actual_output_dir, target_lang, translator_instance, 
                    source_lang, unique_filename_base
                )
            else: 
                logger.info(f"Attempting unformatted DOCX translation.")
                translated_filepath_or_error = translate_docx_file(
                    input_filepath, actual_output_dir, target_lang, translator_instance, 
                    source_lang, unique_filename_base
                )
        
        try:
            if os.path.exists(input_filepath):
                os.remove(input_filepath)
                logger.info(f"Temporary uploaded file removed: {input_filepath}")
        except Exception as e:
            logger.warning(f"Failed to remove temporary uploaded file {input_filepath}: {e}")

        if isinstance(translated_filepath_or_error, str) and not translated_filepath_or_error.startswith("Error:"):
            if not os.path.exists(translated_filepath_or_error):
                 logger.error(f"Translated file path reported ('{translated_filepath_or_error}') but file not found on server.")
                 return jsonify({"error": "Translated file not found on server after processing."}), 500

            output_filename = os.path.basename(translated_filepath_or_error)
            final_downloadable_path_in_translated_folder = os.path.join(app.config['TRANSLATED_FOLDER'], output_filename)

            if os.path.abspath(translated_filepath_or_error) != os.path.abspath(final_downloadable_path_in_translated_folder):
                try:
                    shutil.move(translated_filepath_or_error, final_downloadable_path_in_translated_folder)
                    logger.info(f"Moved translated file from '{translated_filepath_or_error}' to download folder '{final_downloadable_path_in_translated_folder}'")
                except Exception as e:
                    logger.error(f"Failed to move translated file to download folder: {e}")
                    if os.path.exists(translated_filepath_or_error):
                         logger.warning(f"Serving from original translated path '{translated_filepath_or_error}' as move failed.")
                         return jsonify({"error": f"File translated but failed to stage for download: {e}"}), 500
                    else:
                         return jsonify({"error": f"File translated, move failed, and original also missing: {e}"}), 500
            
            output_file_url = f"/download/{output_filename}" 
            logger.info(f"File translation successful. URL: {output_file_url}, Path in download folder: {final_downloadable_path_in_translated_folder}")
            return jsonify({"translated_file_url": output_file_url})
        else: 
            error_message = str(translated_filepath_or_error) if translated_filepath_or_error else "Unknown error during file translation."
            logger.error(f"File translation failed: {error_message}")
            return jsonify({"error": error_message}), 500
    else:
        logger.error("No valid text or file input provided to /translate_api.")
        return jsonify({"error": "No valid text or file input provided."}), 400

@app.route('/download/<filename>')
def download_file(filename):
    if '..' in filename or filename.startswith('/'): 
        logger.warning(f"Attempted directory traversal in download: {filename}")
        return jsonify({"error": "Invalid filename for download."}), 400
    
    try:
        logger.info(f"Attempting to send file for download: {filename} from {app.config['TRANSLATED_FOLDER']}")
        return send_from_directory(app.config['TRANSLATED_FOLDER'], filename, as_attachment=True)
    except FileNotFoundError:
        logger.error(f"File not found for download in TRANSLATED_FOLDER: {filename}")
        return jsonify({"error": "File not found for download."}), 404
    except Exception as e:
        logger.error(f"Error during file download ({filename}): {e}")
        return jsonify({"error": "Could not download file due to server error."}), 500

if __name__ == '__main__':
    server_url = "http://127.0.0.1:5000"
    if not os.environ.get("WERKZEUG_RUN_MAIN"): 
        def open_browser_once():
            time.sleep(1) 
            webbrowser.open_new_tab(server_url)
        
        browser_thread = threading.Thread(target=open_browser_once)
        browser_thread.daemon = True
        browser_thread.start()
        logger.info(f"Flask app starting, browser will open at {server_url}")
    
    logger.info("Press CTRL+C in this console to stop the server.")
    app.run(debug=True, host='0.0.0.0', port=5000)
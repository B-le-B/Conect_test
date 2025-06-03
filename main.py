# main.py
import argparse
import logging
import os
from translator import SiliconFlowTranslator
from file_translator import translate_text_file
from docx_translator import translate_docx_file # <--- 确保此行存在
from config import API_KEY, DEFAULT_MODEL, BASE_URL

# 配置日志记录器
logging.basicConfig(
    level=logging.INFO, # 设置默认日志级别为 INFO。可以改为 DEBUG 看到更多细节。
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    # 可以选择输出到文件而不是控制台
    # filename='translator.log',
    # filemode='a' # 追加模式
)
logger = logging.getLogger(__name__) # 获取当前模块的日志器

# 命令行帮助信息的示例部分
CLI_EXAMPLES = """
Usage Examples:
  Translate text:
    python main.py -t "你好，世界！" -l "English"

  Translate text with explicit source language:
    python main.py -t "How are you?" -l "简体中文" -s "English"

  Translate a plain text file (e.g., input.txt to output_dir/input_translated_english.txt):
    python main.py -i input.txt -o output_dir -l "English"

  Translate a Word document (.docx) (e.g., document.docx to translated_docx/document_translated_english.docx):
    python main.py -id document.docx -od translated_docx -l "English" -s "简体中文"

  Override default model and base URL for any translation type:
    python main.py -t "Test" -l "French" -m "gemma-7b-it" -u "https://api.another-platform.com/v1"

  Provide API Key via command-line (USE WITH CAUTION!):
    python main.py -t "Hello" -l "Spanish" -k "sk-YOUR_KEY_HERE"
"""

def main():
    # 创建 ArgumentParser 对象，用于解析命令行参数
    parser = argparse.ArgumentParser(
        description="A simple command-line text translator using SiliconFlow-like API.",
        formatter_class=argparse.RawTextHelpFormatter, # 保持 epilog 的格式
        epilog=CLI_EXAMPLES # 使用我们定义的常量
    )

    # 添加命令行参数
    # -t / --text: 必需，待翻译的文本
    parser.add_argument(
        "-t", "--text",
        help="The text to be translated. Cannot be used with -i/--input_file or -id/--input_docx."
    )
    # -l / --target_lang: 必需，目标语言
    parser.add_argument(
        "-l", "--target_lang",
        required=True, # 无论是文本还是文件翻译，目标语言都是必需的
        help="The target language (e.g., 'English', 'French', '简体中文')."
    )
    # -s / --source_lang: 可选，源语言
    parser.add_argument(
        "-s", "--source_lang",
        help="The source language (optional, e.g., '简体中文', 'English'). If not provided, the model will attempt to auto-detect."
    )
    # -i / --input_file: 用于纯文本文件翻译
    parser.add_argument(
        "-i", "--input_file",
        help="Path to the input plain text file (.txt) to be translated. Cannot be used with -t/--text or -id/--input_docx."
    )
    # -o / --output_dir: 用于纯文本文件翻译
    parser.add_argument(
        "-o", "--output_dir",
        help="Directory where the translated plain text file will be saved. Required if -i/--input_file is used."
    )
    # --encoding: 用于纯文本文件翻译
    parser.add_argument(
        "--encoding",
        default="utf-8",
        help="Encoding of the input and output plain text files (default: utf-8). Common alternatives: gbk, latin-1."
    )
    # -id / --input_docx: 用于 Word 文档翻译
    parser.add_argument(
        "-id", "--input_docx",
        help="Path to the input Word document (.docx) to be translated. Cannot be used with -t/--text or -i/--input_file."
    )
    # -od / --output_docx_dir: 用于 Word 文档翻译
    parser.add_argument(
        "-od", "--output_docx_dir",
        help="Directory where the translated Word document will be saved. Required if -id/--input_docx is used."
    )
    # -m / --model: 可选，覆盖默认模型
    parser.add_argument(
        "-m", "--model",
        help=f"The model to use for translation (overrides default '{DEFAULT_MODEL}' loaded from .env/config)."
    )
    # -u / --base_url: 可选，覆盖默认 API Base URL
    parser.add_argument(
        "-u", "--base_url",
        help=f"The base URL for the API (overrides default '{BASE_URL}' loaded from .env/config)."
    )
    # -k / --api_key: 可选，覆盖默认 API Key
    parser.add_argument(
        "-k", "--api_key",
        help="Your SiliconFlow API Key (overrides environment variable SILICONFLOW_API_KEY). "
             "USE WITH CAUTION: Typing key on CLI might expose it in shell history or process listings. "
             "Prefer using .env file."
    )

    # 解析命令行参数
    args = parser.parse_args()

    # --- 参数逻辑检查 ---
    # 1. 确保只有一种输入类型被提供：文本(-t), 纯文本文件(-i), Word文档(-id)
    input_modes = [args.text, args.input_file, args.input_docx]
    active_input_modes = [mode for mode in input_modes if mode is not None]

    if len(active_input_modes) > 1:
        parser.error("Only one input type (-t/--text, -i/--input_file, or -id/--input_docx) can be provided at a time. Please choose one.")
    if len(active_input_modes) == 0:
        parser.error("At least one input type (-t/--text, -i/--input_file, or -id/--input_docx) must be provided.")
    
    # 2. 如果使用了 -i (纯文本文件)，则 -o (输出目录) 必需
    if args.input_file and not args.output_dir:
        parser.error("Argument -o/--output_dir is required when -i/--input_file is used.")

    # 3. 如果使用了 -id (Word文档)，则 -od (Word输出目录) 必需
    if args.input_docx and not args.output_docx_dir:
        parser.error("Argument -od/--output_docx_dir is required when -id/--input_docx is used.")

    try:
        logger.info("Translator application started.")
        # 根据命令行参数或 config.py 中的默认值初始化翻译器
        translator = SiliconFlowTranslator(
            api_key=args.api_key,
            base_url=args.base_url,
            model=args.model
        )

        if args.input_docx:
            # 执行 Word 文档翻译
            logger.info(f"Starting Word document translation for: {args.input_docx}")
            # 预检查输入文件是否存在
            if not os.path.exists(args.input_docx):
                print(f"\nError: Input Word document not found at '{args.input_docx}'")
                logger.error(f"Input Word document not found: {args.input_docx}")
                return # 提前退出
            
            output_filepath_or_error = translate_docx_file(
                input_filepath=args.input_docx,
                output_dir=args.output_docx_dir,
                target_lang=args.target_lang,
                translator=translator,
                source_lang=args.source_lang,
                # chunk_size可以在这里覆盖，但目前我们使用 docx_translator.py 内部的 DEFAULT_DOCX_CHUNK_SIZE
            )
            if output_filepath_or_error and output_filepath_or_error.startswith("Error:"):
                print(f"\n--- Word Document Translation Failed ---")
                print(output_filepath_or_error)
                print("----------------------------------------")
                # 错误日志已在 docx_translator 中记录
            else:
                print(f"\n--- Word Document Translation Complete ---")
                print(f"Translated document saved to: {output_filepath_or_error}")
                print("------------------------------------------")
                # 成功日志已在 docx_translator 中记录

        elif args.input_file:
            # 执行纯文本文件翻译
            logger.info(f"Starting plain text file translation for: {args.input_file}")
            if not os.path.exists(args.input_file):
                print(f"\nError: Input file not found at '{args.input_file}'")
                logger.error(f"Input file not found: {args.input_file}")
                return
            
            output_filepath_or_error = translate_text_file(
                input_filepath=args.input_file,
                output_dir=args.output_dir,
                target_lang=args.target_lang,
                translator=translator,
                source_lang=args.source_lang,
                encoding=args.encoding
            )
            if output_filepath_or_error and output_filepath_or_error.startswith("Error:"):
                print(f"\n--- Plain Text File Translation Failed ---")
                print(output_filepath_or_error)
                print("------------------------------------------")
            else:
                print(f"\n--- Plain Text File Translation Complete ---")
                print(f"Translated file saved to: {output_filepath_or_error}")
                print("------------------------------------------")

        elif args.text:
            # 执行单文本翻译
            logger.info(f"Starting text translation for: '{args.text[:50]}...'")
            translated_text = translator.translate(args.text, args.target_lang, args.source_lang)
            print("\n--- Text Translation Result ---")
            print(translated_text)
            print("--------------------------")
            if translated_text.startswith("Error:"):
                # 错误日志已在 translator 中记录
                pass
            else:
                logger.info("Text translation successful.")
        
    except ValueError as ve:
        logger.error(f"Configuration Error: {ve}")
        print(f"\nConfiguration Error: {ve}")
        print("Please ensure SILICONFLOW_API_KEY and SILICONFLOW_MODEL are set in your .env file, or provided via command-line arguments.")
    except Exception as e:
        logger.exception(f"An unexpected error occurred during execution: {e}")
        print(f"\nAn unexpected error occurred: {e}")

if __name__ == "__main__":
    main()
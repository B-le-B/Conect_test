document.addEventListener('DOMContentLoaded', function() {
    // --- 元素获取 ---
    const sourceLangSelect = document.getElementById('source_lang');
    const targetLangSelect = document.getElementById('target_lang');
    const swapLangButton = document.getElementById('swap_lang_button');

    const modeTextButton = document.getElementById('mode_text_button');
    const modeFileButton = document.getElementById('mode_file_button');
    const textInputSection = document.getElementById('text_input_section');
    const fileInputSection = document.getElementById('file_input_section');

    const textInput = document.getElementById('text_input');
    const fileInput = document.getElementById('file_input');
    const fileNameDisplay = document.getElementById('file_name_display');
    const encodingGroup = document.getElementById('encoding_group');
    const translationFormatGroup = document.getElementById('translation_format_group');
    const outputFolderPathGroup = document.querySelector('.file-output-path');
    const outputFolderPathInput = document.getElementById('output_folder_path'); 
    const copyDefaultPathButton = document.getElementById('copy_default_path_button'); 

    const translateButton = document.getElementById('translate_button');
    const statusMessage = document.getElementById('status_message');
    const translatedTextDisplay = document.getElementById('translated_text_display');
    const downloadArea = document.getElementById('download_area');
    const downloadLink = document.getElementById('download_link');
    const logOutputPre = document.getElementById('log_output');

    const apiPlatformSelect = document.getElementById('api_platform');
    const apiKeyInput = document.getElementById('api_key');
    const baseUrlInput = document.getElementById('base_url');
    const modelInput = document.getElementById('model');
    const apiKeyHint = document.querySelector('#api_key + .hint');
    const copyTranslatedTextButton = document.getElementById('copy_translated_text_button');

    // ==================================================
    // >>>>>>>>>> START OF ADDED ELEMENT GETTERS FOR SOURCE TEXT <<<<<<<<<<
    const copySourceTextButton = document.getElementById('copy_source_text_button');
    const clearSourceTextButton = document.getElementById('clear_source_text_button');
    // <<<<<<<<<< END OF ADDED ELEMENT GETTERS FOR SOURCE TEXT <<<<<<<<<<
    // ==================================================


    // --- 语言列表 ---
    const LANGUAGES = [
        {value: "", text: "自动检测"},
        {value: "简体中文", text: "简体中文"},
        {value: "繁體中文", text: "繁體中文"},
        {value: "English", text: "English"},
        {value: "日本語", text: "日本語 (Japanese)"},
        {value: "Français", text: "Français (French)"},
        {value: "Deutsch", text: "Deutsch (German)"},
        {value: "Español", text: "Español (Spanish)"},
        {value: "Português", text: "Português (Portuguese)"}, 
        {value: "Русский", text: "Русский (Russian)"},
        {value: "العربية", text: "العربية (Arabic)"},
    ];

    // --- API 平台配置 ---
    const API_PLATFORM_CONFIGS = {
        "siliconflow": {
            baseUrl: "https://api.siliconflow.cn/v1",
            model: "THUDM/GLM-4-9B-0414",
            apiKeyEnvHint: "SILICONFLOW_API_KEY"
        },
        "Modelscope": {
            baseUrl: "https://api-inference.modelscope.cn/v1",
            model: "Qwen/Qwen2.5-72B-Instruct",
            apiKeyEnvHint: "MODELSCOPE_API_KEY"
        },
        "Openrouter": {
            baseUrl: "https://openrouter.ai/api/v1",
            model: "google/gemini-2.0-flash-exp:free",
            apiKeyEnvHint: "OPENROUTER_API_KEY"
        },
        "openai": {
            baseUrl: "https://api.openai.com/v1",
            model: "gpt-3.5-turbo",
            apiKeyEnvHint: "OPENAI_API_KEY"
        },
        "ollama": {
            baseUrl: "http://localhost:11434/v1", 
            model: "llama3", 
            apiKeyEnvHint: "OLLAMA_API_KEY (通常不需要或任意字符串)"
        },
        "custom": {
            baseUrl: "",
            model: "",
            apiKeyEnvHint: "自定义平台的环境变量"
        }
    };
    
    function updateApiFieldsForPlatform(platform) {
        const config = API_PLATFORM_CONFIGS[platform] || API_PLATFORM_CONFIGS["custom"];
        if (baseUrlInput) baseUrlInput.value = config.baseUrl;
        if (modelInput) modelInput.value = config.model;
        if (apiKeyHint) {
            apiKeyHint.textContent = `留空将使用 .env 环境变量 (例如 ${config.apiKeyEnvHint})。`;
        }
        if (apiPlatformSelect) {
            appendLog(`API 平台切换为: ${apiPlatformSelect.options[apiPlatformSelect.selectedIndex].text}. Base URL 和 Model 已更新。`);
        }
    }


    // --- 辅助函数 ---
    function populateLanguageSelect(selectElement, languages, includeAutoDetect = false) {
        if (!selectElement) return;
        selectElement.innerHTML = ''; 
        const filteredLanguages = includeAutoDetect ? languages : languages.filter(lang => lang.value !== "");
        
        filteredLanguages.forEach(lang => {
            let option = document.createElement('option');
            option.value = lang.value;
            option.textContent = lang.text;
            selectElement.appendChild(option);
        });
    }

    function appendLog(message) {
        if (!logOutputPre) return;
        const now = new Date();
        const timestamp = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
        logOutputPre.textContent += `[${timestamp}] ${message}\n`;
        logOutputPre.scrollTop = logOutputPre.scrollHeight; 
    }

    function resetOutputArea() {
        if (translatedTextDisplay) translatedTextDisplay.value = '';
        if (downloadArea) downloadArea.style.display = 'none';
        if (downloadLink) {
            downloadLink.href = '#';
            downloadLink.textContent = '';
            downloadLink.style.display = 'none';
        }
        if (statusMessage) {
            statusMessage.textContent = '';
            statusMessage.className = 'status-message';
        }
    }

    function switchToTextMode() {
        if (modeTextButton) modeTextButton.classList.add('active');
        if (modeFileButton) modeFileButton.classList.remove('active');
        if (textInputSection) textInputSection.classList.add('active');
        if (fileInputSection) fileInputSection.classList.remove('active');
        
        if (outputFolderPathGroup) outputFolderPathGroup.style.display = 'none';
        if (encodingGroup) encodingGroup.style.display = 'none';
        if (translationFormatGroup) translationFormatGroup.style.display = 'none';
        appendLog("切换到文字翻译模式。");
    }

    function switchToFileMode() {
        if (modeFileButton) modeFileButton.classList.add('active');
        if (modeTextButton) modeTextButton.classList.remove('active');
        if (textInputSection) textInputSection.classList.remove('active');
        if (fileInputSection) fileInputSection.classList.add('active');
        
        if (outputFolderPathGroup) outputFolderPathGroup.style.display = 'block';
        updateFileSpecificOptions();
        appendLog("切换到文档翻译模式。");
    }

    function updateFileSpecificOptions() {
        const currentFile = fileInput && fileInput.files[0];
        if (currentFile && modeFileButton && modeFileButton.classList.contains('active')) {
            const fileExtension = currentFile.name.split('.').pop().toLowerCase();
            if (fileExtension === 'txt') {
                if (encodingGroup) encodingGroup.style.display = 'block';
                if (translationFormatGroup) translationFormatGroup.style.display = 'none';
                appendLog(`已选择 .txt 文档: ${currentFile.name}，显示编码选项。`);
            } else if (fileExtension === 'docx') {
                if (encodingGroup) encodingGroup.style.display = 'none';
                if (translationFormatGroup) translationFormatGroup.style.display = 'block';
                appendLog(`已选择 .docx 文档: ${currentFile.name}，显示翻译格式选项。`);
            } else {
                if (encodingGroup) encodingGroup.style.display = 'none';
                if (translationFormatGroup) translationFormatGroup.style.display = 'none';
                appendLog(`已选择 .${fileExtension} 文档: ${currentFile.name}，隐藏特定文件选项。`);
            }
        } else {
            if (encodingGroup) encodingGroup.style.display = 'none';
            if (translationFormatGroup) translationFormatGroup.style.display = 'none';
        }
    }


    // --- 初始状态设置 ---
    populateLanguageSelect(sourceLangSelect, LANGUAGES, true); 
    populateLanguageSelect(targetLangSelect, LANGUAGES, false); 

    if (sourceLangSelect) sourceLangSelect.value = ''; 
    if (targetLangSelect) targetLangSelect.value = '简体中文'; 

    if (apiPlatformSelect) updateApiFieldsForPlatform(apiPlatformSelect.value);
    switchToTextMode(); 

    // --- 事件监听器 ---
    if (apiPlatformSelect) {
        apiPlatformSelect.addEventListener('change', function() {
            updateApiFieldsForPlatform(this.value);
        });
    }

    if (swapLangButton) {
        swapLangButton.addEventListener('click', function() {
            if (!sourceLangSelect || !targetLangSelect) return;
            let sourceValue = sourceLangSelect.value;
            let targetValue = targetLangSelect.value;
            if (sourceValue === "") { 
                sourceLangSelect.value = targetValue; 
                let newTargetValue = "English"; 
                if (LANGUAGES.some(lang => lang.value === sourceValue && sourceValue !== "")) { 
                    newTargetValue = sourceValue;
                } else if (LANGUAGES.filter(lang => lang.value !== "" && lang.value !== targetValue).length > 0) { 
                     newTargetValue = LANGUAGES.filter(lang => lang.value !== "" && lang.value !== targetValue)[0].value;
                }
                targetLangSelect.value = newTargetValue;
            } else {
                sourceLangSelect.value = targetValue;
                targetLangSelect.value = sourceValue;
            }
            appendLog(`语言互换：源语言变为 ${sourceLangSelect.options[sourceLangSelect.selectedIndex].textContent}，目标语言变为 ${targetLangSelect.options[targetLangSelect.selectedIndex].textContent}`);
        });
    }

    if (modeTextButton) {
        modeTextButton.addEventListener('click', function() {
            switchToTextMode();
            resetOutputArea(); 
        });
    }

    if (modeFileButton) {
        modeFileButton.addEventListener('click', function() {
            switchToFileMode();
            resetOutputArea(); 
        });
    }

    if (fileInput) {
        fileInput.addEventListener('change', function() {
            const file = this.files[0];
            if (file) {
                if (fileNameDisplay) fileNameDisplay.textContent = file.name;
                if (textInput) textInput.value = ''; 
                switchToFileMode(); 
                resetOutputArea();
                updateFileSpecificOptions(); 
            } else {
                if (fileNameDisplay) fileNameDisplay.textContent = '未选择任何文档';
                updateFileSpecificOptions(); 
                appendLog("未选择文档。");
            }
        });
    }

    if (copyDefaultPathButton && outputFolderPathInput) { 
        copyDefaultPathButton.addEventListener('click', function() {
            outputFolderPathInput.value = 'translated_output_web'; 
            appendLog("已复制默认下载目录路径到输入框。");
        });
    }

    // ==================================================
    // >>>>>>>>>> START OF ADDED EVENT LISTENERS FOR SOURCE TEXT BUTTONS <<<<<<<<<<
    if (copySourceTextButton && textInput) {
        copySourceTextButton.addEventListener('click', function() {
            const textToCopy = textInput.value;
            if (textToCopy) {
                navigator.clipboard.writeText(textToCopy).then(function() {
                    appendLog('原文已复制到剪贴板。');
                    if (statusMessage) {
                        const originalStatusText = statusMessage.textContent;
                        const originalStatusClass = statusMessage.className;
                        statusMessage.textContent = '原文已复制!';
                        statusMessage.className = 'status-message success short-lived';
                        setTimeout(() => {
                            if (statusMessage.textContent === '原文已复制!') {
                                statusMessage.textContent = originalStatusText;
                                statusMessage.className = originalStatusClass;
                            }
                        }, 2000);
                    }
                }).catch(function(err) {
                    appendLog('复制原文到剪贴板失败: ' + err);
                    try {
                        textInput.select();
                        textInput.setSelectionRange(0, 99999);
                        document.execCommand('copy');
                        appendLog('尝试使用旧版API复制原文成功。');
                         if (statusMessage) {
                            const originalStatusText = statusMessage.textContent; // Save before changing
                            const originalStatusClass = statusMessage.className;
                            statusMessage.textContent = '原文已复制 (旧版)!';
                            statusMessage.className = 'status-message success short-lived';
                            setTimeout(() => { if (statusMessage.textContent === '原文已复制 (旧版)!') { statusMessage.textContent = originalStatusText; statusMessage.className = originalStatusClass;}}, 2000);
                        }
                    } catch (execErr) {
                        appendLog('旧版API复制原文也失败: ' + execErr);
                        alert('无法自动复制原文。请手动复制。');
                    }
                });
            } else {
                appendLog('原文区域无内容可复制。');
                 if (statusMessage) {
                    const originalStatusText = statusMessage.textContent; // Save before changing
                    const originalStatusClass = statusMessage.className;
                    statusMessage.textContent = '原文无内容';
                    statusMessage.className = 'status-message info short-lived';
                    setTimeout(() => { if (statusMessage.textContent === '原文无内容') {statusMessage.textContent = originalStatusText; statusMessage.className = originalStatusClass;}}, 2000);
                }
            }
        });
    }

    if (clearSourceTextButton && textInput) {
        clearSourceTextButton.addEventListener('click', function() {
            if (textInput.value) {
                textInput.value = '';
                appendLog('原文已清除。');
                if (textInput.focus) textInput.focus(); 
                if (statusMessage) { 
                    const originalStatusText = statusMessage.textContent;
                    const originalStatusClass = statusMessage.className;
                    statusMessage.textContent = '原文已清除';
                    statusMessage.className = 'status-message info short-lived';
                    setTimeout(() => {
                        if (statusMessage.textContent === '原文已清除') {
                           statusMessage.textContent = originalStatusText;
                           statusMessage.className = originalStatusClass;
                        }
                    }, 1500);
                }
            } else {
                appendLog('原文区域已为空，无需清除。');
            }
        });
    }
    // <<<<<<<<<< END OF ADDED EVENT LISTENERS FOR SOURCE TEXT BUTTONS <<<<<<<<<<
    // ==================================================

    if (copyTranslatedTextButton && translatedTextDisplay) {
        copyTranslatedTextButton.addEventListener('click', function() {
            const textToCopy = translatedTextDisplay.value;
            if (textToCopy) {
                navigator.clipboard.writeText(textToCopy).then(function() {
                    appendLog('翻译结果已复制到剪贴板。');
                    if (statusMessage) {
                        const originalStatusText = statusMessage.textContent;
                        const originalStatusClass = statusMessage.className;
                        statusMessage.textContent = '已复制到剪贴板!';
                        statusMessage.className = 'status-message success short-lived';
                        setTimeout(() => {
                            if (statusMessage.textContent === '已复制到剪贴板!') {
                                statusMessage.textContent = originalStatusText; 
                                statusMessage.className = originalStatusClass;
                            }
                        }, 2000);
                    }
                }).catch(function(err) {
                    appendLog('复制到剪贴板失败 (navigator.clipboard): ' + err);
                    try {
                        translatedTextDisplay.select();
                        translatedTextDisplay.setSelectionRange(0, 99999); 
                        document.execCommand('copy');
                        appendLog('尝试使用旧版API复制成功。');
                        if (statusMessage) {
                            const originalStatusText = statusMessage.textContent;
                            const originalStatusClass = statusMessage.className;
                            statusMessage.textContent = '已复制 (旧版)!';
                            statusMessage.className = 'status-message success short-lived';
                            setTimeout(() => {
                                if (statusMessage.textContent === '已复制 (旧版)!') {
                                    statusMessage.textContent = originalStatusText;
                                    statusMessage.className = originalStatusClass;
                                }
                            }, 2000);
                        }
                    } catch (execErr) {
                        appendLog('旧版API复制也失败: ' + execErr);
                        alert('无法自动复制文本。请手动选择并复制。');
                        if (statusMessage) { 
                            statusMessage.textContent = '自动复制失败，请手动操作。';
                            statusMessage.className = 'status-message error';
                        }
                    }
                });
            } else {
                appendLog('没有可复制的翻译结果。');
                if (statusMessage) {
                    const originalStatusText = statusMessage.textContent;
                    const originalStatusClass = statusMessage.className;
                    statusMessage.textContent = '无内容可复制';
                    statusMessage.className = 'status-message info short-lived';
                    setTimeout(() => {
                        if (statusMessage.textContent === '无内容可复制') {
                           statusMessage.textContent = originalStatusText;
                           statusMessage.className = originalStatusClass;
                        }
                    }, 2000);
                }
            }
        });
    }

    if (translateButton) {
        translateButton.addEventListener('click', async function() {
            resetOutputArea(); 

            if (translateButton) translateButton.disabled = true; 
            if (statusMessage) {
                statusMessage.textContent = '正在翻译中...请稍候。';
                statusMessage.className = 'status-message info';
            }
            appendLog("开始翻译...");

            const selectedPlatform = apiPlatformSelect ? apiPlatformSelect.value : 'custom';
            const apiKey = apiKeyInput ? apiKeyInput.value : '';
            const baseUrl = baseUrlInput ? baseUrlInput.value : '';
            const model = modelInput ? modelInput.value : '';
            const sourceLang = sourceLangSelect ? sourceLangSelect.value : '';
            const targetLang = targetLangSelect ? targetLangSelect.value : '';
            const encodingValue = document.getElementById('encoding') ? document.getElementById('encoding').value : 'utf-8';
            const outputFolderPathValue = outputFolderPathInput ? outputFolderPathInput.value : ''; 

            if (!targetLang) {
                if (statusMessage) {
                    statusMessage.textContent = '错误：目标语言是必填项。';
                    statusMessage.className = 'status-message error';
                }
                if (translateButton) translateButton.disabled = false;
                appendLog("错误：目标语言是必填项。");
                return;
            }

            const formData = new FormData();
            formData.append('api_platform', selectedPlatform);
            formData.append('api_key', apiKey);
            formData.append('base_url', baseUrl);
            formData.append('model', model);
            formData.append('target_lang', targetLang);
            formData.append('source_lang', sourceLang);
            
            let isFileTranslation = false;
            let translationFormat = 'unformatted'; 

            if (modeFileButton && modeFileButton.classList.contains('active') && fileInput && fileInput.files.length > 0) {
                const file = fileInput.files[0];
                formData.append('file', file);
                isFileTranslation = true;
                appendLog(`翻译模式：文档翻译。文档: ${file.name}`);
                
                const fileExtension = file.name.split('.').pop().toLowerCase();
                if (fileExtension === 'txt') {
                    formData.append('encoding', encodingValue);
                } else if (fileExtension === 'docx') {
                    const selectedFormatRadio = document.querySelector('input[name="translation_format"]:checked');
                    if (selectedFormatRadio) {
                        translationFormat = selectedFormatRadio.value;
                    }
                    appendLog(`.docx 翻译格式: ${translationFormat === 'formatted' ? '带格式' : '不带格式'}`);
                }
                formData.append('translation_format', translationFormat);
                formData.append('output_folder_path', outputFolderPathValue);
                
            } else if (modeTextButton && modeTextButton.classList.contains('active')) { 
                const textToTranslate = textInput ? textInput.value : '';
                if (!textToTranslate.trim()) { 
                    if (statusMessage) {
                        statusMessage.textContent = '错误：待翻译文字不能为空。';
                        statusMessage.className = 'status-message error';
                    }
                    if (translateButton) translateButton.disabled = false;
                    appendLog("错误：待翻译文字不能为空。");
                    return;
                }
                formData.append('text_input', textToTranslate);
                appendLog("翻译模式：文字翻译 (流式)。");
            } else { 
                if (statusMessage) {
                    statusMessage.textContent = '错误：请选择文件或输入文字进行翻译。';
                    statusMessage.className = 'status-message error';
                }
                if (translateButton) translateButton.disabled = false;
                appendLog("错误：未指定翻译内容。");
                return;
            }

            try {
                const response = await fetch('/translate_api', {
                    method: 'POST',
                    body: formData
                });

                if (!response.ok) {
                    const errData = await response.json().catch(() => ({ error: `HTTP error! status: ${response.status} - ${response.statusText}` }));
                    throw new Error(errData.error || `HTTP error! status: ${response.status} - ${response.statusText}`);
                }

                if (!isFileTranslation && response.headers.get("content-type")?.includes("text/event-stream")) {
                    if (translatedTextDisplay) translatedTextDisplay.value = ''; 
                    appendLog("开始接收流式响应..."); 
                    const reader = response.body.getReader();
                    const decoder = new TextDecoder();
                    let accumulatedText = ""; 
                    let receivedAnyChunk = false; 
                    // console.log("DEBUG: Stream reader created."); // DEBUG

                    let streamCancelledInternally = false;

                    while (true) {
                        try { 
                            const { done, value } = await reader.read();
                            // console.log("DEBUG: Stream read:", { done, value_length: value ? value.length : 0 }); 

                            if (done) {
                                if (statusMessage) {
                                    statusMessage.textContent = receivedAnyChunk ? '翻译完成!' : '翻译完成 (无内容)。';
                                    statusMessage.className = 'status-message success';
                                }
                                appendLog(receivedAnyChunk ? "文字翻译流结束 (done=true)。" : "文字翻译流结束 (done=true, 未收到有效文本块)。");
                                // console.log("DEBUG: Stream ended (done=true). Received any chunk:", receivedAnyChunk); 
                                break;
                            }
                            accumulatedText += decoder.decode(value, { stream: true });
                            let parts = accumulatedText.split('\n\n');
                            accumulatedText = parts.pop() || ""; 
                            for (const part of parts) {
                                // console.log("DEBUG: Processing stream part:", part);
                                if (part.startsWith('data: ')) {
                                    const jsonDataString = part.substring(6);
                                    // console.log("DEBUG: Raw JSON data string from stream:", jsonDataString); 
                                    if (jsonDataString.trim() === "[DONE]") {
                                        if (statusMessage) { statusMessage.textContent = receivedAnyChunk ? '翻译完成!' : '翻译完成 (API标记[DONE])。'; statusMessage.className = 'status-message success';}
                                        appendLog(receivedAnyChunk ? "文字翻译流由 API [DONE] 标记结束。" : "文字翻译流由 API [DONE] 标记结束 (未收到有效文本块)。");
                                        // console.log("DEBUG: Stream ended by API [DONE] message. Received any chunk:", receivedAnyChunk);
                                        if (!reader.closed) await reader.cancel();
                                        streamCancelledInternally = true;
                                        break; 
                                    }
                                    try {
                                        const data = JSON.parse(jsonDataString);
                                        // console.log("DEBUG: Parsed JSON data from stream:", data);
                                        if (data.text_chunk && translatedTextDisplay) {
                                            translatedTextDisplay.value += data.text_chunk;
                                            translatedTextDisplay.scrollTop = translatedTextDisplay.scrollHeight; 
                                            receivedAnyChunk = true; 
                                        } else if (data.error) {
                                            if (statusMessage) { statusMessage.textContent = `错误：${data.error}`; statusMessage.className = 'status-message error';}
                                            appendLog(`流中错误: ${data.error}`);
                                            // console.error("DEBUG: Error in stream from API:", data.error);
                                            if (!reader.closed) await reader.cancel();
                                            streamCancelledInternally = true;
                                            break; 
                                        } else if (data.done) { 
                                             if (statusMessage) { statusMessage.textContent = receivedAnyChunk ? '翻译完成!' : '翻译完成 (API标记done:true)。'; statusMessage.className = 'status-message success';}
                                            appendLog(receivedAnyChunk ? "文字翻译流由 API JSON 'done:true' 标记结束。" : "文字翻译流由 API JSON 'done:true' 标记结束 (未收到有效文本块)。");
                                            // console.log("DEBUG: Stream ended by API JSON 'done:true'. Received any chunk:", receivedAnyChunk);
                                            if (!reader.closed) await reader.cancel();
                                            streamCancelledInternally = true;
                                            break;
                                        } else if (Object.keys(data).length > 0 && !data.text_chunk) {
                                            // console.warn("DEBUG: Received unexpected JSON structure in stream:", data);
                                            appendLog(`流中收到意外JSON结构: ${JSON.stringify(data)}`);
                                        }
                                    } catch (e) {
                                        appendLog(`无法解析流数据块: ${jsonDataString} - ${e}`);
                                        // console.error("DEBUG: JSON parsing error in stream:", e, "Data:", jsonDataString);
                                    }
                                } 
                            } 
                            if (streamCancelledInternally) { break; }
                        } catch (readError) {
                            appendLog(`读取流时发生错误: ${readError.message}`);
                            // console.error("DEBUG: Error reading from stream:", readError);
                            if (statusMessage) { statusMessage.textContent = `读取流错误: ${readError.message}`; statusMessage.className = 'status-message error';}
                            break; 
                        }
                    } 
                } else if (isFileTranslation) {
                    const result = await response.json();
                    if (statusMessage) { statusMessage.textContent = '翻译成功！'; statusMessage.className = 'status-message success';}
                    if (result.translated_file_url && downloadLink && downloadArea) {
                        downloadLink.href = result.translated_file_url;
                        downloadLink.textContent = `下载翻译文件 (${result.translated_file_url.split('/').pop()})`;
                        downloadArea.style.display = 'block';
                        downloadLink.style.display = 'inline-block';
                        appendLog(`文档翻译完成。下载链接: ${result.translated_file_url}`);
                    } else if (result.message && translatedTextDisplay) { 
                        translatedTextDisplay.value = result.message;
                        appendLog(`文档翻译消息: ${result.message}`);
                    }  else if (result.error && statusMessage) { 
                        statusMessage.textContent = `错误：${result.error}`;
                        statusMessage.className = 'status-message error';
                        appendLog(`文件翻译API返回错误: ${result.error}`);
                    }
                } else { 
                     const result = await response.json().catch(() => ({ "error" : "非流式响应且无法解析JSON"}));
                     if (result.error && statusMessage) {
                        statusMessage.textContent = `错误：${result.error}`;
                        statusMessage.className = 'status-message error';
                        appendLog(`非流式响应错误: ${JSON.stringify(result)}`);
                     } else if (result.translated_text && translatedTextDisplay) {
                        translatedTextDisplay.value = result.translated_text;
                        if(statusMessage) { statusMessage.textContent = '翻译完成!'; statusMessage.className = 'status-message success';}
                     } else if (statusMessage) { 
                         statusMessage.textContent = `错误：收到意外的响应格式。`;
                         statusMessage.className = 'status-message error';
                         appendLog(`意外响应格式: ${JSON.stringify(result)}`);
                     }
                }
            } catch (error) {
                if (statusMessage) { statusMessage.textContent = `翻译请求失败：${error.message}。`; statusMessage.className = 'status-message error';}
                appendLog(`网络或JS错误: ${error.message}`);
            } finally {
                if (translateButton) translateButton.disabled = false;
                appendLog(isFileTranslation ? "文档翻译过程结束。" : "文字翻译过程结束。");
            }
        });
    }

});
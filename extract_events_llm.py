#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用 DeepSeek API 按章节提取《明朝那些事儿》第壹卷的事件。

运行前请设置环境变量:
    export DEEPSEEK_API_KEY="your-api-key"

DeepSeek API 兼容 OpenAI 格式，base_url: https://api.deepseek.com
"""

import os
import re
import json
import time
from openai import OpenAI

API_KEY = os.environ.get("DEEPSEEK_API_KEY")
if not API_KEY:
    print("错误：未设置 DEEPSEEK_API_KEY 环境变量")
    print("请运行: export DEEPSEEK_API_KEY='your-api-key'")
    exit(1)

client = OpenAI(api_key=API_KEY, base_url="https://api.deepseek.com")

# 读取第壹卷文本
with open('/Disk1/development/App/ming/明朝那些事儿.txt', 'rb') as f:
    text = f.read().decode('gbk', errors='ignore')
lines = text.split('\n')
vol1_lines = lines[22:5798]

# 识别章节
chapters = []
chapter_pattern = re.compile(r'^第[一二三四五六七八九十]+章\s+')
for i, line in enumerate(vol1_lines):
    s = line.strip()
    if chapter_pattern.match(s):
        chapters.append((i, s))

print(f"共找到 {len(chapters)} 个章节")

PROMPT_TEMPLATE = """你是中国历史专家。请根据以下《明朝那些事儿》第壹卷（朱元璋篇）的章节内容，提取5-10个关键历史事件。

要求：
1. 每个事件必须包含：题目（简短标题）、时间（公元年份，如1368）、涉及人物（列表）、事件简介（50-100字）、重要性（1-5分，5分最重要）
2. 事件必须是该章节中实际发生或提及的，不要编造
3. 时间尽量精确，如果只有年号请转换为公元年份（洪武元年=1368，至正元年=1341）
4. 重要性评分标准：5分=改变历史走向（如称帝、大战），4分=重大政治军事事件，3分=重要政策或战役，2分=一般事件，1分=背景铺垫
5. 只输出JSON数组，不要任何解释文字

输出格式示例：
[
  {
    "title": "朱元璋称帝",
    "year": 1368,
    "persons": ["朱元璋", "刘基", "徐达"],
    "summary": "朱元璋在应天称帝，建立明朝，年号洪武。",
    "importance": 5
  }
]

章节内容：
{content}
"""

all_events = []

for idx, (start_line, title) in enumerate(chapters):
    end_line = chapters[idx + 1][0] if idx + 1 < len(chapters) else len(vol1_lines)
    chapter_text = '\n'.join(vol1_lines[start_line:end_line])

    # 截断文本，避免超出上下文限制（约6000字符）
    if len(chapter_text) > 6000:
        chapter_text = chapter_text[:6000] + "\n...（内容截断）"

    print(f"\n[{idx+1}/{len(chapters)}] 处理: {title} ({len(chapter_text)} 字符)")

    prompt = PROMPT_TEMPLATE.replace("{content}", chapter_text)

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "你是一个严谨的中国历史研究者，擅长从文本中提取结构化历史事件。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=2000,
        )

        content = response.choices[0].message.content.strip()

        # 提取 JSON
        # 有时模型会输出 ```json ... ``` 包裹的内容
        if '```json' in content:
            content = content.split('```json')[1].split('```')[0].strip()
        elif '```' in content:
            content = content.split('```')[1].split('```')[0].strip()

        events = json.loads(content)

        # 添加章节来源
        for ev in events:
            ev['chapter'] = title
            ev['id'] = f"ev_llm_{len(all_events)}"
            all_events.append(ev)

        print(f"  提取到 {len(events)} 个事件")
        for ev in events:
            print(f"    - {ev['year']} {ev['title']} (重要性:{ev['importance']})")

    except Exception as e:
        print(f"  错误: {e}")
        # 保存当前进度
        with open('/Disk1/development/App/ming/data/events_llm_partial.json', 'w', encoding='utf-8') as f:
            json.dump(all_events, f, ensure_ascii=False, indent=2)
        continue

    # 请求间隔，避免限流
    time.sleep(1)

# 保存结果
output_path = '/Disk1/development/App/ming/data/events_llm.json'
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(all_events, f, ensure_ascii=False, indent=2)

print(f"\n✅ 完成！共提取 {len(all_events)} 个事件")
print(f"   保存至: {output_path}")

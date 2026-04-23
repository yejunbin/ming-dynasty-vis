#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用 DeepSeek API 按章节提取《明朝那些事儿》第壹卷的人物和关系。

运行前请设置环境变量:
    export DEEPSEEK_API_KEY="your-api-key"
"""

import os
import re
import json
import time
from openai import OpenAI

API_KEY = os.environ.get("DEEPSEEK_API_KEY")
if not API_KEY:
    print("错误：未设置 DEEPSEEK_API_KEY 环境变量")
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

PROMPT_TEMPLATE = """你是中国历史专家。请根据以下《明朝那些事儿》第壹卷（朱元璋篇）的章节内容，提取所有出现的历史人物及其关系。

要求：
1. **人物**字段：
   - name: 人物全名（优先用常用名，如"朱元璋"而非"朱重八"）
   - aliases: 别名列表（如"朱重八"、"洪武帝"等）
   - identity: 身份（如农民/将领/皇帝/谋士/对手等）
   - birthYear: 生年（整数，不详则null）
   - deathYear: 卒年（整数，不详则null）
   - bio: 一句话简介（50字以内）
   - appearanceTime: 本章中该人物出场的时间，格式要求如下：
     * 如有具体公元年份，直接写整数年份（如1355）
     * 如只有年号，换算为公元年份（至正元年=1341，龙凤元年=1355，洪武元年=1368）
     * 如只有模糊描述，写为字符串区间，如"1340年代"、"洪武初年(1368-1372)"、"元末(1330-1368)"、"少年时期"
     * 如完全无法判断，写"不详"

2. **关系**字段：
   - source: 人物A
   - target: 人物B
   - type: 关系类型（只选一种：君臣/敌对/亲属/朋友/同盟/师生/关联）
   - description: 关系简述（如"朱元璋封徐达为魏国公"）
   - chapterEvent: 本章涉及的具体事件名
   - note: 如果有关系变化（如从朋友变敌人），在此说明

3. 注意：
   - 只提取本章实际提到的人物和关系，不要编造
   - 关系必须两人在本章都有出现
   - 生卒年不详的填null，不要猜测
   - appearanceTime 尽量精确到年份，这是最重要的字段
   - 只输出JSON，不要解释

输出格式：
{
  "persons": [
    {"name": "朱元璋", "aliases": ["朱重八"], "identity": "明朝开国皇帝", "birthYear": 1328, "deathYear": 1398, "bio": "明朝开国皇帝，出身贫苦", "appearanceTime": 1328}
  ],
  "relations": [
    {"source": "朱元璋", "target": "徐达", "type": "君臣", "description": "朱元璋任命徐达为大将军", "chapterEvent": "任命将领", "note": ""}
  ]
}

章节内容：
{content}
"""

all_persons = {}
all_relations = []

for idx, (start_line, title) in enumerate(chapters):
    end_line = chapters[idx + 1][0] if idx + 1 < len(chapters) else len(vol1_lines)
    chapter_text = '\n'.join(vol1_lines[start_line:end_line])

    if len(chapter_text) > 8000:
        chapter_text = chapter_text[:8000] + "\n...（内容截断）"

    print(f"\n[{idx+1}/{len(chapters)}] 处理: {title} ({len(chapter_text)} 字符)")

    prompt = PROMPT_TEMPLATE.replace("{content}", chapter_text)

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "你是一个严谨的中国历史研究者，擅长从文本中提取结构化历史数据。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=4000,
        )

        content = response.choices[0].message.content.strip()
        if '```json' in content:
            content = content.split('```json')[1].split('```')[0].strip()
        elif '```' in content:
            content = content.split('```')[1].split('```')[0].strip()

        result = json.loads(content)

        # Merge persons
        for p in result.get('persons', []):
            name = p.get('name', '')
            if not name:
                continue
            if name not in all_persons:
                all_persons[name] = p
                all_persons[name]['chapters'] = [title]
            else:
                # Merge aliases
                existing = all_persons[name]
                for alias in p.get('aliases', []):
                    if alias not in existing.get('aliases', []):
                        existing.setdefault('aliases', []).append(alias)
                # Update birth/death if previously null
                if p.get('birthYear') and not existing.get('birthYear'):
                    existing['birthYear'] = p['birthYear']
                if p.get('deathYear') and not existing.get('deathYear'):
                    existing['deathYear'] = p['deathYear']
                # Update bio if longer
                if len(p.get('bio', '')) > len(existing.get('bio', '')):
                    existing['bio'] = p['bio']
                existing['chapters'].append(title)

        # Merge relations
        for r in result.get('relations', []):
            r['chapter'] = title
            all_relations.append(r)

        print(f"  提取到 {len(result.get('persons', []))} 个人物, {len(result.get('relations', []))} 条关系")

    except Exception as e:
        print(f"  错误: {e}")
        with open('/Disk1/development/App/ming/data/persons_relations_partial.json', 'w', encoding='utf-8') as f:
            json.dump({'persons': list(all_persons.values()), 'relations': all_relations}, f, ensure_ascii=False, indent=2)
        continue

    time.sleep(1)

# Save
output = {
    'persons': list(all_persons.values()),
    'relations': all_relations,
}

output_path = '/Disk1/development/App/ming/data/persons_relations_llm.json'
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"\n✅ 完成！")
print(f"   人物: {len(all_persons)}")
print(f"   关系: {len(all_relations)}")
print(f"   保存至: {output_path}")
